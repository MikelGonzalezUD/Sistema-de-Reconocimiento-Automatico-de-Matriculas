import base64
import os
import time
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

# CONFIGURACIÓN
st.set_page_config(page_title="ALPR Dashboard", layout="wide")

count = st_autorefresh(interval=10000, key="fscounter")

if "ultimo_id_incidencia" not in st.session_state:
    st.session_state.ultimo_id_incidencia = None

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from config import DB_NAME, DB_PORT, DB_USER, DB_PASSWORD, DB_HOST, API_KEY
except ImportError as e:
    print(f"Error fatal: No se encuentra config.py. {e}")


# CONEXIÓN A BASE DE DATOS

def get_data():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            host=DB_HOST, port=DB_PORT
        )
        query = """
            SELECT
                v.matricula,
                CASE WHEN a.autorizado THEN '✅ SI' ELSE '❌ NO' END as "Permitido",
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


def get_total_accesos():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            host=DB_HOST, port=DB_PORT
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM accesos;")
        total = cur.fetchone()[0]
        conn.close()
        return total
    except Exception:
        return None


# AUTENTICACIÓN

with open('src/dashboard/config_auth.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

name, authentication_status, username = authenticator.login('main')

if authentication_status:

    st.title("Sistema de monitorización (ALPR)")
    st.markdown("Visualización en tiempo real de los accesos detectados.")

    authenticator.logout('Cerrar sesión', 'sidebar')
    st.sidebar.write(f'Bienvenido, *{name}*')

    tab_general_data, tab_analytics, tab_admin = st.tabs(["Resumen de accesos", "Analisis de Datos", "Administración"])

    # DATOS
    data = get_data()

    if data is None:
        st.error("No se pudo conectar a la base de datos. Comprueba la conexión.")
        st.stop()

    data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')
    data['hour'] = data['timestamp'].dt.hour

    # FILTROS
    st.sidebar.header("Filtros de Búsqueda")

    search_plate = st.sidebar.text_input("Buscar matrículas (sin espacios)", "").upper()

    temp_data = data.dropna(subset=['timestamp'])
    if not temp_data.empty:
        min_date = data['timestamp'].min().date()
        max_date = data['timestamp'].max().date()
        date_range = st.sidebar.date_input("Rango de fechas", [min_date, max_date])
    else:
        st.sidebar.warning("Esperando datos con fecha válida...")
        date_range = []

    if search_plate:
        data = data[data['matricula'].str.contains(search_plate)]

    if len(date_range) == 2:
        data = data[(data['timestamp'].dt.date >= date_range[0]) & (data['timestamp'].dt.date <= date_range[1])]


    with tab_general_data:
        if data is not None and not data.empty:
            col1, col2 = st.columns(2)
            col1.metric("Total Accesos", get_total_accesos())
            col2.metric("Última Matrícula", data.iloc[0]['matricula'])

            st.write("---")
            st.subheader("Últimas Detecciones (50)")

            for i in range(0, len(data), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(data):
                        row = data.iloc[i + j]
                        with cols[j]:
                            if row['matricula_img'] is not None:
                                nparr = np.frombuffer(row['matricula_img'], np.uint8)
                                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                                st.image(img_rgb, width='stretch')

                            st.write(f"**Matrícula:** {row['matricula']} ({row['pais']})")
                            st.write(f"📅 {row['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}")
                            st.write(f"🎯 Confianza: **{row['confianza']}%**")
                            st.write(f"Permitido: {row['Permitido']}")
                            st.write("---")
        else:
            st.warning("No hay datos registrados en la base de datos aún.")

    with tab_analytics:
        if data.empty:
            st.warning("Aplica filtros menos restrictivos para ver estadísticas.")
        else:
            st.subheader("Estadísticas Avanzadas")

            total_accesos = len(data)
            no_autorizados = len(data[data['Permitido'] == '❌ NO'])
            porcentaje_no_auth = (no_autorizados / total_accesos * 100) if total_accesos > 0 else 0

            # MÉTRICAS
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Vehículos únicos", data["matricula"].nunique())
            k2.metric("Confianza media", f"{data['confianza'].mean():.1f}%")
            k3.metric("Países detectados", data["pais"].nunique())
            # delta_color="inverse" para que el porcentaje de no autorizados aparezca en rojo
            k4.metric(
                label="Accesos NO autorizados",
                value=f"{no_autorizados}",
                delta=f"{porcentaje_no_auth:.1f}% del total",
                delta_color="inverse"
            )

            st.divider()

            # GRÁFICOS
            col_pie, col_hist = st.columns([1, 2])
            with col_pie:
                st.write("**Distribución por País**")
                country_counts = data['pais'].value_counts()
                st.bar_chart(country_counts)

            with col_hist:
                st.write("**Detecciones por Franja Horaria**")
                all_hours = pd.DataFrame({'hour': range(24)})
                hour_counts = data.groupby('hour').size().reset_index(name='counts')
                chart_data = all_hours.merge(hour_counts, on='hour', how='left').fillna(0)
                st.area_chart(chart_data.set_index('hour'))

            st.divider()

            freq = data['matricula'].value_counts().reset_index()
            freq.columns = ['matricula', 'frecuencia']
            st.subheader("Matrículas más detectadas")
            st.bar_chart(freq.set_index('matricula').head(10), sort=False)

            st.divider()

            # MAPA DE CALOR SEMANAL
            st.write("**Actividad Semanal**")
            if data['timestamp'].dt.tz is None:
                data['timestamp'] = data['timestamp'].dt.tz_localize('UTC')

            data['timestamp_madrid'] = data['timestamp'].dt.tz_convert('Europe/Madrid')
            data['hora_local'] = data['timestamp_madrid'].dt.hour
            data['day_name'] = data['timestamp_madrid'].dt.day_name()

            heatmap_data = data.groupby(['day_name', 'hora_local']).size().unstack(fill_value=0)
            heatmap_data = heatmap_data.reindex(columns=list(range(24)), fill_value=0)

            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            days_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            heatmap_data = heatmap_data.reindex(days_order).fillna(0)
            heatmap_data.index = days_es

            heatmap_data_transposed = heatmap_data.T.astype(int)

            st.dataframe(
                heatmap_data_transposed.style.background_gradient(cmap="YlGnBu").format("{:d}"),
                width='stretch',
                height=500  # altura fija para mostrar las 24 horas sin scroll externo
            )

    with tab_admin:
        st.header("Panel de Administración")
        headers = {'x-api-key': API_KEY}

        subtab_camaras, subtab_autorizados, subtab_incidencias, subtab_registros = st.tabs(
            ["Gestión de cámaras", "Lista de autorizados", "Incidencias", "Exportar registros"]
        )

        with subtab_camaras:
            st.subheader("Gestión de cámaras registradas")
            st.write("Formulario para registrar nueva cámara:")

            with st.form("registro_camara"):
                ubicacion = st.text_input("Ubicación exacta")
                modelo = st.text_input("Modelo de cámara")
                btn_guardar = st.form_submit_button("Registrar nueva cámara")

                if btn_guardar:
                    payload = {'ubicacion': ubicacion, 'modelo': modelo}
                    response = requests.post("http://api:8000/camaras", data=payload, headers=headers)
                    if response.status_code == 200:
                        st.success("¡Cámara registrada!")

            st.write("---")
            st.write("Lista de cámaras registradas:")

            try:
                response = requests.get("http://api:8000/camaras", headers=headers)

                if response.status_code == 200:
                    lista_camaras = response.json()['data']
                    if lista_camaras:
                        df_visual = pd.DataFrame(lista_camaras)
                        st.data_editor(
                            df_visual[["ubicacion", "modelo"]],
                            column_config={"ubicacion": "Ubicación", "modelo": "Modelo"},
                            disabled=["ubicacion", "modelo"],
                            hide_index=True,
                            width='stretch'
                        )

                        opciones = {f"{c['ubicacion']} ({c['modelo']})": c['id'] for c in lista_camaras}
                        cam_a_borrar_label = st.selectbox(
                            "Selecciona una cámara para eliminar:",
                            options=list(opciones.keys()),
                            index=None,
                            placeholder="Elige una cámara..."
                        )

                        if st.button("Eliminar cámara seleccionada", type="primary"):
                            if cam_a_borrar_label:
                                id_seleccionado = opciones[cam_a_borrar_label]
                                r = requests.delete(f"http://api:8000/camaras/{id_seleccionado}", headers=headers)
                                if r.status_code == 200:
                                    st.success(f"Cámara '{cam_a_borrar_label}' eliminada.")
                                    st.rerun()
                                else:
                                    st.error(f"Error al eliminar: {r.json().get('detail', 'Error desconocido')}")
                    else:
                        st.info("No hay cámaras registradas.")
                else:
                    st.error("Error al obtener cámaras de la API")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

        with subtab_autorizados:
            st.subheader("Gestión de vehículos autorizados")
            st.write("Añade la matrícula del vehículo que deseas autorizar.")

            col1, col2 = st.columns([2, 1])
            with col1:
                nueva_matricula = st.text_input("➕ Nueva matrícula a autorizar", placeholder="1234ABC").upper()
                nueva_matricula = "".join(nueva_matricula.split())
            with col2:
                st.write(" ")

            if st.button("Confirmar"):
                if nueva_matricula:
                    res = requests.post("http://api:8000/autorizados", data={'matricula': nueva_matricula}, headers=headers)
                    if res.status_code == 200:
                        st.success(f"¡Éxito! Matrícula {nueva_matricula} añadida correctamente.")
                        time.sleep(1)
                        st.rerun()
                    elif res.status_code == 400:
                        st.error(f"Error: Formato de matrícula \"{nueva_matricula}\" no válido.")

            st.write("---")

            try:
                res_list = requests.get("http://api:8000/autorizados", headers=headers)
                if res_list.status_code == 200:
                    lista_auth = res_list.json()['data']
                    if lista_auth:
                        df_auth = pd.DataFrame(lista_auth)
                        df_auth["Eliminar"] = False
                        st.write("Lista de matrículas autorizadas.")

                        edited_df = st.data_editor(
                            df_auth[["matricula", "fecha", "Eliminar"]],
                            column_config={
                                "matricula": "Matrícula Autorizada",
                                "fecha": "Fecha de Alta",
                                "Eliminar": st.column_config.CheckboxColumn(help="Marcar para borrar")
                            },
                            disabled=["matricula", "fecha"],
                            hide_index=True,
                            width='stretch'
                        )

                        seleccionados = edited_df[edited_df["Eliminar"] == True]["matricula"].tolist()
                        if seleccionados:
                            if st.button(f"Eliminar {len(seleccionados)} autorizado(s)", type="primary"):
                                for mat in seleccionados:
                                    requests.delete(f"http://api:8000/autorizados/{mat}", headers=headers)
                                st.success("Registros eliminados correctamente")
                                st.rerun()
                    else:
                        st.info("No hay vehículos autorizados.")
            except Exception as e:
                st.error(f"Error: {e}")

        with subtab_incidencias:
            st.subheader("Incidencias")
            try:
                res_incidencias = requests.get("http://api:8000/incidencias", headers=headers)
                if res_incidencias.status_code == 200:
                    incidencias = res_incidencias.json()['data']
                    st.metric(label="Número de alertas", value=len(incidencias), delta="No autorizados", delta_color="inverse")

                    if incidencias:
                        id_mas_reciente = incidencias[0]['acceso_id']
                        # notificar solo cuando llega una incidencia nueva
                        if st.session_state.ultimo_id_incidencia is not None and id_mas_reciente != st.session_state.ultimo_id_incidencia:
                            st.toast(f"🚨 ¡ALERTA! Vehículo no autorizado detectado en {incidencias[0]['ubicacion']}", icon="🔴")

                        st.session_state.ultimo_id_incidencia = id_mas_reciente

                        df_inc = pd.DataFrame(incidencias)[["fecha_hora", "ubicacion", "matricula", "matricula_img"]]
                        st.dataframe(
                            df_inc,
                            column_config={
                                "fecha_hora": "Fecha y Hora",
                                "ubicacion": "Ubicación / Cámara",
                                "matricula": "Matrícula Detectada",
                                "matricula_img": st.column_config.ImageColumn(
                                    "Captura",
                                    help="Miniatura de la matrícula detectada (Haz clic para ampliar)"
                                )
                            },
                            hide_index=True,
                            width='stretch'
                        )
                    else:
                        st.info("No hay incidencias registradas.")
                else:
                    st.error("Error al obtener incidencias de la API")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

        with subtab_registros:
            st.subheader("Exportar registro de accesos")
            try:
                res_accesos = requests.get("http://api:8000/accesos", headers=headers)
                if res_accesos.status_code == 200:
                    todos_accesos = res_accesos.json()['data']
                    if todos_accesos:
                        df_todos = pd.DataFrame(todos_accesos)
                        df_todos["autorizado"] = df_todos["autorizado"].map({True: "SI", False: "NO"})

                        col_f1, col_f2, col_f3 = st.columns(3)
                        with col_f1:
                            filtro_matricula = st.text_input("Filtrar por matrícula", "", key="exp_matricula").upper()
                        with col_f2:
                            filtro_auth = st.selectbox("Filtrar por autorización", ["Todos", "Autorizados", "No autorizados"], key="exp_auth")
                        with col_f3:
                            filtro_pais = st.selectbox("Filtrar por país", ["Todos"] + sorted(df_todos["pais"].unique().tolist()), key="exp_pais")

                        df_export = df_todos.copy()
                        if filtro_matricula:
                            df_export = df_export[df_export["matricula"].str.contains(filtro_matricula)]
                        if filtro_auth == "Autorizados":
                            df_export = df_export[df_export["autorizado"] == "SI"]
                        elif filtro_auth == "No autorizados":
                            df_export = df_export[df_export["autorizado"] == "NO"]
                        if filtro_pais != "Todos":
                            df_export = df_export[df_export["pais"] == filtro_pais]

                        st.write(f"**{len(df_export)}** registros encontrados (de {len(df_todos)} totales)")

                        st.dataframe(
                            df_export[["acceso_id", "matricula", "pais", "ubicacion", "fecha_hora", "confianza", "autorizado"]],
                            column_config={
                                "acceso_id": "ID",
                                "matricula": "Matrícula",
                                "pais": "País",
                                "ubicacion": "Cámara",
                                "fecha_hora": "Fecha y Hora",
                                "confianza": st.column_config.NumberColumn("Confianza (%)", format="%.1f"),
                                "autorizado": "Autorizado"
                            },
                            hide_index=True,
                            width='stretch'
                        )

                        csv = df_export.drop(columns=["acceso_id"]).to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="Descargar CSV",
                            data=csv,
                            file_name="accesos_alpr.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No hay accesos registrados.")
                else:
                    st.error("Error al obtener los registros de la API")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

        if st.button('Actualizar Datos'):
            st.rerun()

elif authentication_status is False:
    st.error('Usuario o contraseña incorrectos')
elif authentication_status is None:
    st.warning('Por favor, introduce tu usuario y contraseña')
