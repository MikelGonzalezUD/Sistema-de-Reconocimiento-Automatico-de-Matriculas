from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

ROOT_DIR = Path(__file__).parent.resolve()

# ENTRENAMIENTO
YAML_PATH = ROOT_DIR / os.getenv("DATASET_YAML_PATH")
CUSTOM_MODEL_WEIGHTS_PATH = ROOT_DIR / os.getenv("CUSTOM_MODEL_WEIGHTS_PATH")
OCR_MODEL_WEIGHTS_PATH = ROOT_DIR / os.getenv("OCR_MODEL_WEIGHTS_PATH")

# BASE DE DATOS
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")

# MOTOR
LP_MODEL_PATH = ROOT_DIR / os.getenv("LP_MODEL_PATH")
OCR_MODEL_PATH = ROOT_DIR / os.getenv("OCR_MODEL_PATH")
CAMERA_ID = int(os.getenv("CAMERA_ID", 1))

# API
API_URL = os.getenv("API_URL", "http://localhost:8000/deteccion")
API_KEY = os.getenv("API_KEY")

# TELEGRAM
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
