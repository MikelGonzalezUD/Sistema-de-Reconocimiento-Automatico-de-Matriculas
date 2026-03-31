from ultralytics import YOLO
import cv2
import easyocr
import imutils  
import re
import requests
import numpy as np
import torch
import sys
from pathlib import Path
from deep_sort_realtime.deepsort_tracker import DeepSort

root_path = Path.cwd().parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))
    
from config import LP_MODEL_PATH, OCR_MODEL_PATH

OCR_CONF_THRESHOLD = 0.65  # Threshold para validar OCR
TRACK_MAX_AGE = 15        # Frames para mantener un track perdido vivo
VOTING_BUFFER_SIZE = 45   # Numero de frames para agregar y decidir el "mejor" resultado

# Inicializar Tracker DeepSort
tracker = DeepSort(max_age=TRACK_MAX_AGE, n_init=3, max_iou_distance=0.7)

# Memoria de tracks: Almacena el historial de OCR por ID de track
# Formato: { track_id: {"texts":, "confidences":, "finalized": False} }
matriculas_traqueadas = {}

# Cuda check
print("Using device:", "cuda" if torch.cuda.is_available() else "cpu")

# Inicializar video, modelo y OCR
cap = cv2.VideoCapture("rtsp://192.168.1.136:554/stream1")
# cap = cv2.VideoCapture("parking.MOV")
model = YOLO(LP_MODEL_PATH).to("cuda")
ocr = YOLO(OCR_MODEL_PATH).to("cuda")


frame_cont = 0

