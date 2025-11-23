from gspread.auth import service_account

from app.shared.paths import ROOT_PATH
from app import config


g_client = service_account(ROOT_PATH.joinpath(config.KEYS_PATH))

spreadsheet = g_client.open_by_key(config.SHEET_ID)

worksheet = spreadsheet.worksheet(config.SHEET_NAME)
