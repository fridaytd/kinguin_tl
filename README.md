# Kinguin Price Automation Tool

A tool for automating Kinguin offers price adjustments based on competitor analysis and market data.

## Prerequisites

Before you begin, ensure you have the following installed:

### 1. Git
- Install Git from [git-scm.com](https://git-scm.com/downloads/win)
- Verify installation by running `git --version` in PowerShell

### 2. UV Package Manager
- Install UV by running this command in PowerShell:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- Restart PowerShell after installation
- Verify installation by running `uv --version`

## Installation

1. Open PowerShell in your desired installation directory
2. Clone the repository:
   ```powershell
   git clone https://github.com/fridaytd/kinguin_tl.git
   cd kinguin_tl
   ```
3. Set up configuration:
   - Copy `keys.json` to the project directory
   - Copy `setting.env` to the project directory

## Configuration

### Required Files

1. **`keys.json`** - Google Sheets API credentials
   - Obtain from Google Cloud Console
   - Place in the project root directory

2. **`setting.env`** - Application configuration
   ```env
   # Logger
   LOG_NAME="app_logger"
   LOG_LEVEL="INFO"
   IS_LOG_FILE="False"
   LOG_FILE_NAME="app.log"

   # Keys
   KEYS_PATH="keys.json"

   # Sheets
   SHEET_ID="your_spreadsheet_id"
   SHEET_NAME="Your Sheet Name"

   # Kinguin API
   KINGUIN_CLIENT_ID="your_client_id"
   KINGUIN_SECRET_KEY="your_secret_key"

   # My seller name
   MY_SELLER_NAME="YourSellerName"

   # Relax time each round in seconds
   RELAX_TIME_EACH_ROUND="10"

   # Thread number for parallel processing
   THREAD_NUMBER="3"
   ```

## Usage

### Running the Tool

Start the tool with automatic updates:
```powershell
.\run.ps1
```
