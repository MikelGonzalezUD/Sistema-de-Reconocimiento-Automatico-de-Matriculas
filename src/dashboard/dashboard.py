import os
import requests
import streamlit as st
import pandas as pd
import psycopg2
import cv2
import numpy as np
from PIL import Image
import sys
from pathlib import Path
from streamlit_autorefresh import st_autorefresh
import streamlit_authenticator as stauth
from yaml import SafeLoader
import yaml

count = st_autorefresh(interval=10000, limit=100, key="fscounter")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from config import DB_NAME, DB_PORT, DB_USER, DB_PASSWORD, DB_HOST, API_KEY
except ImportError as e:
    print(f"Error fatal: No se encuentra config.py. {e}")
    
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

# 1. Cargar configuración de usuarios
with open('src/dashboard/config_auth.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)
    
# 2. Inicializar el objeto authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)  

# 3. Renderizar el formulario de Login
name, authentication_status, username = authenticator.login('main')

if authentication_status:
    
    st.title("Sistema de monitorización (ALPR)")
    st.markdown("Visualización en tiempo real de los accesos detectados.")
    
    authenticator.logout('Cerrar sesión', 'sidebar')
    st.sidebar.write(f'Bienvenido, *{name}*')

    # CREAR TABS 
    tab_general_data, tab_analytics, tab_admin = st.tabs(["Resumen de accesos", "Analisis de Datos", "Administración"])

    # CONFIGURACIÓN DE LA PÁGINA 
    st.set_page_config(page_title="ALPR Dashboard", layout="wide")


    # LÓGICA DEL DASHBOARD 
    data = get_data()

    data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')
    data['hour'] = data['timestamp'].dt.hour

    # FILTROS DE BUSQUEDA EN LA BARRA LATERAL
    st.sidebar.header("Filtros de Búsqueda")

    # Filtro por matrícula
    search_plate = st.sidebar.text_input("Buscar matrículas (sin espacios)", "").upper()

    # Filtro por rango de fechas
    temp_data = data.dropna(subset=['timestamp'])

    if not temp_data.empty:
        min_date = data['timestamp'].min().date()
        max_date = data['timestamp'].max().date()
        date_range = st.sidebar.date_input("Rango de fechas", [min_date, max_date]) 
    else:
        st.sidebar.warning("Esperando datos con fecha válida...")
        date_range = []

    # Aplicar filtros al dataframe
    if search_plate:
        data = data[data['matricula'].str.contains(search_plate)]

    if len(date_range) == 2:
        data = data[(data['timestamp'].dt.date >= date_range[0]) & (data['timestamp'].dt.date <= date_range[1])]


    with tab_general_data:
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
                                st.image(img_rgb, width='stretch')
                            
                            # 2. Mostrar Info
                            st.write(f"**Matrícula:** {row['matricula']} ({row['pais']})")
                            st.write(f"📅 {row['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}")
                            st.write(f"🎯 Confianza: **{row['confianza']}%**")
                            st.write("---")
        else:
            st.warning("No hay datos registrados en la base de datos aún.")
            
    with tab_analytics:
        if data.empty:
            st.warning("Aplica filtros menos restrictivos para ver estadísticas.")
        else:
            st.subheader("Estadísticas Avanzadas")
            
            #Datos generales
            k1, k2, k3 = st.columns(3)
            k1.metric("Vehículos únicos", data["matricula"].nunique())
            k2.metric("Confianza media", f"{data['confianza'].mean():.1f}%")
            k3.metric("Países detectados", data["pais"].nunique())
            
            st.divider()
            
            col_pie, col_hist = st.columns([1, 2])
            
            with col_pie:
                st.write("**Distribución por País**")
                country_counts = data['pais'].value_counts()
                # Gráfico de tarta
                st.write(country_counts) 
                # Si quieres algo visual sin librerías extra:
                st.bar_chart(country_counts)

            with col_hist:
                st.write("**Detecciones por Franja Horaria**")
                all_hours = pd.DataFrame({'hour': range(24)})
                hour_counts = data.groupby('hour').size().reset_index(name='counts')
                chart_data = all_hours.merge(hour_counts, on='hour', how='left').fillna(0)
                
                st.area_chart(chart_data.set_index('hour'))
            
            st.divider()
            
            #Frecuencia por matricula
            freq = data['matricula'].value_counts().reset_index()
            freq.columns = ['matricula', 'frecuencia']

            st.subheader("Matrículas más detectadas")
            st.bar_chart(freq.set_index('matricula').head(10), sort=False)

            st.divider()
            
            # Mapa de calor de actividad (Día de la semana vs Hora)
            st.write("**Actividad Semanal**")
            data['day_name'] = data['timestamp'].dt.day_name()
            # Ordenar días
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heatmap_data = data.groupby(['day_name', 'hour']).size().unstack(fill_value=0)
            # Reordenar filas
            heatmap_data = heatmap_data.reindex(days_order)
            
            st.dataframe(heatmap_data.style.background_gradient(cmap="YlGnBu"), width='stretch')
            
    with tab_admin:
        st.header("Gestión de Cámaras")
        st.subheader("Cámaras Registradas")
        
        headers = {'x-api-key': API_KEY}
        
        try:
            response = requests.get("http://api:8000/camaras", headers=headers)
            
            if response.status_code == 200:
                lista_camaras = response.json()['data']
                if lista_camaras:
                    # Convertimos el JSON de la API a un DataFrame de Pandas para mostrarlo bonito
                    df_visual = pd.DataFrame(lista_camaras)
                    st.dataframe(df_visual, width='stretch')
                else:
                    st.info("No hay cámaras registradas.")
            else:
                st.error("Error al obtener cámaras de la API")
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            
        st.write("---")
        
        with st.form("registro_camara"):
            ubicacion = st.text_input("Ubicación exacta")
            modelo = st.text_input("Modelo de cámara")
            btn_guardar = st.form_submit_button("Registrar nueva cámara")
            
            if btn_guardar:
                payload = {'ubicacion': ubicacion, 'modelo': modelo}
                response = requests.post("http://api:8000/camaras", data=payload, headers=headers)
                if response.status_code == 200:
                    st.success("¡Cámara registrada!")

    # Botón para refrescar manualmente
    if st.button('Actualizar Datos'):
        st.rerun()
        
elif authentication_status is False:
    st.error('Usuario o contraseña incorrectos')
elif authentication_status is None:
    st.warning('Por favor, introduce tu usuario y contraseña')