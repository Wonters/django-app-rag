from django_app_rag.rag.logging_setup import get_logger

logger = get_logger(__name__)
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    """
    A Pydantic-based settings class for managing application configurations.
    """

    # --- Pydantic Settings ---
    model_config: SettingsConfigDict = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env", env_file_encoding="utf-8"
    )

    STORAGE_TYPE: str = Field(
        default="disk", description="Type of storage to save collections"
    )

    # --- AWS Configuration ---
    AWS_ACCESS_KEY: str | None = Field(
        default=None, description="AWS access key for authentication."
    )
    AWS_SECRET_KEY: str | None = Field(
        default=None, description="AWS secret key for authentication."
    )
    AWS_DEFAULT_REGION: str = Field(
        default="eu-central-1", description="AWS region for cloud services."
    )
    AWS_S3_BUCKET_NAME: str = Field(
        default="decodingml-public-data",
        description="Name of the S3 bucket for storing application data.",
    )

    # --- Comet ML & Opik Configuration ---
    COMET_API_KEY: str | None = Field(
        default=None, description="API key for Comet ML and Opik services."
    )
    COMET_PROJECT: str = Field(
        default="second_brain_course",
        description="Project name for Comet ML and Opik tracking.",
    )
    USE_HUGGINGFACE_DEDICATED_ENDPOINT: bool = Field(
        default=False,
        description="Whether to use the dedicated endpoint for summarizing responses. If True, we will use the dedicated endpoint instead of OpenAI.",
    )

    # --- Hugging Face Configuration ---
    HUGGINGFACE_ACCESS_TOKEN: str | None = Field(
        default=None, description="Access token for Hugging Face API authentication."
    )
    HUGGINGFACE_DEDICATED_ENDPOINT: str | None = Field(
        default=None,
        description="Dedicated endpoint URL for real-time inference. "
        "If provided, we will use the dedicated endpoint instead of OpenAI. "
        "For example, https://um18v2aeit3f6g1b.eu-west-1.aws.endpoints.huggingface.cloud/v1/, "
        "with /v1 after the endpoint URL.",
    )

    # --- Notion API Configuration ---
    NOTION_SECRET_KEY: str | None = Field(
        default=None, description="Secret key for Notion API authentication."
    )

    # --- OpenAI API Configuration ---
    OPENAI_API_KEY: str = Field(
        description="API key for OpenAI service authentication.",
    )
    
    OPENAI_MODEL_ID: str = Field(
        default="gpt-4o-mini", description="Identifier for the OpenAI model to be used."
    )

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def check_not_empty(cls, value: str, info) -> str:
        if not value or value.strip() == "":
            logger.error(f"{info.field_name} cannot be empty.")
            raise ValueError(f"{info.field_name} cannot be empty.")
        return value


try:
    settings = Settings()
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise SystemExit(e)
