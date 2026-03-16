from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

ROOT_DIR = Path(__file__).parent.resolve()


YAML_PATH = ROOT_DIR / os.getenv("DATASET_YAML_PATH")
CUSTOM_MODEL_WEIGHTS_PATH = ROOT_DIR / os.getenv("CUSTOM_MODEL_WEIGHTS_PATH")
OCR_MODEL_WEIGHTS_PATH = ROOT_DIR / os.getenv("OCR_MODEL_WEIGHTS_PATH")