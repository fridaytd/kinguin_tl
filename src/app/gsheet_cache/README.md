# gsheet-cache

A Python library for efficiently caching Google Sheets data locally with automatic key rotation and rate limit handling.

## Features

- **Local CSV Caching**: Store Google Sheets data locally for fast read operations without API calls
- **Batch Operations**: Minimize API usage with batch write operations
- **Smart Key Management**:
  - Random selection from multiple service account keys
  - Automatic key rotation on rate limits
  - Exponential backoff retry logic
- **Multi-Sheet Support**: Manage multiple sheets across different spreadsheets
- **Type Safety**: Built with Pydantic for robust data validation

## Installation

```bash
pip install gsheet-cache
```

## Quick Start

### Basic Usage

```python
from pathlib import Path
from gsheet_cache import CacheSheet, GSheetCacheConfig

# Configure paths
config = GSheetCacheConfig(
    cache_dir=Path(".gsheet_cache"),
    keys_dir=Path("keys")
)

# Initialize a cached sheet
sheet = CacheSheet(
    sheet_id="your_spreadsheet_id_here",
    sheet_name="Sheet1",
    config=config
)

# Read from cache (fast, no API call)
value = sheet.get_value("A1")
print(f"A1 contains: {value}")

# Update local cache
sheet.update_value("A1", "New Value")
sheet.update_value("B1", "Another Value")

# Sync to Google Sheets (with automatic retry and key rotation)
response = sheet.flush_to_sheet(["A1", "B1"])
```

### Managing Multiple Sheets

```python
from gsheet_cache import GSheetCacheManager, GSheetCacheConfig

# Create manager
config = GSheetCacheConfig()
manager = GSheetCacheManager(config)

# Add multiple sheets
manager.add_sheet("spreadsheet_1", "Sales")
manager.add_sheet("spreadsheet_1", "Inventory")
manager.add_sheet("spreadsheet_2", "Customers")

# Work with sheets through the manager
manager.update_value("spreadsheet_1", "Sales", "A1", "Q1 Revenue: $1M")
value = manager.get_value("spreadsheet_1", "Sales", "A1")

# Flush changes
manager.flush_to_sheet("spreadsheet_1", "Sales", ["A1"])
```

## Setup

### 1. Service Account Keys

1. Create a Google Cloud Project
2. Enable the Google Sheets API
3. Create one or more Service Account keys
4. Download the JSON key files
5. Place them in your `keys_dir` (default: `./keys/`)

```
keys/
├── service-account-1.json
├── service-account-2.json
└── service-account-3.json
```

### 2. Share Your Spreadsheet

Share your Google Sheets with the service account email addresses found in your JSON key files.

### 3. Directory Structure

```
your-project/
├── keys/                    # Service account keys
│   ├── account-1.json
│   └── account-2.json
├── .gsheet_cache/          # Cached CSV files (auto-created)
│   ├── spreadsheet1_Sheet1.csv
│   └── spreadsheet2_Data.csv
└── main.py                 # Your code
```

## Advanced Features

### Automatic Key Rotation

The library automatically rotates between service account keys when rate limits are hit:

```python
# Initialize with multiple keys in the keys/ directory
sheet = CacheSheet(
    sheet_id="your_id",
    sheet_name="Sheet1",
    config=config,
    max_retries=3  # Number of retry attempts with different keys
)

# The library will automatically:
# 1. Randomly select a key
# 2. Detect rate limit errors (429, 403)
# 3. Rotate to a different key
# 4. Retry with exponential backoff (1s, 2s, 4s...)

sheet.flush_to_sheet(["A1", "B1", "C1"])
```

### Monitoring Key Usage

```python
# Check current key status
status = sheet.get_key_status()
print(f"Using key: {status['current_key']}")
print(f"Available keys: {status['available_keys']}/{status['total_keys']}")
print(f"Failed keys: {status['failed_keys']}")

# Reset failed keys after cooldown period
import time
time.sleep(60)  # Wait for quota reset
sheet.reset_failed_keys()
```

### Working with Ranges

```python
# Get a range of values
data = sheet.get_range("A1:C10")
# Returns: [[cell_a1, cell_b1, cell_c1], [cell_a2, cell_b2, cell_c2], ...]

# Iterate over range data
for row in data:
    for cell_value in row:
        print(cell_value, end="\t")
    print()
```

## API Reference

### CacheSheet

The core class for caching a single Google Sheet.

#### Constructor

```python
CacheSheet(
    sheet_id: str,
    sheet_name: str,
    config: GSheetCacheConfig,
    max_retries: int = 3
)
```

**Parameters:**
- `sheet_id`: Google Sheets spreadsheet ID (from the URL)
- `sheet_name`: Name of the sheet/tab
- `config`: Configuration object
- `max_retries`: Maximum retry attempts on rate limits

#### Methods

##### `get_value(cell: str) -> str | None`
Get a single cell value from the cache.

```python
value = sheet.get_value("A1")
```

##### `update_value(cell: str, value: str) -> None`
Update a cell in the local cache.

```python
sheet.update_value("A1", "New Value")
```

##### `flush_to_sheet(cells: list[str]) -> dict`
Sync cached values back to Google Sheets.

```python
response = sheet.flush_to_sheet(["A1", "B1", "C1"])
```

##### `get_range(a1_range: str) -> list[list[str]]`
Get a range of values from cache.

```python
data = sheet.get_range("A1:C10")
```

##### `reset_failed_keys() -> None`
Reset the list of failed keys.

```python
sheet.reset_failed_keys()
```

##### `get_key_status() -> dict`
Get current key usage information.

```python
status = sheet.get_key_status()
```

### GSheetCacheManager

Manager for multiple cached sheets.

#### Constructor

```python
GSheetCacheManager(config: GSheetCacheConfig)
```

#### Methods

##### `add_sheet(sheet_id: str, sheet_name: str) -> CacheSheet`
Add a sheet to the manager.

```python
sheet = manager.add_sheet("spreadsheet_id", "Sheet1")
```

##### `get_sheet(sheet_id: str, sheet_name: str) -> CacheSheet`
Get a managed sheet instance.

```python
sheet = manager.get_sheet("spreadsheet_id", "Sheet1")
```

##### `get_value(sheet_id: str, sheet_name: str, cell: str) -> str | None`
Get a value from a managed sheet.

```python
value = manager.get_value("spreadsheet_id", "Sheet1", "A1")
```

##### `update_value(sheet_id: str, sheet_name: str, cell: str, value: str) -> None`
Update a value in a managed sheet.

```python
manager.update_value("spreadsheet_id", "Sheet1", "A1", "Value")
```

##### `flush_to_sheet(sheet_id: str, sheet_name: str, cells: list[str]) -> None`
Flush changes from a managed sheet.

```python
manager.flush_to_sheet("spreadsheet_id", "Sheet1", ["A1"])
```

##### `remove_sheet(sheet_id: str, sheet_name: str) -> None`
Remove a sheet from the manager.

```python
manager.remove_sheet("spreadsheet_id", "Sheet1")
```

##### `clear_all_sheets() -> None`
Clear all managed sheets.

```python
manager.clear_all_sheets()
```

### GSheetCacheConfig

Configuration for cache and keys directories.

#### Constructor

```python
GSheetCacheConfig(
    cache_dir: Path = Path(".gsheet_cache"),
    keys_dir: Path = Path("keys")
)
```

**Parameters:**
- `cache_dir`: Directory for storing cached CSV files
- `keys_dir`: Directory containing service account JSON keys

## Error Handling

The library handles several types of errors:

### Rate Limits

Rate limit errors (HTTP 429, 403) are automatically handled:
- Detects rate limit from status code or error message
- Rotates to a different service account key
- Retries with exponential backoff
- Raises `APIError` if all keys are exhausted

### Missing Files

```python
from gsheet_cache import GSheetCacheConfig, CacheSheet

try:
    config = GSheetCacheConfig(keys_dir=Path("nonexistent"))
    sheet = CacheSheet("id", "Sheet1", config)
except FileNotFoundError as e:
    print(f"Error: {e}")
```

### Missing Sheets

```python
from gsheet_cache import GSheetCacheManager

try:
    manager = GSheetCacheManager(config)
    sheet = manager.get_sheet("unknown_id", "Unknown")
except ValueError as e:
    print(f"Error: {e}")
```

## Best Practices

### 1. Use Multiple Service Accounts

Create 3-5 service accounts to maximize your API quota:
- Each account has its own rate limit
- Automatic rotation distributes load
- Better resilience against quota issues

### 2. Batch Your Updates

Minimize API calls by batching updates:

```python
# Good: Single API call
sheet.update_value("A1", "Value 1")
sheet.update_value("A2", "Value 2")
sheet.update_value("A3", "Value 3")
sheet.flush_to_sheet(["A1", "A2", "A3"])

# Avoid: Multiple API calls
sheet.update_value("A1", "Value 1")
sheet.flush_to_sheet(["A1"])
sheet.update_value("A2", "Value 2")
sheet.flush_to_sheet(["A2"])
```

### 3. Enable Logging

Monitor key rotation and API usage:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# You'll see logs like:
# INFO - Using key: service-account-1.json
# WARNING - Rate limit error on attempt 1/3
# INFO - Rotating to new key: service-account-2.json
```

### 4. Handle Cache Directory

Ensure proper cache directory management:

```python
from pathlib import Path

# Create cache directory if needed
cache_dir = Path(".gsheet_cache")
cache_dir.mkdir(exist_ok=True)

config = GSheetCacheConfig(cache_dir=cache_dir)
```

### 5. Reset Failed Keys Periodically

If you have long-running processes:

```python
import time
from datetime import datetime, timedelta

last_reset = datetime.now()

while True:
    # Your processing logic
    sheet.update_value("A1", "data")
    sheet.flush_to_sheet(["A1"])

    # Reset failed keys every hour
    if datetime.now() - last_reset > timedelta(hours=1):
        sheet.reset_failed_keys()
        last_reset = datetime.now()
```

## Examples

See the `examples/` directory for complete examples:

- `key_rotation_example.py`: Demonstrates automatic key rotation
- More examples coming soon...

## Module Documentation

### Core Modules

- **`sheet.py`**: Core CacheSheet implementation with key rotation
- **`manager.py`**: Multi-sheet manager (GSheetCacheManager)
- **`config.py`**: Configuration classes (GSheetCacheConfig)
- **`schemas.py`**: Data models (GridRange)
- **`utils.py`**: Helper functions for range conversion

Each module includes comprehensive docstrings. Use Python's `help()` function:

```python
from gsheet_cache import CacheSheet
help(CacheSheet)
```

## Limitations

- Only supports reading/writing values (not formulas or formatting)
- Cache is stored as CSV (text-based values only)
- Requires service account authentication
- Initial load fetches entire sheet (not just specific ranges)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

[Your License Here]

## Support

For issues and questions:
- GitHub Issues: [Your Repo URL]
- Documentation: See docstrings in source code
- Examples: Check the `examples/` directory
