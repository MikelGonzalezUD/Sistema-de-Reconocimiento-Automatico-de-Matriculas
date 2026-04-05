import os
import streamlit as st
import pandas as pd
import psycopg2
import cv2
import numpy as np
from PIL import Image
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from config import DB_NAME, DB_PORT, DB_USER, DB_PASSWORD, DB_HOST
except ImportError as e:
    print(f"Error fatal: No se encuentra config.py. {e}")

# CONFIGURACIÓN DE LA PÁGINA 
st.set_page_config(page_title="ALPR Dashboard", layout="wide")

st.title("Sistema de monitorización (ALPR)")
st.markdown("Visualización en tiempo real de los accesos detectados.")

# FUNCIÓN DE CONEXIÓN 
def get_data():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, 
            host=DB_HOST, port=DB_PORT
        )
        # Consulta JOIN para tener texto e imagen juntos
        query = """
            SELECT 
                v.matricula, 
                v.pais, 
                a.timestamp, 
                a.confianza, 
                a.matricula_img
            FROM accesos a
            JOIN vehiculos v ON a.vehiculo_id = v.vehiculo_id
            ORDER BY a.timestamp DESC
            LIMIT 50;
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        return None

# LÓGICA DEL DASHBOARD 
data = get_data()

if data is not None and not data.empty:
    # Métricas rápidas en la parte superior
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Accesos", len(data))
    col2.metric("Última Matrícula", data.iloc[0]['matricula'])

    st.write("---")

    # Mostrar los datos en una cuadrícula (Grid)
    st.subheader("Últimas Detecciones")
    
    # Filas de 3 columnas para mostrar las imágenes y datos
    for i in range(0, len(data), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(data):
                row = data.iloc[i + j]
                with cols[j]:
                    # 1. Procesar la imagen BYTEA
                    if row['matricula_img'] is not None:
                        nparr = np.frombuffer(row['matricula_img'], np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        st.image(img_rgb, use_container_width=True)
                    
                    # 2. Mostrar Info
                    st.write(f"**Matrícula:** {row['matricula']} ({row['pais']})")
                    st.write(f"📅 {row['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}")
                    st.write(f"🎯 Confianza: **{row['confianza']}%**")
                    st.write("---")
else:
    st.warning("No hay datos registrados en la base de datos aún.")

# Botón para refrescar manualmente
if st.button('Actualizar Datos'):
    st.rerun()