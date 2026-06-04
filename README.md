# Sistema-de-Reconocimiento-Automatico-de-Matriculas

Proyecto fin de grado. Desarrollo de un sistema de reconocimiento automático de matrículas.

## Arquitectura del Sistema

El proyecto implementa una arquitectura **Cliente-Servidor distribuida** y contenerizada, dividida en cuatro componentes principales que se comunican a través de una red local/interna:

1. **Motor de IA (Cliente / Edge):** Ejecuta la detección y OCR aprovechando la aceleración por GPU (CUDA). Envía los resultados mediante HTTP POST a la API.
2. **Gateway API (Servidor / Docker):** Lógica de la aplicación construida con FastAPI.
3. **Base de Datos (Servidor / Docker):** PostgreSQL para el almacenamiento persistente de detecciones, vehículos autorizados e imágenes (BYTEA).
4. **Dashboard (Servidor / Docker):** Interfaz web en Streamlit para la visualización y análisis de datos.

---

## Setup del entorno

### 1. Clonar y configurar variables

Copia el archivo de ejemplo y configura tus credenciales:

```bash
copy .env.example .env
```

**Notas:**

- Configurar `API_URL` en base a la IP del servidor.
- La `API_KEY` debe ser la misma en cliente y servidor.

### 2. Configurar variables de autenticación del dashboard

Copia el archivo de ejemplo y configura tus credenciales:

```bash
copy src\dashboard\config_auth.yaml.example src\dashboard\config_auth.yaml
```

Para crear una contraseña hasheada puedes usar el script `cont_generator.py` cambiando la variable `password` por la que se desee. Al iniciar sesión, se solicitará esa contraseña junto con el usuario configurado en el `.yaml` (por defecto, `admin`).

### 3. Levantar la infraestructura (Docker)

Con Docker Desktop instalado e iniciado, ejecuta el siguiente comando en el servidor:

```bash
docker-compose up -d --build
```

*Esto levantará la base de datos (puerto 5433), FastAPI (puerto 8000) y el Dashboard (puerto 8501).*

Para detener o eliminar los contenedores:

```bash
docker-compose stop     # detener los contenedores
docker-compose down     # borrar contenedores sin borrar datos
docker-compose down -v  # borrar contenedores y datos
```

### 4. Configurar el Motor de IA (local)

1. Crear entorno virtual con Python 3.10:

```bash
py -3.10 -m venv venv
venv\Scripts\activate
```

2. Instalar PyTorch desde https://pytorch.org/get-started/locally/

Ejemplo para GPU (CUDA 13.0):

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
```

Ejemplo para CPU:

```bash
pip install torch torchvision
```

3. Instalar el resto de dependencias:

```bash
pip install -r requirements.txt
```

---

## Uso del sistema

### En el servidor

Asegúrate de que los contenedores de Docker están activos:

```bash
docker-compose up -d
```

Para acceder al dashboard abre un navegador e introduce: <http://ip_del_servidor:8501> (o <http://localhost:8501> si estás en el propio servidor).

### En el cliente

Con el entorno virtual activado, navega a la carpeta del motor y ejecútalo:

```bash
cd src\motor
python main.py
```

---

## Base de datos

La base de datos se inicializa automáticamente al levantar Docker gracias al script `db/schema.sql`.

- **Persistencia:** Los datos se guardan en el volumen de Docker `postgres_data`.
- **Imágenes:** Los recortes de las matrículas se almacenan como BYTEA y se visualizan directamente en el Dashboard.
- El archivo `schema.sql` añade una cámara por defecto a la base de datos. En las variables de entorno se emplea esta cámara (ID=1) para el motor. **Importante modificar esto en base a las necesidades.**

---

## Hardware usado

GPU: NVIDIA GeForce RTX 2060 SUPER (compatible con CUDA)
