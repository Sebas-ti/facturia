from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path, not "../.env": a relative path is resolved against the
# current working directory, which breaks whenever something (evals/, a
# script run from the repo root) doesn't `cd backend` first.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "local"
    database_url: str = "postgresql+psycopg://facturia:facturia@localhost:5432/facturia"
    azure_storage_connection_string: str = (
        "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/"
        "K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )
    api_key: str = "change-me"

    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-08-01-preview"


settings = Settings()
