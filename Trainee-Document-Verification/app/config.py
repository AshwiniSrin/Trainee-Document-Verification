import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    API_URL = os.getenv("OPENAI_API_BASE") or os.getenv("API_URL") or "https://api.openai.com/v1"
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    MAX_DOCUMENT_SIZE = 5 * 1024 * 1024  # 5 MB
    ALLOWED_FILE_TYPES = ["pdf", "jpg", "png", "docx"]
    LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")