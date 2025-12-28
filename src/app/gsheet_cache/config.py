"""Configuration module for gsheet-cache.

This module provides configuration classes for managing gsheet-cache settings,
including directory paths for cache storage and service account keys.

Classes:
    GSheetCacheConfig: Configuration container for cache and keys directories.

Example:
    >>> from pathlib import Path
    >>> from gsheet_cache import GSheetCacheConfig
    >>> config = GSheetCacheConfig(
    ...     cache_dir=Path(".cache"),
    ...     keys_dir=Path("keys")
    ... )
    >>> print(config.cache_dir)
    .cache
"""

from pathlib import Path

from pydantic import BaseModel, Field


class GSheetCacheConfig(BaseModel):
    """Configuration for gsheet-cache directories.

    This class holds the configuration for where cache files and service account
    keys are stored. It uses Pydantic for validation and provides sensible defaults.

    Attributes:
        cache_dir: Directory path where CSV cache files are stored.
            Defaults to ".gsheet_cache" in the current directory.
        keys_dir: Directory path containing Google Service Account JSON key files.
            Defaults to "keys" in the current directory.

    Example:
        >>> config = GSheetCacheConfig()  # Use defaults
        >>> config.cache_dir
        PosixPath('.gsheet_cache')

        >>> # Custom paths
        >>> config = GSheetCacheConfig(
        ...     cache_dir=Path("/var/cache/gsheet"),
        ...     keys_dir=Path("/etc/gsheet/keys")
        ... )
    """

    cache_dir: Path = Field(
        default=Path(".gsheet_cache"),
        description="Directory for storing cached CSV files"
    )
    keys_dir: Path = Field(
        default=Path("keys"),
        description="Directory containing service account JSON keys"
    )
