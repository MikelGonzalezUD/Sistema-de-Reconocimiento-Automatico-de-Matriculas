# Sistema-de-Reconocimiento-Automatico-de-Matriculas

Proyecto fin de grado. Desarrollo de un sistema de reconocimiento automático de matrículas.

## Arquitectura del Sistema

El sistema se divide en tres componentes principales:

1. **Motor de IA (Local):** Ejecuta la detección y OCR aprovechando la aceleración por GPU (CUDA).
2. **Base de Datos (Docker):** PostgreSQL para el almacenamiento persistente de detecciones e imágenes (BYTEA).
3. **Dashboard (Docker):** Interfaz web en Streamlit para la visualización y análisis de datos.

---

## Setup del entorno

### 1. Clonar y configurar variables

Copia el archivo de ejemplo y configura tus credenciales:

```bash
cp .env.example .env
```

### 2. Levantar Infraestructura (Docker)

Con Docker Desktop instalado y en ejecución haz:

*Esto levantará la base de datos (puerto 5433) y el Dashboard (puerto 8501).*

```bash
docker-compose up -d
```

(*)Para finalizar la ejecución

```bash
docker-compose stop     #Para detener los contenedores
docker-compose down     #Borrar contenedores sin borrar datos
docker-compose down -v  #Borrar contenedores Y datos
```

### 3. Configurar el Motor de IA (Local)

1. Crear venv:

```bash
python -m venv venv
venv\Scripts\activate     # Windows
```

2. Instalar pytorch CUDA 13.0

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
```

3. Instalar el resto de dependencias

```bash
pip install -r requirements.txt
```

---

## Uso del sistema

1. Ejecutar el motor:

```bash
python main.py
```

2. Acceder al dashboard:

Abre en tu navegador: http://localhost:8501

---

## Base de datos

La base de datos se inicializa automáticamente al levantar Docker gracias al script db/schema.sql.

- Persistencia: Los datos se guardan en el volumen de Docker postgres_data.
- Imágenes: Los recortes de las matrículas se almacenan como BYTEA y se visualizan directamente en el Dashboard.

---

## Hardware usado

GPU: NVIDIA GeForce RTX 2060 SUPER (Compatible con CUDA)
