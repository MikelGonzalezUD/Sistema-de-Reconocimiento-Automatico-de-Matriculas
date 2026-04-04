# Sistema-de-Reconocimiento-Automatico-de-Matriculas

Proyecto fin de grado. Desarrollo de un sistema de reconocimiento automático de matrículas.

## Setup del entorno

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

### Hardware usado

GPU: NVIDIA GeForce RTX 2060 SUPER

### Base de datos

Para este proyecto se ha usado postgresql.

1. Configurar el servicio de postgres con los datos adecuados:
    - Usuario
    - Nombre de la base de datos
    - Contrsaeña

2. Cambiar el .env con los nuevos datos

3. Ejecutar el script *init_db.py* para la inicialización de las tablas. (*)Modifica el archivo *schema.sql* para agregar las camaras necesarias a la base de datos.

```bash
python init_db.py #Desde el directorio db
```

El código principal guarda los crops de las matrículas en la base de datos como BYTEA. Para visualizar las imagenes, hacer uso de la función **recuperar_y_mostrar(acceso_id)** de *db_manager.py*.
