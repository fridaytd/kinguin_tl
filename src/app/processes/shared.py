"""Shared processing utilities"""
from datetime import datetime
from app.service.data_cache import CachedRow, get_cache
from app.shared.utils import formated_datetime


def update_cache_note(cached_row: CachedRow, note: str):
    """Update note and last_update in cache"""
    now = datetime.now()
    cache = get_cache()
    cache.update_fields(
        index=cached_row.index,
        note=note,
        last_update=formated_datetime(now)
    )


def extract_offer_id_from_product_link(link: str) -> str:
    """Extract offer ID from product link"""
    return link.split("/")[-1]
