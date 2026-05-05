import base64

import cv2
import requests
import numpy as np
import json
import re

def order_points(pts):

    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect

def rectify_plate(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray, 100, 200)

    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:

            pts = approx.reshape(4, 2)

            rect = order_points(pts)

            (tl, tr, br, bl) = rect

            widthA = np.linalg.norm(br - bl)
            widthB = np.linalg.norm(tr - tl)
            maxWidth = int(max(widthA, widthB))

            heightA = np.linalg.norm(tr - br)
            heightB = np.linalg.norm(tl - bl)
            maxHeight = int(max(heightA, heightB))

            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")

            M = cv2.getPerspectiveTransform(rect, dst)

            warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

            return warped

    return image

def load_patterns(json_path):
    """Carga los patrones desde el archivo JSON."""
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando JSON: {e}")
        return {}

def validate_plate(text, patterns):
    """
    Compara el texto detectado con los regex del JSON.
    Devuelve el código del país si coincide, de lo contrario None.
    """
    for key, info in patterns.items():
        if re.match(info['regex'], text):
            return info['country']
    return None

def enviar_deteccion(matricula, pais, confianza, imagen_np, camara_id, API_URL, API_KEY):
    # Convertir imagen a bytes
    _, img_encoded = cv2.imencode('.jpg', imagen_np)
    
    # Preparar datos y archivo
    payload = {
        'matricula': matricula,
        'pais': pais,
        'confianza': confianza,
        'camara_id': camara_id
    }
    files = [
        ('imagen', ('plate.jpg', img_encoded.tobytes(), 'image/jpeg'))
    ]

    try:
        headers = {
            'x-api-key': API_KEY
        }
        response = requests.post(API_URL, data=payload, files=files, headers=headers, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Error enviando a API: {e}")
        return False
    
    
def ordenar_ocr(chars, results_ocr, char_label, threshold=10):
    for res in results_ocr:
        for b in res.boxes:
            # Guardamos la posición X y el nombre de la clase (el caracter)
            x_center = b.xywh[0][0].item()
            y_center = b.xywh[0][1].item()
            chars.append((x_center, y_center, char_label))
                
    # ORDENAR POR Y (Altura)
    chars.sort(key=lambda x: x[1])
    
    lines = []
    threshold = 10 
    
    for char in chars:
        placed = False
        for line in lines:
            if abs(char[1] - line[0][1]) < threshold:
                line.append(char)
                placed = True
                break
        if not placed:
            lines.append([char])
    
    # ORDENAR POR X (Izquierda a derecha)
    for line in lines:
        line.sort(key=lambda x: x[0])
        
    lines.sort(key=lambda line: line[0][1])
    clean_text = "".join(
        char[2] for line in lines for char in line
    ).upper()
    
    return clean_text