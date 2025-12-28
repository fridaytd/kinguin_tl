"""Manager module for handling multiple cached Google Sheets.

This module provides the GSheetCacheManager class for managing multiple
CacheSheet instances simultaneously. It allows centralized management of
multiple sheets across different spreadsheets.

Classes:
    GSheetCacheManager: Central manager for multiple cached Google Sheets.

Example:
    >>> from pathlib import Path
    >>> from gsheet_cache import GSheetCacheManager, GSheetCacheConfig
    >>> config = GSheetCacheConfig(cache_dir=Path(".cache"), keys_dir=Path("keys"))
    >>> manager = GSheetCacheManager(config)
    >>> manager.add_sheet("spreadsheet_id_1", "Sheet1")
    >>> value = manager.get_value("spreadsheet_id_1", "Sheet1", "A1")
"""

from .config import GSheetCacheConfig
from .sheet import CacheSheet


class GSheetCacheManager:
    """Central manager for multiple cached Google Sheets.

    This class provides a convenient way to manage multiple CacheSheet instances,
    allowing you to work with multiple sheets and spreadsheets through a single
    interface. It handles sheet lifecycle and provides convenient proxy methods
    for common operations.

    Attributes:
        config: The GSheetCacheConfig containing directory paths.
        sheets: Dictionary mapping (sheet_id, sheet_name) tuples to CacheSheet instances.

    Example:
        >>> config = GSheetCacheConfig()
        >>> manager = GSheetCacheManager(config)
        >>>
        >>> # Add sheets
        >>> manager.add_sheet("spreadsheet_1", "Sales")
        >>> manager.add_sheet("spreadsheet_1", "Inventory")
        >>> manager.add_sheet("spreadsheet_2", "Customers")
        >>>
        >>> # Work with sheets
        >>> manager.update_value("spreadsheet_1", "Sales", "A1", "Q1 Revenue")
        >>> value = manager.get_value("spreadsheet_1", "Sales", "A1")
        >>>
        >>> # Flush changes
        >>> manager.flush_to_sheet("spreadsheet_1", "Sales", ["A1"])
    """

    def __init__(self, config: GSheetCacheConfig):
        """Initialize the GSheetCacheManager.

        Args:
            config: Configuration containing cache and keys directory paths.

        Raises:
            FileNotFoundError: If the keys directory does not exist.

        Example:
            >>> config = GSheetCacheConfig(
            ...     cache_dir=Path(".cache"),
            ...     keys_dir=Path("keys")
            ... )
            >>> manager = GSheetCacheManager(config)
        """
        self.config = config
        # A dict to hold CacheSheet instances, keyed by (sheet_id, sheet_name)
        self.sheets: dict[tuple[str, str], CacheSheet] = {}

        # Ensure cache directory exists
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)

        self.__check_keys_dir()

    def __check_keys_dir(self) -> None:
        """Raise an error if the keys directory does not exist.

        Raises:
            FileNotFoundError: If the configured keys directory doesn't exist.
        """
        if not self.config.keys_dir.exists():
            raise FileNotFoundError(
                f"Keys directory does not exist: {self.config.keys_dir}"
            )

    def add_sheet(self, sheet_id: str, sheet_name: str) -> CacheSheet:
        """Add a new CacheSheet to the manager.

        If a sheet with the same ID and name already exists, returns the
        existing instance instead of creating a new one.

        Args:
            sheet_id: The Google Sheets spreadsheet ID.
            sheet_name: The name of the sheet/tab within the spreadsheet.

        Returns:
            The CacheSheet instance (either newly created or existing).

        Example:
            >>> manager = GSheetCacheManager(config)
            >>> sheet = manager.add_sheet("1BxiMV...", "Sheet1")
            >>> # Adding again returns the same instance
            >>> same_sheet = manager.add_sheet("1BxiMV...", "Sheet1")
            >>> assert sheet is same_sheet
        """
        key = (sheet_id, sheet_name)
        if key not in self.sheets:
            self.sheets[key] = CacheSheet(sheet_id, sheet_name, self.config)
        return self.sheets[key]

    def remove_sheet(self, sheet_id: str, sheet_name: str) -> None:
        """Remove a CacheSheet from the manager.

        Note: This only removes the sheet from the manager's memory.
        The cached CSV file is not deleted from disk.

        Args:
            sheet_id: The Google Sheets spreadsheet ID.
            sheet_name: The name of the sheet/tab to remove.

        Example:
            >>> manager.add_sheet("1BxiMV...", "Sheet1")
            >>> manager.remove_sheet("1BxiMV...", "Sheet1")
            >>> # Sheet is no longer managed
        """
        key = (sheet_id, sheet_name)
        if key in self.sheets:
            del self.sheets[key]

    def clear_all_sheets(self) -> None:
        """Clear all CacheSheet instances from the manager.

        This removes all sheets from memory but does not delete cache files
        from disk. Useful for resetting the manager state.

        Example:
            >>> manager.add_sheet("sheet1", "Tab1")
            >>> manager.add_sheet("sheet2", "Tab2")
            >>> manager.clear_all_sheets()
            >>> len(manager.sheets)
            0
        """
        self.sheets.clear()

    def get_sheet(self, sheet_id: str, sheet_name: str) -> CacheSheet:
        """Get a CacheSheet instance from the manager.

        Args:
            sheet_id: The Google Sheets spreadsheet ID.
            sheet_name: The name of the sheet/tab.

        Returns:
            The CacheSheet instance.

        Raises:
            ValueError: If the sheet is not found in the manager.

        Example:
            >>> manager.add_sheet("1BxiMV...", "Sheet1")
            >>> sheet = manager.get_sheet("1BxiMV...", "Sheet1")
            >>> value = sheet.get_value("A1")
        """
        key = (sheet_id, sheet_name)
        if key not in self.sheets:
            raise ValueError(f"Sheet not found: {sheet_id} - {sheet_name}")

        sheet = self.sheets[key]
        return sheet

    def get_value(self, sheet_id: str, sheet_name: str, cell: str) -> str | None:
        """Get a value from a specific sheet and cell.

        Convenience method that combines get_sheet() and CacheSheet.get_value().

        Args:
            sheet_id: The Google Sheets spreadsheet ID.
            sheet_name: The name of the sheet/tab.
            cell: Cell reference in A1 notation (e.g., "A1", "B5").

        Returns:
            The cell value as a string, or None if the cell is out of bounds.

        Raises:
            ValueError: If the sheet is not found.

        Example:
            >>> value = manager.get_value("1BxiMV...", "Sheet1", "A1")
            >>> print(value)
            'Hello World'
        """
        sheet = self.get_sheet(sheet_id, sheet_name)
        return sheet.get_value(cell)

    def update_value(
        self, sheet_id: str, sheet_name: str, cell: str, value: str
    ) -> None:
        """Update a value in a specific sheet and cell.

        Updates only the local cache. Call flush_to_sheet() to sync to Google Sheets.

        Args:
            sheet_id: The Google Sheets spreadsheet ID.
            sheet_name: The name of the sheet/tab.
            cell: Cell reference in A1 notation (e.g., "A1", "B5").
            value: The new value to set.

        Raises:
            ValueError: If the sheet is not found.

        Example:
            >>> manager.update_value("1BxiMV...", "Sheet1", "A1", "New Value")
            >>> # Changes are in local cache only
            >>> manager.flush_to_sheet("1BxiMV...", "Sheet1", ["A1"])
        """
        sheet = self.get_sheet(sheet_id, sheet_name)
        sheet.update_value(cell, value)

    def flush_to_sheet(self, sheet_id: str, sheet_name: str, cells: list[str]) -> None:
        """Flush updated values to the Google Sheet.

        Syncs the specified cells from the local cache back to the remote
        Google Sheet. Uses automatic key rotation on rate limits.

        Args:
            sheet_id: The Google Sheets spreadsheet ID.
            sheet_name: The name of the sheet/tab.
            cells: List of cell references in A1 notation to sync.

        Raises:
            ValueError: If the sheet is not found.
            APIError: If the API call fails after all retries.

        Example:
            >>> manager.update_value("1BxiMV...", "Sheet1", "A1", "Value 1")
            >>> manager.update_value("1BxiMV...", "Sheet1", "B1", "Value 2")
            >>> manager.flush_to_sheet("1BxiMV...", "Sheet1", ["A1", "B1"])
        """
        sheet = self.get_sheet(sheet_id, sheet_name)
        sheet.flush_to_sheet(cells)

    def get_range(
        self, sheet_id: str, sheet_name: str, a1_range: str
    ) -> list[list[str]]:
        """Get a range of values from a specific sheet.

        Convenience method that combines get_sheet() and CacheSheet.get_range().

        Args:
            sheet_id: The Google Sheets spreadsheet ID.
            sheet_name: The name of the sheet/tab.
            a1_range: Range in A1 notation (e.g., "A1:B5", "A:A", "1:1").

        Returns:
            A 2D list of strings representing the range values.
            Empty cells are represented as empty strings.

        Raises:
            ValueError: If the sheet is not found.
            FileNotFoundError: If the cache directory does not exist.

        Example:
            >>> # Get a cell range
            >>> data = manager.get_range("1BxiMV...", "Sheet1", "A1:C10")
            >>> print(f"Retrieved {len(data)} rows")
            Retrieved 10 rows
            >>>
            >>> # Iterate over the data
            >>> for row in data:
            ...     for cell in row:
            ...         print(cell, end="\\t")
            ...     print()
            >>>
            >>> # Get entire column
            >>> column_data = manager.get_range("1BxiMV...", "Sheet1", "A:A")
        """
        sheet = self.get_sheet(sheet_id, sheet_name)
        return sheet.get_range(a1_range)
