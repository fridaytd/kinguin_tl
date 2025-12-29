"""Google Sheets caching module.

This module provides a CacheSheet class that caches Google Sheets data locally
as CSV files, allowing for efficient read/write operations with periodic syncing
back to the remote sheet.

The cache enables:
- Fast local reads without API calls
- Batch updates to minimize API usage
- Offline work with later synchronization

Example:
    >>> from gsheet_cache import CacheSheet, GSheetCacheConfig
    >>> config = GSheetCacheConfig(cache_dir=Path(".cache"), keys_dir=Path("keys"))
    >>> sheet = CacheSheet("spreadsheet_id", "Sheet1", config)
    >>> value = sheet.get_value("A1")
    >>> sheet.update_value("A1", "new value")
    >>> sheet.flush_to_sheet(["A1"])
"""

from typing import Any, MutableMapping

from pathlib import Path

import csv
import random
import logging
import time

from gspread import service_account
from gspread.utils import ValueInputOption, absolute_range_name, a1_to_rowcol
from gspread.http_client import HTTPClient
from gspread.exceptions import APIError

from .config import GSheetCacheConfig
from .utils import a1_range_to_grid_range_custom

logger = logging.getLogger(__name__)


class CacheSheet:
    """A cached interface to Google Sheets.

    This class maintains a local CSV cache of a Google Sheet, allowing for
    efficient local operations with the ability to flush changes back to the
    remote sheet.

    Features:
    - Random key selection from available service account keys
    - Automatic key rotation on rate limits or API errors
    - Retry logic with exponential backoff

    Attributes:
        sheet_id: The Google Sheets spreadsheet ID.
        sheet_name: The name of the specific sheet/tab within the spreadsheet.
        config: Configuration object containing cache and keys directories.
        cache_file: Path to the local CSV cache file.
        keys: List of available service account JSON key files.
        max_retries: Maximum number of retry attempts on API errors (default: 3).
    """

    def __init__(
        self,
        sheet_id: str,
        sheet_name: str,
        config: GSheetCacheConfig,
        max_retries: int = 3,
    ) -> None:
        """Initialize a CacheSheet instance.

        Args:
            sheet_id: The Google Sheets spreadsheet ID.
            sheet_name: The name of the sheet/tab to cache.
            config: Configuration containing cache and keys directory paths.
            max_retries: Maximum number of retry attempts on API errors.

        Raises:
            FileNotFoundError: If the keys directory does not exist.
            ValueError: If no valid key files are found.
        """
        self.sheet_id = sheet_id
        self.config = config
        self.sheet_name = sheet_name
        self.cache_path = config.cache_dir
        self.max_retries = max_retries
        self._http_client: HTTPClient | None = None
        self._current_key_index: int | None = None
        self._failed_keys: set[int] = set()
        self._cache_data: list[list[str]] | None = None
        self._dirty: bool = False

        self.__init_cache_file()
        self.__load_keys()
        self.__load_values_from_sheet()

    def __check_keys_dir(self) -> None:
        """Raise an error if the keys directory does not exist."""
        if not self.config.keys_dir.exists():
            raise FileNotFoundError(
                f"Keys directory does not exist: {self.config.keys_dir}"
            )

    def __load_keys(self) -> None:
        """Load API keys from the keys directory.

        Raises:
            FileNotFoundError: If the keys directory does not exist.
            ValueError: If no valid JSON key files are found.
        """
        self.__check_keys_dir()

        keys_dir = self.config.keys_dir
        self.keys = [
            f for f in keys_dir.iterdir() if f.is_file() and f.suffix == ".json"
        ]

        if not self.keys:
            raise ValueError(f"No JSON key files found in {keys_dir}")

        logger.info(f"Loaded {len(self.keys)} service account key(s)")

    def __init_cache_file(self) -> None:
        """Initialize the cache file path."""
        self.cache_file: Path = (
            self.cache_path / f"{self.sheet_id}_{self.sheet_name}.csv"
        )

    def __ensure_cache_dir_exists(self) -> None:
        """Ensure the cache directory exists.

        Raises:
            FileNotFoundError: If the cache directory does not exist.
        """
        if not self.cache_path.exists():
            raise FileNotFoundError(
                f"Cache directory does not exist: {self.cache_path}"
            )

    def __get_http_client(self) -> HTTPClient:
        """Get or create the HTTP client for Google Sheets API.

        Returns:
            An authenticated HTTPClient instance.
        """
        if self._http_client is None:
            self.__select_random_key()
            assert self._current_key_index is not None
            key_path = self.keys[self._current_key_index]
            logger.info(f"Using key: {key_path.name}")
            self._http_client = service_account(filename=str(key_path)).http_client
        return self._http_client

    def __select_random_key(self) -> None:
        """Select a random key from available keys, excluding failed ones."""
        available_indices = [
            i for i in range(len(self.keys)) if i not in self._failed_keys
        ]

        if not available_indices:
            # Reset failed keys if all have failed
            logger.warning("All keys have failed, resetting failed keys list")
            self._failed_keys.clear()
            available_indices = list(range(len(self.keys)))

        self._current_key_index = random.choice(available_indices)

    def __rotate_key(self) -> None:
        """Rotate to a different key after a failure.

        This method marks the current key as failed and selects a new one.
        """
        if self._current_key_index is not None:
            self._failed_keys.add(self._current_key_index)
            logger.warning(
                f"Marking key {self.keys[self._current_key_index].name} as failed"
            )

        # Reset HTTP client to force new connection with new key
        self._http_client = None
        self.__select_random_key()

        assert self._current_key_index is not None
        new_key_path = self.keys[self._current_key_index]
        logger.info(f"Rotating to new key: {new_key_path.name}")
        self._http_client = service_account(filename=str(new_key_path)).http_client

    def __is_rate_limit_error(self, error: APIError) -> bool:
        """Check if an API error is due to rate limiting.

        Args:
            error: The APIError to check.

        Returns:
            True if the error is rate limit related, False otherwise.
        """
        # Check for common rate limit status codes
        if hasattr(error, "response") and error.response is not None:
            status_code = error.response.status_code
            # 429 = Too Many Requests, 403 can also indicate quota exceeded
            if status_code in (429, 403):
                return True

            # Check error message for rate limit keywords
            error_message = str(error).lower()
            rate_limit_keywords = [
                "rate limit",
                "quota",
                "too many requests",
                "user rate limit",
            ]
            return any(keyword in error_message for keyword in rate_limit_keywords)

        return False

    def __execute_with_retry(self, operation, *args, **kwargs):
        """Execute an operation with automatic retry and key rotation on failure.

        Args:
            operation: The function to execute.
            *args: Positional arguments for the operation.
            **kwargs: Keyword arguments for the operation.

        Returns:
            The result of the operation.

        Raises:
            APIError: If all retries are exhausted.
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except APIError as e:
                last_error = e
                if self.__is_rate_limit_error(e):
                    logger.warning(
                        f"Rate limit error on attempt {attempt + 1}/{self.max_retries}: {e}"
                    )

                    if attempt < self.max_retries - 1:
                        # Rotate key and retry
                        self.__rotate_key()

                        # Exponential backoff
                        wait_time = 2**attempt
                        logger.info(f"Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                    else:
                        logger.error("Max retries reached, all keys exhausted")
                        raise
                else:
                    # Non-rate-limit error, re-raise immediately
                    logger.error(f"API error (non-rate-limit): {e}")
                    raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error

    def __read_cache_data(self) -> list[list[str]]:
        """Read all data from the cache file with in-memory caching.

        Returns:
            A 2D list of strings representing the cached sheet data.

        Raises:
            FileNotFoundError: If the cache directory does not exist.
        """
        if self._cache_data is None:
            self.__ensure_cache_dir_exists()

            with self.cache_file.open("r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                self._cache_data = list(reader)

        return self._cache_data

    def __write_cache_data(self, data: list[list[str]]) -> None:
        """Write data to the cache file.

        Args:
            data: A 2D list of strings to write to the cache.
        """
        with self.cache_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        # Update in-memory cache after writing to disk
        self._cache_data = data
        self._dirty = False

    def __ensure_cell_exists(self, data: list[list[str]], row: int, col: int) -> None:
        """Ensure the data structure is large enough for the given cell.

        Args:
            data: The 2D list to expand if necessary.
            row: The 0-based row index.
            col: The 0-based column index.
        """
        while len(data) <= row:
            data.append([])
        while len(data[row]) <= col:
            data[row].append("")

    def __a1_to_indices(self, cell: str) -> tuple[int, int]:
        """Convert A1 notation to 0-based row and column indices.

        Args:
            cell: A cell reference in A1 notation (e.g., "A1", "B5").

        Returns:
            A tuple of (row_index, col_index) in 0-based indexing.
        """
        row, col = a1_to_rowcol(cell)
        return row - 1, col - 1

    def __load_values_from_sheet(self):
        """Load all values from the Google Sheet and cache them locally."""

        def _fetch():
            gsheet_http_client = self.__get_http_client()
            return gsheet_http_client.values_get(
                id=self.sheet_id,
                range=absolute_range_name(self.sheet_name),
            )

        res = self.__execute_with_retry(_fetch)

        if not res:
            raise ValueError("Failed to fetch data from Google Sheet")

        self.__init_cache_file()
        with self.cache_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in res["values"]:
                writer.writerow(row)

        # Clear in-memory cache to force reload from new file
        self._cache_data = None
        self._dirty = False

    def get_value(self, cell: str) -> str | None:
        """Get the value of a specific cell from the cache.

        Args:
            cell: Cell reference in A1 notation (e.g., "A1", "B5").

        Returns:
            The cell value as a string, or None if the cell is out of bounds.

        Raises:
            FileNotFoundError: If the cache directory does not exist.
        """
        data = self.__read_cache_data()
        row, col = self.__a1_to_indices(cell)

        try:
            value = data[row][col]
            if value == "":
                value = None
            return value
        except IndexError:
            return None

    def update_value(self, cell: str, value: str) -> None:
        """Update the value of a specific cell in the cache.

        This only updates the in-memory cache. Call flush_cache() to write
        changes to disk, or flush_to_sheet() to sync both to disk and the
        Google Sheet.

        Args:
            cell: Cell reference in A1 notation (e.g., "A1", "B5").
            value: The new value to set.

        Raises:
            FileNotFoundError: If the cache directory does not exist.
        """
        data = self.__read_cache_data()
        row, col = self.__a1_to_indices(cell)

        self.__ensure_cell_exists(data, row, col)
        data[row][col] = value

        # Mark cache as dirty but don't write to disk yet
        self._dirty = True

    def flush_cache(self) -> None:
        """Write in-memory cache to disk if dirty.

        This method writes pending changes to the local CSV cache file.
        It's automatically called by flush_to_sheet(), but you can call
        it manually if you want to persist changes to disk without
        syncing to Google Sheets.

        Raises:
            FileNotFoundError: If the cache directory does not exist.
        """
        if self._dirty and self._cache_data is not None:
            self.__write_cache_data(self._cache_data)

    def flush_to_sheet(self, cells: list[str]) -> dict[str, Any] | None:
        """Flush the cached values back to the Google Sheet.

        This method automatically flushes pending changes to disk before
        syncing to the Google Sheet.

        Args:
            cells: List of cell references in A1 notation to sync (e.g., ["A1", "B5"]).

        Returns:
            The API response from the batch update operation.

        Raises:
            FileNotFoundError: If the cache directory does not exist.
            APIError: If the API call fails after all retries.
        """
        # Flush in-memory changes to disk first
        self.flush_cache()

        data = self.__read_cache_data()

        data_body = []
        for cell in cells:
            row, col = self.__a1_to_indices(cell)

            self.__ensure_cell_exists(data, row, col)

            data_body.append(
                {
                    "range": cell,
                    "values": [[data[row][col]]],
                }
            )

        value_input_option = ValueInputOption.raw

        for values in data_body:
            values["range"] = absolute_range_name(self.sheet_name, values["range"])

        body: MutableMapping[str, Any] = {
            "valueInputOption": value_input_option,
            "includeValuesInResponse": None,
            "responseValueRenderOption": None,
            "responseDateTimeRenderOption": None,
            "data": data_body,
        }

        def _update():
            gsheet_http_client = self.__get_http_client()
            return gsheet_http_client.values_batch_update(self.sheet_id, body=body)

        response = self.__execute_with_retry(_update)

        return response

    def get_range(self, a1_range: str) -> list[list[str]]:
        """Get a range of values from the cache.

        Args:
            a1_range: Range in A1 notation (e.g., "A1:B5", "A:A", "1:1").

        Returns:
            A 2D list of strings representing the range values.
            Empty cells are represented as empty strings.

        Raises:
            FileNotFoundError: If the cache directory does not exist.
        """
        data = self.__read_cache_data()

        grid_range = a1_range_to_grid_range_custom(a1_range)

        result = []
        for r in range(
            grid_range.startRowIndex or 0,
            grid_range.endRowIndex or len(data),
        ):
            row_data = []
            for c in range(
                grid_range.startColumnIndex or 0,
                grid_range.endColumnIndex or (len(data[r]) if r < len(data) else 0),
            ):
                try:
                    value = data[r][c]
                    if value == "":
                        value = None
                    row_data.append(value)
                except IndexError:
                    row_data.append(None)
            result.append(row_data)

        return result

    def reset_failed_keys(self) -> None:
        """Reset the list of failed keys.

        This can be called to give previously failed keys another chance,
        for example after a cooldown period or when you know quota has reset.
        """
        self._failed_keys.clear()
        logger.info("Failed keys list has been reset")

    def get_key_status(self) -> dict[str, Any]:
        """Get information about the current key usage and status.

        Returns:
            A dictionary containing:
            - total_keys: Total number of available keys
            - current_key: Name of the currently active key (or None)
            - failed_keys: List of failed key names
            - available_keys: Number of keys still available
        """
        current_key_name = None
        if self._current_key_index is not None:
            current_key_name = self.keys[self._current_key_index].name

        failed_key_names = [self.keys[i].name for i in self._failed_keys]

        return {
            "total_keys": len(self.keys),
            "current_key": current_key_name,
            "failed_keys": failed_key_names,
            "available_keys": len(self.keys) - len(self._failed_keys),
        }
