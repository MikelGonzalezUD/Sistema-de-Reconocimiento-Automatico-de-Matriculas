from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

ROOT_DIR = Path(__file__).parent.resolve()


YAML_PATH = ROOT_DIR / os.getenv("DATASET_YAML_PATH")
CUSTOM_MODEL_WEIGHTS_PATH = ROOT_DIR / os.getenv("CUSTOM_MODEL_WEIGHTS_PATH")
OCR_MODEL_WEIGHTS_PATH = ROOT_DIR / os.getenv("OCR_MODEL_WEIGHTS_PATH")

DB_NAME = ROOT_DIR / os.getenv("DB_NAME")
DB_USER = ROOT_DIR / os.getenv("DB_USER")
DB_PASSWORD = ROOT_DIR / os.getenv("DB_PASSWORD")
DB_HOST = ROOT_DIR / os.getenv("DB_HOST")
DB_PORT = ROOT_DIR / os.getenv("DB_PORT")