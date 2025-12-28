# Installation Guide

This guide will walk you through setting up the Kinguin Price Automation Tool on your system.

## Table of Contents

- [System Requirements](#system-requirements)
- [Prerequisites](#prerequisites)
- [Installation Steps](#installation-steps)
- [Configuration](#configuration)

## System Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux
- **Python**: 3.8 or higher (automatically managed by UV)
- **RAM**: Minimum 4GB (8GB recommended for multiple threads)
- **Storage**: 500MB free space
- **Internet**: Stable connection required for API calls and web scraping

## Prerequisites

Before installing the tool, you need to install the following software:

### 1. Git

Git is required to clone the repository and pull updates.

#### Windows
Download and install from [git-scm.com](https://git-scm.com/downloads/win)

Verify installation:
```powershell
git --version
```

#### macOS
```bash
# Using Homebrew
brew install git

# Verify installation
git --version
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install git

# Fedora
sudo dnf install git

# Verify installation
git --version
```

### 2. UV Package Manager

UV is a fast Python package manager that handles dependencies and virtual environments.

#### Windows
Open PowerShell and run:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart PowerShell after installation and verify:
```powershell
uv --version
```

#### macOS/Linux
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

### 3. Google Sheets API Credentials

You'll need service account credentials to access Google Sheets:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API
4. Create a service account
5. Download the JSON key file
6. Save it as `keys.json` (or multiple files in the `keys/` directory for rotation)

## Installation Steps

### Step 1: Clone the Repository

Open your terminal/command prompt in your desired installation directory:

#### Windows (PowerShell)
```powershell
cd C:\your\desired\path
git clone https://github.com/fridaytd/kinguin_tl.git
cd kinguin_tl
```

#### macOS/Linux
```bash
cd ~/your/desired/path
git clone https://github.com/fridaytd/kinguin_tl.git
cd kinguin_tl
```

### Step 2: Set Up Configuration Files

#### 2.1 Create Keys Directory

Create a `keys` directory and add your Google Sheets service account JSON files:

```bash
mkdir -p keys
```

Copy your service account JSON files into the `keys/` directory. You can have multiple key files for API rate limit rotation:
- `keys/service-account-1.json`
- `keys/service-account-2.json`
- `keys/service-account-3.json`

#### 2.2 Create Environment Configuration

Create a `setting.env` file in the project root:

```bash
# Copy the example below and customize it
```

**`setting.env`** template:
```env
# Google Sheets Configuration
SHEET_ID="your_google_spreadsheet_id_here"
SHEET_NAME="Sheet1"

# Kinguin API Credentials
KINGUIN_CLIENT_ID="your_kinguin_client_id"
KINGUIN_SECRET_KEY="your_kinguin_secret_key"

# Seller Configuration
MY_SELLER_NAME="YourSellerName"

# Performance Settings
RELAX_TIME_EACH_ROUND="10"
THREAD_NUMBER="3"
```

**Configuration Parameters Explained:**

- `SHEET_ID`: Your Google Spreadsheet ID (found in the URL)
- `SHEET_NAME`: Name of the sheet/tab to process
- `KINGUIN_CLIENT_ID`: Your Kinguin API client ID
- `KINGUIN_SECRET_KEY`: Your Kinguin API secret key
- `MY_SELLER_NAME`: Your seller name on Kinguin
- `RELAX_TIME_EACH_ROUND`: Seconds to wait between processing rounds
- `THREAD_NUMBER`: Number of parallel threads (recommended: 2-5)


### Step 4: Share Your Google Sheet

Share your Google Spreadsheet with the service account email(s):

1. Open your Google Sheet
2. Click "Share" button
3. Add the service account email from your `keys/*.json` files
4. Give "Editor" permissions
5. Service account emails look like: `account-name@project-id.iam.gserviceaccount.com`

### Step 5: Run the Application
```powershell
.\run.ps1
``` 