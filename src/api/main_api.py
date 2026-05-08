from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Depends
import cv2
import numpy as np
import uvicorn
from src.database.db_manager import insertar_deteccion, insertar_camara, listar_camaras, listar_vehiculos_autorizados, insertar_vehiculo_autorizado, eliminar_vehiculo_autorizado
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from config import API_KEY
except ImportError as e:
    print(f"Error fatal: No se encuentra config.py. {e}")

app = FastAPI(title="ALPR API Gateway")

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="No autorizado: API Key inválida")
    return x_api_key

@app.get("/")
def read_root():
    return {"status": "API Online", "message": "Esperando detecciones"}

@app.post("/deteccion")
async def recibir_deteccion(
    matricula: str = Form(...),
    pais: str = Form(...),
    confianza: float = Form(...),
    camara_id: int = Form(...),
    imagen: UploadFile = File(...),
    token: str = Depends(verify_api_key)
):
    try:
        # 1. Leer los bytes de la imagen enviada
        image_bytes = await imagen.read()
        
        # 2. Convertir bytes a formato OpenCV (numpy)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Imagen inválida")

        success = insertar_deteccion(matricula, pais, confianza, img, camara_id)
        
        if success:
            return {"status": "success", "message": f"Matrícula {matricula} registrada"}
        else:
            raise HTTPException(status_code=500, detail="Error al insertar en DB")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/camaras")
async def api_obtener_camaras(token: str = Depends(verify_api_key)):
    try:
        camaras = listar_camaras()
        return {"status": "success", "data": camaras}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))   
    
@app.post("/camaras")
async def crear_camara(ubicacion: str = Form(...), modelo: str = Form(...), _ = Depends(verify_api_key)):
    insertar_camara(ubicacion, modelo)
    return {"status": "Cámara creada"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    
@app.get("/autorizados")
async def api_listar_autorizados(_ = Depends(verify_api_key)):
    data = listar_vehiculos_autorizados()
    return {"status": "success", "data": data}

@app.post("/autorizados")
async def api_añadir_autorizado(matricula: str = Form(...), _ = Depends(verify_api_key)):
    res = insertar_vehiculo_autorizado(matricula)
    if res:
        return {"status": "success", "message": "Matrícula autorizada"}
    return {"status": "exists", "message": "La matrícula ya estaba autorizada"}

@app.delete("/autorizados/{matricula}")
async def api_eliminar_autorizado(matricula: str, _ = Depends(verify_api_key)):
    eliminar_vehiculo_autorizado(matricula)
    return {"status": "success", "message": "Autorización revocada"}