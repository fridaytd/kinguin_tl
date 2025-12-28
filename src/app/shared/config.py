import os
from dotenv import load_dotenv
from pydantic import BaseModel


class Config(BaseModel):
    # Sheets
    SHEET_ID: str
    SHEET_NAME: str

    # Kinguin API
    KINGUIN_CLIENT_ID: str
    KINGUIN_SECRET_KEY: str

    # My seller name
    MY_SELLER_NAME: str

    # Relax time each round in second
    RELAX_TIME_EACH_ROUND: int

    # Thread number
    THREAD_NUMBER: int

    @staticmethod
    def from_env(dotenv_path: str = "settings.env") -> "Config":
        load_dotenv(dotenv_path)
        return Config.model_validate(os.environ)
