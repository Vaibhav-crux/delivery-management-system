import os
from dotenv import load_dotenv
from typing import Optional

class Config:
    def __init__(self):
        load_dotenv()
        
        # App Environment
        self.FLASK_ENV = os.getenv("FLASK_ENV", "production")
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        self.PORT = int(os.getenv("PORT", 5000))
        self.HOST = os.getenv("HOST", "127.0.0.1")

        # Secret Key
        self.SECRET_KEY = os.getenv("SECRET_KEY")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_EXPIRATION_TIME = int(os.getenv("JWT_EXPIRATION_TIME", 3600))

        # Database Config
        self.DB_HOST = os.getenv("DB_HOST")
        self.DB_PORT = os.getenv("DB_PORT")
        self.DB_NAME = os.getenv("DB_NAME")
        self.DB_USER = os.getenv("DB_USER")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD")

        # Scheduler Settings
        self.SCHEDULER_API_ENABLED = os.getenv("SCHEDULER_API_ENABLED", "False").lower() == "true"
        self.SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "UTC")

        # Rate Limiting
        self.RATE_LIMIT = os.getenv("RATE_LIMIT", "100 per minute")

        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = os.getenv("LOG_FILE", "app.log")

        # CORS
        self.ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

        # Validate configuration
        self._validate()

    def _validate(self):
        required_fields = [
            "SECRET_KEY", "DB_HOST", "DB_PORT", 
            "DB_NAME", "DB_USER", "DB_PASSWORD"
        ]
        
        for field in required_fields:
            if not getattr(self, field):
                raise ValueError(f"Missing required configuration: {field}")