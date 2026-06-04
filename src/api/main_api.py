from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Depends
import cv2
import numpy as np
import uvicorn
from src.database.db_manager import insertar_deteccion, listar_accesos_deshautorizados, listar_todos_accesos, listar_camaras, insertar_camara, eliminar_camara, listar_vehiculos_autorizados, insertar_vehiculo_autorizado, eliminar_vehiculo_autorizado
from src.motor.utils import validate_plate, load_patterns, alerta_telegram
import os
import sys
from fastapi import BackgroundTasks

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from config import API_KEY, TELEGRAM_BOT_TOKEN, CHAT_ID
except ImportError as e:
    print(f"Error fatal: No se encuentra config.py. {e}")

app = FastAPI(title="ALPR API Gateway")
patterns = load_patterns("src/motor/patrones.json")


# AUTENTICACIÓN

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="No autorizado: API Key inválida")
    return x_api_key


# ENDPOINTS

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
    background_tasks: BackgroundTasks = BackgroundTasks(),
    token: str = Depends(verify_api_key)
):
    try:
        image_bytes = await imagen.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Imagen inválida")

        resultado_db = insertar_deteccion(matricula, pais, confianza, img, camara_id)

        if resultado_db and resultado_db["success"]:
            es_autorizado = resultado_db["autorizado"]

            if not es_autorizado:
                print(f"🚨 Alerta: Matrícula {matricula} NO autorizada. Notificando...")
                background_tasks.add_task(alerta_telegram, matricula, camara_id, TELEGRAM_BOT_TOKEN, CHAT_ID)
            else:
                print(f"✅ Acceso correcto: Matrícula {matricula} autorizada.")

            return {"status": "success", "message": f"Matrícula {matricula} registrada", "autorizado": es_autorizado}
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


@app.delete("/camaras/{camara_id}")
async def api_eliminar_camara(camara_id: int, _ = Depends(verify_api_key)):
    res = eliminar_camara(camara_id)
    if res:
        return {"status": "success", "message": "Cámara eliminada"}
    raise HTTPException(status_code=404, detail="ID de cámara no encontrado en la base de datos")


@app.get("/autorizados")
async def api_listar_autorizados(_ = Depends(verify_api_key)):
    data = listar_vehiculos_autorizados()
    return {"status": "success", "data": data}


@app.post("/autorizados")
async def api_añadir_autorizado(matricula: str = Form(...), _ = Depends(verify_api_key)):
    pais = validate_plate(matricula, patterns=patterns)
    if pais:
        res = insertar_vehiculo_autorizado(matricula)
        if res:
            return {"status": "success", "message": "Matrícula autorizada"}
        return {"status": "exists", "message": "La matrícula ya estaba autorizada"}
    raise HTTPException(status_code=400, detail="Formato de matrícula no válido. Debe cumplir los patrones de España, Francia o Finlandia.")


@app.delete("/autorizados/{matricula}")
async def api_eliminar_autorizado(matricula: str, _ = Depends(verify_api_key)):
    eliminar_vehiculo_autorizado(matricula)
    return {"status": "success", "message": "Autorización revocada"}


@app.get("/accesos")
async def api_listar_accesos(_ = Depends(verify_api_key)):
    data = listar_todos_accesos()
    return {"status": "success", "data": data}


@app.get("/incidencias")
async def api_listar_incidencias(_ = Depends(verify_api_key)):
    data = listar_accesos_deshautorizados()
    return {"status": "success", "data": data}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
