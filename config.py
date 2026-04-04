from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

ROOT_DIR = Path(__file__).parent.resolve()

#DATASET & TRAINING
YAML_PATH = ROOT_DIR / os.getenv("DATASET_YAML_PATH")
CUSTOM_MODEL_WEIGHTS_PATH = ROOT_DIR / os.getenv("CUSTOM_MODEL_WEIGHTS_PATH")
OCR_MODEL_WEIGHTS_PATH = ROOT_DIR / os.getenv("OCR_MODEL_WEIGHTS_PATH")

#DATABASE
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

#MAIN
LP_MODEL_PATH = ROOT_DIR / os.getenv("LP_MODEL_PATH")
OCR_MODEL_PATH = ROOT_DIR / os.getenv("OCR_MODEL_PATH")