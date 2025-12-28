"""Utility functions for gsheet-cache.

This module provides helper functions for working with Google Sheets data,
particularly for converting between different range notation formats.

Functions:
    a1_range_to_grid_range_custom: Convert A1 notation to GridRange objects.

Example:
    >>> from gsheet_cache.utils import a1_range_to_grid_range_custom
    >>> grid_range = a1_range_to_grid_range_custom("A1:B10")
    >>> print(f"Rows: {grid_range.startRowIndex}-{grid_range.endRowIndex}")
    Rows: 0-10
"""

from gspread.utils import a1_range_to_grid_range

from .schemas import GridRange


def a1_range_to_grid_range_custom(a1_range: str) -> GridRange:
    """Convert an A1 notation range string to a GridRange object.

    This function wraps the gspread library's A1 notation converter and
    returns a typed GridRange object that can be used throughout the
    gsheet-cache library.

    Args:
        a1_range: A range string in A1 notation. Supported formats:
            - Cell ranges: "A1:B10", "C5:F20"
            - Full columns: "A:A", "B:E"
            - Full rows: "1:1", "5:10"
            - Single cells: "A1", "B5"
            - Unbounded ranges: "A1:B", "A:B10"

    Returns:
        A GridRange object with 0-based, half-open interval indices:
        - startRowIndex: First row (inclusive)
        - endRowIndex: Last row (exclusive)
        - startColumnIndex: First column (inclusive)
        - endColumnIndex: Last column (exclusive)

    Example:
        >>> # Convert a cell range
        >>> range_obj = a1_range_to_grid_range_custom("A1:B10")
        >>> range_obj.startRowIndex
        0
        >>> range_obj.endRowIndex
        10
        >>> range_obj.startColumnIndex
        0
        >>> range_obj.endColumnIndex
        2

        >>> # Convert entire column
        >>> col_range = a1_range_to_grid_range_custom("A:A")
        >>> col_range.startColumnIndex
        0
        >>> col_range.endColumnIndex
        1
        >>> col_range.startRowIndex is None
        True

    Note:
        The returned GridRange uses 0-based indexing with exclusive end indices,
        consistent with the Google Sheets API specification.
    """
    grid_range_dict = a1_range_to_grid_range(a1_range)
    return GridRange(**grid_range_dict)
