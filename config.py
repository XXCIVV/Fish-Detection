from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    # App
    APP_NAME: str = "Fish Species Detection App"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"
    ALLOWED_ORIGIN: str = "https://*"
    MAX_STREAM_FPS: int = 5

    # Model
    MODEL_PATH: str = "app/model/best.pt"
    CONFIDENCE_THRESHOLD: float = 0.4
    SAVE_DETECTIONS_IMAGES: bool = False
    IMG_SIZE: int = 640

    # File storage
    UPLOAD_FOLDER: str = "app/static/uploads"
    OUTPUT_FOLDER: str = "app/static/outputs"

    # Database
    DATABASE_URL: str = "postgresql://postgres:Tomon230547@localhost:5432/fish_species_db"

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        extra = "ignore"
    )

    def init_dirs(self):
        Path(self.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
        Path(self.OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

# สร้าง instance ตัวเดียวเพื่อใช้ทั้งโปรเจกต์
config = Config()