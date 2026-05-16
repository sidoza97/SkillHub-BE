from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HF_TOKEN: str = ""
    HF_MODEL: str = "deepseek-ai/DeepSeek-V4-Pro:novita"
    HF_BASE_URL: str = "https://router.huggingface.co/v1"

    GEMMA_API_KEY: str = ""
    GEMMA_ENDPOINT: str = ""
    GEMMA_API_VERSION: str = "2024-05-01-preview"
    GEMMA_DEPLOYMENT: str = "gpt-4.1"

    LLAMA_MODEL: str = "meta-llama/Meta-Llama-3-8B-Instruct:novita"

    SECRET_KEY: str = "skillshub-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    DATABASE_URL: str = "sqlite:///./skillshub.db"
    CHROMA_PATH: str = "./chroma_db"

    class Config:
        env_file = ".env"


settings = Settings()
