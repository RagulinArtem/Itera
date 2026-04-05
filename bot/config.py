from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    telegram_test_bot_token: str = Field(default="", alias="TELEGRAM_TEST_BOT_TOKEN")

    # OpenAI
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    # Database
    database_url: str = Field(alias="DATABASE_URL")

    # Webhook
    webhook_domain: str = Field(default="", alias="WEBHOOK_DOMAIN")
    port: int = Field(default=8080, alias="PORT")

    # Environment
    env: str = Field(default="development", alias="ENV")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def bot_token(self) -> str:
        """Use test token in development, production token otherwise."""
        if self.env == "development" and self.telegram_test_bot_token:
            return self.telegram_test_bot_token
        return self.telegram_bot_token

    @property
    def webhook_path(self) -> str:
        return f"/webhook/{self.bot_token}"

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_domain}{self.webhook_path}"

    @property
    def is_production(self) -> bool:
        return self.env == "production"


settings = Settings()
