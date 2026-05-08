import psycopg2
import cv2
import numpy as np
import sys
from pathlib import Path

root_path = Path.cwd().parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from config import DB_NAME, DB_PORT, DB_USER, DB_PASSWORD, DB_HOST

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def insertar_deteccion(matricula, pais, confianza, imagen_np, camara_id):
    """
    Inserta o actualiza el vehículo y registra el acceso con la imagen en BYTEA.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Insertar o recuperar el vehiculo_id
        # ON CONFLICT para que si ya existe, no haga nada pero nos devuelva el ID
        cur.execute("""
            INSERT INTO vehiculos (matricula, pais)
            VALUES (%s, %s)
            ON CONFLICT (matricula) DO UPDATE SET pais = EXCLUDED.pais
            RETURNING vehiculo_id;
        """, (matricula.upper(), pais.upper()))
        
        vehiculo_id = cur.fetchone()[0]

        # Convertir imagen OpenCV (numpy) a bytes para BYTEA
        success, encoded_image = cv2.imencode('.jpg', imagen_np)
        if not success:
            return False
        content = encoded_image.tobytes()

        # Insertar el acceso
        cur.execute("""
            INSERT INTO accesos (vehiculo_id, camara_id, confianza, matricula_img, autorizado)
            VALUES (%s, %s, %s, %s, (SELECT EXISTS(SELECT 1 FROM autorizados WHERE matricula = %s)))
        """, (vehiculo_id, camara_id, confianza, psycopg2.Binary(content), matricula.upper()))

        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"❌ Error en DB: {e}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()
        
      
def recuperar_y_mostrar(acceso_id):
    """
    Obtener la imagen de un acceso específico y mostrarla  
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Pedimos los bytes de la imagen
    cur.execute("SELECT matricula_img FROM accesos WHERE acceso_id = %s", (acceso_id,))
    res = cur.fetchone()
    
    if res and res[0]:
        # Convertir los bytes de Postgres a un array de numpy
        nparr = np.frombuffer(res[0], np.uint8)
        # Decodificar la imagen
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        cv2.imshow(f"Acceso ID: {acceso_id}", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("No se encontró la imagen.")
    
    cur.close()
    conn.close()


def insertar_camara(ubicacion, modelo):
    """
    Inserta una nueva cámara en la base de datos y devuelve su ID.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO camaras (ubicacion, modelo)
            VALUES (%s, %s)
            RETURNING camara_id;
        """, (ubicacion, modelo))
        camara_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return camara_id
    except Exception as e:
        print(f"Error insertando cámara: {e}")
        if conn: conn.rollback()
        return None
    finally:
        if conn: conn.close()
        
def listar_camaras():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT camara_id, ubicacion, modelo FROM camaras ORDER BY camara_id DESC;")
        rows = cur.fetchall()
        
        camaras = []
        for r in rows:
            camaras.append({
                "id": r[0],
                "ubicacion": r[1],
                "modelo": r[2]
            })
        return camaras
    finally:
        if conn: conn.close()
        
        
def listar_vehiculos_autorizados():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT autorizado_id, matricula, fecha_alta FROM autorizados ORDER BY fecha_alta DESC;")
        rows = cur.fetchall()
        return [{"id": r[0], "matricula": r[1], "fecha": r[2].strftime("%Y-%m-%d %H:%M:%S")} for r in rows]
    finally:
        if conn: conn.close()
        
        
def insertar_vehiculo_autorizado(matricula):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO autorizados (matricula) VALUES (%s) ON CONFLICT DO NOTHING RETURNING autorizado_id;", (matricula.upper(),))
        result = cur.fetchone()
        conn.commit()
        return result[0] if result else None
    except Exception as e:
        if conn: conn.rollback()
        raise e
    finally:
        if conn: conn.close()
        
def eliminar_vehiculo_autorizado(matricula):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM autorizados WHERE matricula = %s;", (matricula.upper(),))
        conn.commit()
        return True
    finally:
        if conn: conn.close()