import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# โหลด .env เมื่อเริ่มต้นโปรแกรม
load_dotenv()

class Settings(BaseModel):
    gemini_api_key: str | None = Field(alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    gemini_vision_model: str = Field(
        default="gemini-2.5-pro ", alias="GEMINI_VISION_MODEL"
    )

    @classmethod
    def from_env(cls):
        data = {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "GEMINI_VISION_MODEL": os.getenv(
                "GEMINI_VISION_MODEL", "gemini-1.5-pro-vision"
            ),
        }
        return cls.model_validate(data)

settings = Settings.from_env()
