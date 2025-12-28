from .gsheet_cache import GSheetCacheConfig, GSheetCacheManager

from app.shared.paths import ROOT_PATH
from app import config

gsheet_cache_config = GSheetCacheConfig(
    cache_dir=ROOT_PATH / ".gsheet_cache",
    keys_dir=ROOT_PATH / "keys",
)


gsheet_cache_manager = GSheetCacheManager(config=gsheet_cache_config)


def initialize_gsheet_cache_manager() -> None:
    global gsheet_cache_manager

    gsheet_cache_manager.add_sheet(
        sheet_id=config.SHEET_ID,
        sheet_name=config.SHEET_NAME,
    )
