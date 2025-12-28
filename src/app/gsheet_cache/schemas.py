"""Data schemas for gsheet-cache.

This module defines Pydantic data models used throughout the gsheet-cache library,
primarily for representing Google Sheets data structures.

Classes:
    GridRange: Represents a rectangular range of cells in a Google Sheet.

Example:
    >>> from gsheet_cache.schemas import GridRange
    >>> range_obj = GridRange(
    ...     startRowIndex=0,
    ...     endRowIndex=10,
    ...     startColumnIndex=0,
    ...     endColumnIndex=5
    ... )
    >>> print(f"Range: rows {range_obj.startRowIndex}-{range_obj.endRowIndex}")
    Range: rows 0-10
"""

from pydantic import BaseModel, Field


class GridRange(BaseModel):
    """Represents a rectangular range of cells in a Google Sheet.

    This class models the GridRange object used by the Google Sheets API to
    specify cell ranges. All indices are 0-based and the end indices are
    exclusive (similar to Python slice notation).

    Attributes:
        startRowIndex: The start row (inclusive), 0-based. None means start from row 0.
        endRowIndex: The end row (exclusive), 0-based. None means extend to the last row.
        startColumnIndex: The start column (inclusive), 0-based. None means start from column A.
        endColumnIndex: The end column (exclusive), 0-based. None means extend to the last column.

    Example:
        >>> # Represents A1:E10 (rows 0-9, columns 0-4)
        >>> range_obj = GridRange(
        ...     startRowIndex=0,
        ...     endRowIndex=10,
        ...     startColumnIndex=0,
        ...     endColumnIndex=5
        ... )

        >>> # Entire column A (all rows, column 0 only)
        >>> column_range = GridRange(
        ...     startRowIndex=None,
        ...     endRowIndex=None,
        ...     startColumnIndex=0,
        ...     endColumnIndex=1
        ... )

    Note:
        This follows the Google Sheets API GridRange specification where:
        - Indices are 0-based
        - End indices are exclusive
        - None values represent unbounded ranges
    """

    startRowIndex: int | None = Field(
        default=None,
        description="Start row (inclusive, 0-based). None for first row."
    )
    endRowIndex: int | None = Field(
        default=None,
        description="End row (exclusive, 0-based). None for last row."
    )
    startColumnIndex: int | None = Field(
        default=None,
        description="Start column (inclusive, 0-based). None for first column."
    )
    endColumnIndex: int | None = Field(
        default=None,
        description="End column (exclusive, 0-based). None for last column."
    )
