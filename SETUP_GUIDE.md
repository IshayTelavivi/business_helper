# Setup Guide for Nurit's Computer

Follow these steps using Claude Code on Nurit's computer.

## Prerequisites

- Windows 10 or 11
- Internet connection
- The following API keys (Ishay will provide):
  - ANTHROPIC_API_KEY
  - TAVILY_API_KEY
  - RESEND_API_KEY

## Step 1: Install Python

Check if Python is already installed:
```bash
python --version
```

If not installed:
1. Download Python from https://www.python.org/downloads/
2. Run the installer
3. **IMPORTANT**: Check the box "Add Python to PATH" at the bottom of the installer
4. Click "Install Now"
5. Verify: open a new terminal and run `python --version` — should show 3.9 or higher

## Step 2: Install Git

Check if Git is already installed:
```bash
git --version
```

If not installed:
1. Download Git from https://git-scm.com/download/win
2. Run the installer with default settings
3. Verify: open a new terminal and run `git --version`

## Step 3: Clone the repository

```bash
cd %USERPROFILE%\Documents
git clone https://github.com/IshayTelavivi/business_helper.git
cd business_helper
```

## Step 4: Create the .env file

Create a file named `.env` in the `business_helper` folder with this content:

```
ANTHROPIC_API_KEY=<paste the Anthropic key here>
TAVILY_API_KEY=<paste the Tavily key here>
RESEND_API_KEY=<paste the Resend key here>
```

No quotes around the keys. Just paste them directly after the `=` sign.

## Step 5: Create Nurit's profile

Copy the file `config/nurit_profile.json` into the `config/` folder.
This file contains Nurit's personal profile data and should NOT be committed to Git.

If the file is provided separately (e.g., via email or USB), place it at:
```
business_helper/config/nurit_profile.json
```

## Step 6: First run

Double-click `start.bat` in the `business_helper` folder.

On the first run it will:
1. Install Python dependencies (takes 1-2 minutes, only happens once)
2. Start the application
3. Open the browser automatically at http://localhost:8501
4. Load Nurit's profile into the database

## Daily Usage

- Double-click `start.bat` to open the app
- Close the black terminal window to stop the app
- The app saves all data locally — search history, settings, etc.

## Updating the App

If Ishay pushes updates to the code:
```bash
cd %USERPROFILE%\Documents\business_helper
git pull
```

Or simply tell Claude Code: "pull the latest changes from GitHub"

Then double-click `start.bat` again.

## Troubleshooting

- **"Python is not installed"**: Install Python and make sure "Add to PATH" was checked
- **"Missing API keys"**: Check that the `.env` file exists and has all 3 keys
- **Browser doesn't open**: Manually go to http://localhost:8501
- **Port already in use**: Close any other terminal windows running the app, then try again
