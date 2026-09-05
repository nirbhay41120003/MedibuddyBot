from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "policies" / "sops.yaml"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
USE_GROQ_INTENT = os.getenv("USE_GROQ_INTENT", "false").lower() == "true"
GROQ_MODEL = "openai/gpt-oss-20b"
