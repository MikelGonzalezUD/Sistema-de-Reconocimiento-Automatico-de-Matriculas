import json
from ultralytics import YOLO
import cv2
import imutils
import re
import requests
import numpy as np
import torch
import sys
from pathlib import Path
from utils import rectify_plate, load_patterns, validate_plate, enviar_deteccion
from deep_sort_realtime.deepsort_tracker import DeepSort

root_path = Path.cwd().parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from config import LP_MODEL_PATH, OCR_MODEL_PATH, CAMERA_ID, API_URL, API_KEY
from src.database.db_manager import insertar_deteccion


# PARÁMETROS
TRACK_MAX_AGE = 40        # frames para mantener un track perdido vivo
VOTING_BUFFER_SIZE = 8   # lecturas necesarias antes de enviar la matrícula
FRAME_SKIP = 2            # procesar uno de cada N frames para reducir carga
frame_count = 0
ocr_frame_count = 0

# historial de OCR por ID de track: {track_id: {texts, country, sent, max_conf}}
tracked_plates = {}

# INICIALIZACIÓN
device = "cuda" if torch.cuda.is_available() else "cpu"
print("Dispositivo:", device)

tracker = DeepSort(max_age=TRACK_MAX_AGE, n_init=3, max_iou_distance=0.7)
patterns = load_patterns("patrones.json")

model_lp = YOLO(LP_MODEL_PATH).to(device)
model_ocr = YOLO(OCR_MODEL_PATH).to(device)

# fuente de vídeo: descomentar la línea correspondiente al entorno de producción
# cap = cv2.VideoCapture("rtsp://192.168.1.132:554/stream1")
# cap = cv2.VideoCapture("https://192.168.1.130:8080/video")
cap = cv2.VideoCapture("parking2.MOV")


# BUCLE PRINCIPAL
try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        frame_count += 1
        if frame_count > 1000:  # reiniciar para evitar overflow
            frame_count = 0
        if frame_count % FRAME_SKIP != 0:
            continue

        frame = cv2.resize(frame, (640, 360))

        # 1. DETECCIÓN DE MATRÍCULAS
        results = model_lp(frame, conf=0.5, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = box.conf[0].item()
                detections.append(([x1, y1, x2 - x1, y2 - y1], conf, 0))

        # 2. TRACKING
        tracks = tracker.update_tracks(detections, frame=frame)

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = track.track_id
            x1, y1, x2, y2 = map(int, track.to_ltrb())
            area = (x2 - x1) * (y2 - y1)
            if area < 400:
                continue

            # si ya fue enviado, solo mostrar el resultado en pantalla
            if track_id in tracked_plates and tracked_plates[track_id]["sent"]:
                sent = tracked_plates[track_id]
                sent_texts = sent["texts"]
                sent_plate = max(set(sent_texts), key=sent_texts.count) if sent_texts else "?"
                sent_pais = sent["country"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
                cv2.putText(frame, f"ID:{track_id} [{sent_pais}] {sent_plate}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                continue

            ocr_frame_count += 1
            if ocr_frame_count > 10000:
                ocr_frame_count = 0
            if ocr_frame_count % FRAME_SKIP != 0:
                continue

            # recorte con margen alrededor de la matrícula
            plate_crop = frame[max(0, y1-15):y2+15, max(0, x1-15):x2+15]
            if plate_crop.size == 0: continue

            plate_rectified = rectify_plate(plate_crop)
            # plate_rectified = plate_crop

            # 3. OCR
            results_ocr = model_ocr(plate_rectified, conf=0.35, imgsz=640, verbose=False)

            chars = []
            char_heights = []
            for res in results_ocr:
                for b in res.boxes:
                    x_center = b.xywh[0][0].item()
                    y_center = b.xywh[0][1].item()
                    char_label = model_ocr.names[int(b.cls[0])]
                    chars.append((x_center, y_center, char_label))
                    char_heights.append(b.xywh[0][3].item())

            if not chars:
                continue

            # ordenar caracteres por fila (Y) y dentro de cada fila por columna (X)
            chars.sort(key=lambda x: x[1])
            lines = []
            threshold = np.mean(char_heights) * 0.5

            for char in chars:
                placed = False
                for line in lines:
                    if abs(char[1] - line[0][1]) < threshold:
                        line.append(char)
                        placed = True
                        break
                if not placed:
                    lines.append([char])

            for line in lines:
                line.sort(key=lambda x: x[0])
            lines.sort(key=lambda line: line[0][1])

            clean_text = "".join(char[2] for line in lines for char in line).upper()

            # 4. VALIDACIÓN
            pais_detectado = validate_plate(clean_text, patterns)

            if pais_detectado:
                if track_id not in tracked_plates:
                    tracked_plates[track_id] = {"texts": [], "country": pais_detectado, "sent": False, "max_conf": 0.0}

                tracked_plates[track_id]["texts"].append(clean_text)

                conf_actual = track.get_det_conf() if track.get_det_conf() else 0.8
                if conf_actual > tracked_plates[track_id]["max_conf"]:
                    tracked_plates[track_id]["max_conf"] = conf_actual

            # 5. VISUALIZACIÓN Y ENVÍO
            display_info = "Procesando..."
            if track_id in tracked_plates and tracked_plates[track_id]["texts"]:
                text_list = tracked_plates[track_id]["texts"]
                # votación: el texto más repetido gana
                best_plate = max(set(text_list), key=text_list.count)
                pais = tracked_plates[track_id]["country"]
                conf = tracked_plates[track_id]["max_conf"] * 100
                display_info = f"[{pais}] {best_plate}"

                if len(text_list) >= VOTING_BUFFER_SIZE and not tracked_plates[track_id]["sent"]:
                    success = enviar_deteccion(best_plate, pais, conf, plate_rectified, CAMERA_ID, API_URL, API_KEY)
                    if success:
                        tracked_plates[track_id]["sent"] = True
                        print(f"✅ ID {track_id} enviado: {best_plate}")

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"ID:{track_id} {display_info}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # eliminar tracks enviados que ya no están activos para evitar crecimiento ilimitado
        active_ids = {t.track_id for t in tracks if t.is_confirmed()}
        tracked_plates = {tid: data for tid, data in tracked_plates.items()
                          if tid in active_ids or not data["sent"]}

        if frame is not None and frame.size != 0:
            resized_frame = imutils.resize(frame, width=1024)
            cv2.imshow("ALPR YOLO + JSON", resized_frame)
        if cv2.waitKey(1) & 0xFF == 27: break

finally:
    cap.release()
    cv2.destroyAllWindows()
