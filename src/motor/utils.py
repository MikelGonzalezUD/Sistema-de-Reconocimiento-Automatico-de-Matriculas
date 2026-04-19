import base64

import cv2
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