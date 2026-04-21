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

### 2. Clonar y configurar variables de autenticación

Copia el archivo de ejemplo y configura tus credenciales:

```bash
cp .config_auth.yaml.example .config_auth.yaml
```

Para crear una contraseña hasheada se puede el script *cont_generator.py* cambiando la variable password por la que se desee. Al iniciar sesión, se solicitará esa contraseña junto con el user configurado en el .yaml (por defecto, admin).

### 3. Levantar Infraestructura (Docker)

Con Docker Desktop instalado y en ejecución haz:

```bash
docker-compose up -d
```

*Esto levantará la base de datos (puerto 5433) y el Dashboard (puerto 8501).*

(*)Para finalizar la ejecución

```bash
docker-compose stop     #Para detener los contenedores
docker-compose down     #Borrar contenedores sin borrar datos
docker-compose down -v  #Borrar contenedores Y datos
```

### 3. Configurar el Motor de IA (Local)

1. Crear venv (python 3.10):

```bash
py -3.10 -m venv venv
venv\Scripts\activate     # Windows
```

2. Comando para instalar pytorch desde el siguiente link: https://pytorch.org/get-started/locally/

Ejemplo de instalación para CUDA 13 (GPU)

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
```

Ejemplo de instalación para CPU

```bash
pip install torch torchvision
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

EL archivo schema.sql añade una cámara deafult a la base de datos, **importante modificar esto en base a las necesidades**

---

## Hardware usado

GPU: NVIDIA GeForce RTX 2060 SUPER (Compatible con CUDA)
