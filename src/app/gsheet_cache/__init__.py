"""gsheet-cache: A local caching library for Google Sheets.

This package provides efficient local caching for Google Sheets data with
automatic key rotation and rate limit handling.

Features:
    - Local CSV caching for fast read operations
    - Batch write operations to minimize API calls
    - Random service account key selection
    - Automatic key rotation on rate limits
    - Exponential backoff retry logic
    - Support for multiple sheets and spreadsheets

Main Classes:
    CacheSheet: Core class for caching a single Google Sheet.
    GSheetCacheManager: Manager for multiple cached sheets.
    GSheetCacheConfig: Configuration for cache and keys directories.

Quick Start:
    >>> from pathlib import Path
    >>> from gsheet_cache import CacheSheet, GSheetCacheConfig
    >>>
    >>> # Configure
    >>> config = GSheetCacheConfig(
    ...     cache_dir=Path(".gsheet_cache"),
    ...     keys_dir=Path("keys")
    ... )
    >>>
    >>> # Create a cached sheet
    >>> sheet = CacheSheet("your_spreadsheet_id", "Sheet1", config)
    >>>
    >>> # Read from cache (no API call)
    >>> value = sheet.get_value("A1")
    >>>
    >>> # Update cache locally
    >>> sheet.update_value("A1", "New Value")
    >>>
    >>> # Sync to Google Sheets (with automatic key rotation)
    >>> sheet.flush_to_sheet(["A1"])

For more information, see the README.md file or the individual module documentation.
"""

from .config import GSheetCacheConfig
from .manager import GSheetCacheManager
from .sheet import CacheSheet

__version__ = "0.1.0"
__all__ = ["GSheetCacheConfig", "GSheetCacheManager", "CacheSheet"]