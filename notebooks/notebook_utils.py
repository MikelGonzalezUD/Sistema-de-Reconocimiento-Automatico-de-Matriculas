import os
import easyocr
import cv2
import torch
import time
import re

# Funcion para leer los archivos .txt de etiquetas y reconstruir el texto real ordenado por X
def cargar_texto_real_desde_txt(ruta_imagen, model_names):

    ruta_txt = os.path.normpath(ruta_imagen.replace('images', 'labels').replace('.jpg', '.txt').replace('.png', '.txt').replace('.jpeg', '.txt'))
    if not os.path.exists(ruta_txt): return None
    
    etiquetas = []
    with open(ruta_txt, 'r') as f:
        for linea in f:
            datos = linea.split()
            if datos:
                clase, x_centro = int(datos[0]), float(datos[1])
                etiquetas.append((x_centro, model_names[clase]))
    
    etiquetas.sort(key=lambda x: x[0])
    return "".join([char for _, char in etiquetas])


#Wrapper para que EasyOCR se comporte como un modelo de YOLO en el script.
class EasyOCRModel:
    def __init__(self):
        # Cargamos el lector de EasyOCR
        self.reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())

    def predict_ocr(self, img_path):
        # Cargamos la imagen con OpenCV
        img = cv2.imread(img_path)
        if img is None:
            return "", 0
        
        start_time = time.time()
        
        # Pasamos la imagen ya cargada (numpy array) a EasyOCR
        ocr_res = self.reader.readtext(img)
        latencia = (time.time() - start_time) * 1000
        
        # Ordenar por coordenada X del cuadro delimitador (izq a der)
        ocr_res.sort(key=lambda x: x[0][0][0])
        pred_text = "".join([re.sub(r'[^A-Z0-9]', '', x[1].upper()) for x in ocr_res])
        return pred_text, latencia