# SCRIPT OBSOLETO - SE DEJA SOLO COMO REFERENCIA PARA CREAR LA BASE DE DATOS Y LAS TABLAS, PERO NO SE EJECUTARÁ DESDE EL PROYECTO
# PARA INICIALIZAR LA BASE DE DATOS, SE EMPLEA DOCKER COMPOSE

import psycopg2
import sys
from pathlib import Path

root_path = Path.cwd().parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from config import DB_NAME, DB_PORT, DB_USER, DB_PASSWORD, DB_HOST

try:
    with psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    ) as conn:
        with conn.cursor() as cur:
            with open("schema.sql", "r") as f:
                cur.execute(f.read())

    print("Tablas creadas correctamente")

except Exception as e:
    print(f"Error al crear tablas: {e}")