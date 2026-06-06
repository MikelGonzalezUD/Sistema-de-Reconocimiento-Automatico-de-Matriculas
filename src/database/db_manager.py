import psycopg2
import cv2
import numpy as np
import sys
import base64
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
    """Inserta o actualiza el vehículo y registra el acceso con la imagen."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # upsert del vehículo para obtener su ID
        cur.execute("""
            INSERT INTO vehiculos (matricula, pais)
            VALUES (%s, %s)
            ON CONFLICT (matricula) DO UPDATE SET pais = EXCLUDED.pais
            RETURNING vehiculo_id;
        """, (matricula.upper(), pais.upper()))
        vehiculo_id = cur.fetchone()[0]

        # la imagen se almacena como BYTEA en la BD
        success, encoded_image = cv2.imencode('.jpg', imagen_np)
        if not success:
            return {"success": False, "autorizado": False}
        content = encoded_image.tobytes()

        cur.execute("""
            INSERT INTO accesos (vehiculo_id, camara_id, confianza, matricula_img, autorizado)
            VALUES (%s, %s, %s, %s, (SELECT EXISTS(SELECT 1 FROM autorizados WHERE matricula = %s)))
            RETURNING autorizado;
        """, (vehiculo_id, camara_id, confianza, psycopg2.Binary(content), matricula.upper()))
        es_autorizado = cur.fetchone()[0]

        conn.commit()
        cur.close()
        return {"success": True, "autorizado": es_autorizado}
    except Exception as e:
        print(f"Error en DB: {e}")
        if conn: conn.rollback()
        return {"success": False, "autorizado": False}
    finally:
        if conn: conn.close()


def recuperar_y_mostrar(acceso_id):
    """Recupera y muestra la imagen asociada a un acceso."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT matricula_img FROM accesos WHERE acceso_id = %s", (acceso_id,))
    res = cur.fetchone()

    if res and res[0]:
        nparr = np.frombuffer(res[0], np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        cv2.imshow(f"Acceso ID: {acceso_id}", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("No se encontró la imagen.")

    cur.close()
    conn.close()


# CÁMARAS

def insertar_camara(ubicacion, modelo):
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
        return [{"id": r[0], "ubicacion": r[1], "modelo": r[2]} for r in rows]
    finally:
        if conn: conn.close()


def eliminar_camara(camara_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM camaras WHERE camara_id = %s;", (camara_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        if conn: conn.close()


# VEHÍCULOS AUTORIZADOS

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
        cur.execute(
            "INSERT INTO autorizados (matricula) VALUES (%s) ON CONFLICT DO NOTHING RETURNING autorizado_id;",
            (matricula.upper(),)
        )
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
        return cur.rowcount > 0
    finally:
        if conn: conn.close()


# ACCESOS

def limpiar_imagenes_antiguas(dias: int = 30) -> int:
    """Elimina las imágenes de matrículas con más de `dias` días para cumplir con la LOPD."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE accesos
            SET matricula_img = NULL
            WHERE matricula_img IS NOT NULL
              AND timestamp < NOW() - INTERVAL '%s days';
        """, (dias,))
        conn.commit()
        return cur.rowcount
    except Exception as e:
        print(f"Error limpiando imágenes antiguas: {e}")
        if conn: conn.rollback()
        return 0
    finally:
        if conn: conn.close()


def listar_todos_accesos():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT a.acceso_id, v.matricula, v.pais, c.ubicacion, a.timestamp, a.confianza, a.autorizado
            FROM accesos a
            JOIN vehiculos v ON a.vehiculo_id = v.vehiculo_id
            JOIN camaras c ON a.camara_id = c.camara_id
            ORDER BY a.timestamp DESC;
        """)
        rows = cur.fetchall()
        return [
            {
                "acceso_id": r[0],
                "matricula": r[1],
                "pais": r[2],
                "ubicacion": r[3],
                "fecha_hora": r[4].strftime("%Y-%m-%d %H:%M:%S"),
                "confianza": float(r[5]) if r[5] is not None else None,
                "autorizado": r[6]
            }
            for r in rows
        ]
    finally:
        if conn: conn.close()


def listar_accesos_deshautorizados():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT a.acceso_id, v.matricula, c.ubicacion, a.timestamp, a.matricula_img
            FROM accesos a
            JOIN vehiculos v ON a.vehiculo_id = v.vehiculo_id
            JOIN camaras c ON a.camara_id = c.camara_id
            WHERE a.autorizado = FALSE
            ORDER BY a.timestamp DESC;
        """)
        rows = cur.fetchall()

        resultado = []
        for r in rows:
            img_b64 = None
            if r[4] is not None:
                bytes_img = r[4].tobytes() if isinstance(r[4], memoryview) else r[4]
                img_b64 = f"data:image/jpeg;base64,{base64.b64encode(bytes_img).decode('utf-8')}"

            resultado.append({
                "acceso_id": r[0],
                "matricula": r[1],
                "ubicacion": r[2],
                "fecha_hora": r[3].strftime("%Y-%m-%d %H:%M:%S"),
                "matricula_img": img_b64
            })
        return resultado
    finally:
        if conn: conn.close()
