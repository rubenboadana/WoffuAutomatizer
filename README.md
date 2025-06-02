# WoffuAutomatizer

A Python CLI tool for automating Woffu API interactions to manage flexible work schedules.

## Quick Start

1. **Setup - No Dependencies Required:**
   ```
   # Clone the repository
   git clone <repository-url>
   cd WoffuAutomatizer

   # Create and activate a virtual environment (recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Make script executable
   chmod +x woffu_api_cli_v2.py
   ```

2. **Usage:**
   ```
   ./woffu_api_cli_v2.py --token "your_jwt_token" [options]
   ```

## Key Options

| Option | Description |
|--------|-------------|
| `--token`, `-t` | **Required.** JWT Bearer token for authentication |
| `--template`, `-temp` | HTTP template file path |
| `--year`, `-y` | Year to check (defaults to current) |
| `--month`, `-m` | Month to check (defaults to current) |
| `--execute`, `-e` | Execute the generated HTTP requests |
| `--verbose`, `-v` | Enable verbose logging |

## How It Works

1. Authenticates with Woffu API using JWT token
2. Identifies flexible schedule days for the specified month
3. Creates HTTP request files for each day
4. Optionally executes requests to update schedules
