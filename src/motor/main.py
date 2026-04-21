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


TRACK_MAX_AGE = 40        # Frames para mantener un track perdido vivo
VOTING_BUFFER_SIZE = 10   # Numero de frames para agregar y decidir el "mejor" resultado
FRAME_SKIP = 2            # Procesar cada N frames para reducir carga computacional
frame_count = 0
ocr_frame_count = 0

# Inicializar Tracker DeepSort
tracker = DeepSort(max_age=TRACK_MAX_AGE, n_init=3, max_iou_distance=0.7)

# Carga de patrones desde JSON
patterns = load_patterns("patrones.json")

# Memoria de tracks: Almacena el historial de OCR por ID de track
tracked_plates = {}

# Cuda check
print("Using device:", "cuda" if torch.cuda.is_available() else "cpu")
device = "cuda" if torch.cuda.is_available() else "cpu"

#Inicializar modelos
model_lp = YOLO(LP_MODEL_PATH).to(device)
model_ocr = YOLO(OCR_MODEL_PATH).to(device)

# Inicializar video captura de la cámara o video
# cap = cv2.VideoCapture("rtsp://192.168.1.132:554/stream1")
# cap = cv2.VideoCapture("https://192.168.1.131:8080/video")
cap = cv2.VideoCapture("parking2.MOV")


while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    
    frame_count += 1
    if frame_count > 1000:  # Reiniciar contador para evitar overflow
        frame_count = 0
    if frame_count % FRAME_SKIP != 0:
        continue
    
    frame = cv2.resize(frame, (640, 360))

    # 1. Detección de Placas
    results = model_lp(frame, conf=0.5, verbose=False)
    detections = []
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf[0].item()
            detections.append(([x1, y1, x2 - x1, y2 - y1], conf, 0))

    # 2. Tracking
    tracks = tracker.update_tracks(detections, frame=frame)

    for track in tracks:
        if not track.is_confirmed(): 
            continue
        
        track_id = track.track_id
        x1, y1, x2, y2 = map(int, track.to_ltrb())
        area = (x2 - x1) * (y2 - y1)
        # print(f"Area: {area}")
        if area < 400: 
            continue
        
        if track_id in tracked_plates and tracked_plates[track_id]["sent"]:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.putText(frame, f"ID:{track_id} [{pais}] {best_plate}", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            continue
        
        ocr_frame_count += 1
        if ocr_frame_count > 10000:  # Reiniciar contador para evitar overflow
            ocr_frame_count = 0
        if ocr_frame_count % (FRAME_SKIP) != 0:
            continue
        
        # Crop y Rectificación
        plate_crop = frame[max(0, y1-15):y2+15, max(0, x1-15):x2+15]
        if plate_crop.size == 0: continue
        
        # plate_rectified = rectify_plate(plate_crop)
        plate_rectified = plate_crop
        
        cv2.imshow("Ultima Matricula Detectada", imutils.resize(plate_rectified, width=300))

        # 3. OCR con YOLO (Detección de caracteres)
        results_ocr = model_ocr(plate_rectified, conf=0.4, imgsz=640, verbose=False)
        
        chars = []
        for res in results_ocr:
            for b in res.boxes:
                # Guardamos la posición X y el nombre de la clase (el caracter)
                x_center = b.xywh[0][0].item()
                char_label = model_ocr.names[int(b.cls[0])]
                chars.append((x_center, char_label))
        
        # ORDENAR POR X (Izquierda a derecha)
        chars.sort(key=lambda x: x[0])
        clean_text = "".join([c[1] for c in chars]).upper()

        # 4. Post-procesamiento con el JSON (desde utils)
        pais_detectado = validate_plate(clean_text, patterns)

        if pais_detectado:
            if track_id not in tracked_plates:
                tracked_plates[track_id] = {"texts": [], "country": pais_detectado, "sent": False, "max_conf": 0.0}
            
            tracked_plates[track_id]["texts"].append(clean_text)
            
            conf_actual = track.get_det_conf() if track.get_det_conf() else 0.8
            if conf_actual > tracked_plates[track_id]["max_conf"]:
                tracked_plates[track_id]["max_conf"] = conf_actual

        # Lógica de visualización
        display_info = "Procesando..."
        if track_id in tracked_plates and tracked_plates[track_id]["texts"]:
            text_list = tracked_plates[track_id]["texts"]
            # Votación: el texto más repetido gana
            best_plate = max(set(text_list), key=text_list.count)
            pais = tracked_plates[track_id]["country"]
            conf = tracked_plates[track_id]["max_conf"] * 100
            
            display_info = f"[{pais}] {best_plate}"
            
            #ENVIAR A LA DB
            if len(text_list) >= VOTING_BUFFER_SIZE and not tracked_plates[track_id]["sent"]:
                success = enviar_deteccion(best_plate, pais, conf, plate_rectified, CAMERA_ID, API_URL, API_KEY)
                if success:
                    tracked_plates[track_id]["sent"] = True
                    print(f"✅ ID {track_id} inyectado con éxito: {best_plate}")
                    print(f"Tracked plates: {len(tracked_plates)}")
                    print(f"{tracked_plates}")

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"ID:{track_id} {display_info}", (x1, y1 - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2) 

    if frame is not None and frame.size != 0:
        resized_frame = imutils.resize(frame, width=1024)
        cv2.imshow("ALPR YOLO + JSON", resized_frame)
    if cv2.waitKey(1) & 0xFF == 27: break

cap.release()
cv2.destroyAllWindows()