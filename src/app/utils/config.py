import os
from dotenv import load_dotenv
from pydantic import BaseModel


class Config(BaseModel):
    # Keys
    KEYS_PATH: str

    # Sheets
    SHEET_ID: str
    SHEET_NAME: str

    # Gameboost API key
    GAMEBOOST_API_KEY: str

    # My seller name
    MY_SELLER_NAME: str

    # Relax time each round in second
    RELAX_TIME_EACH_ROUND: int

    #Thread number
    THREAD_NUMBER: int

    @staticmethod
    def from_env(dotenv_path: str = "settings.env") -> "Config":
        load_dotenv(dotenv_path)
        return Config.model_validate(os.environ)
