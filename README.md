# Woffu Automatizer

A Python CLI tool to automatically generate and execute HTTP requests for Woffu API to fill flexible schedule days.

## Features

- **Automatic Detection**: Identifies flexible schedule days that need to be filled
- **Template-based**: Uses HTTP templates for consistent request generation
- **Execution Support**: Can automatically execute the generated HTTP requests
- **Today Mode**: Process only today's entry for quick daily automation
- **Flexible Filtering**: Process specific months/years or just recent entries
- **JWT Support**: Extracts user information directly from JWT tokens

## Installation

No external dependencies required! The tool uses only Python standard library modules.

```bash
git clone <repository-url>
cd WoffuAutomatizer
chmod +x woffu_api_cli_v2.py
```

## Usage

### Basic Usage

```bash
# Generate HTTP requests for flexible schedule days
python3 woffu_api_cli_v2.py --token "your_jwt_token"

# Generate and execute HTTP requests immediately
python3 woffu_api_cli_v2.py --token "your_jwt_token" --execute
```

### Today Mode (New!)

Process only today's diary entry - perfect for daily automation:

```bash
# Check if today is a flexible schedule day and generate request
python3 woffu_api_cli_v2.py --token "your_jwt_token" --today

# Process today's entry and execute immediately
python3 woffu_api_cli_v2.py --token "your_jwt_token" --today --execute

# Today mode with verbose logging
python3 woffu_api_cli_v2.py --token "your_jwt_token" --today --verbose
```

### Advanced Usage

```bash
# Process specific month/year
python3 woffu_api_cli_v2.py --token "your_jwt_token" --year 2025 --month 11

# Use custom template and output directory
python3 woffu_api_cli_v2.py --token "your_jwt_token" \
  --template custom_template.http \
  --output-dir /path/to/output

# Enable debug logging
python3 woffu_api_cli_v2.py --token "your_jwt_token" --debug
```

## Command Line Arguments

| Argument | Short | Description |
|----------|--------|-------------|
| `--token` | `-t` | **Required.** JWT Bearer token for Woffu API authentication |
| `--today` | | **New!** Process only today's entry (if it's a flexible schedule day) |
| `--execute` | `-e` | Execute the generated HTTP requests immediately |
| `--template` | `-temp` | Path to HTTP template file (default: `template.http`) |
| `--output-dir` | `-o` | Output directory for HTTP files (default: `requests/`) |
| `--year` | `-y` | Year to check (defaults to current year) |
| `--month` | `-m` | Month to check (defaults to current month) |
| `--verbose` | `-v` | Enable verbose logging |
| `--debug` | `-d` | Enable debug mode (extra verbose logging) |

## How It Works

1. **JWT Parsing**: Extracts user ID from the provided JWT token
2. **API Query**: Fetches monthly diary entries from Woffu API
3. **Filtering**: Identifies flexible schedule days that need to be filled:
   - Entry has `in: '_FlexibleSchedule'`
   - Entry has empty `out` field
   - Not a holiday or weekend
   - For regular mode: entries before today
   - For `--today` mode: only today's entry
4. **Generation**: Creates HTTP request files from template
5. **Execution** (optional): Executes the requests using curl

## Template Format

The tool uses an HTTP template file (`template.http`) with placeholders:

```http
PUT https://aetion.woffu.com/api/diaries/DIARY_ID/workday/slots/self
Authorization: Bearer TOKEN_PLACEHOLDER
Content-Type: application/json

{
  "date": "2025-11-15",
  "userId": 0,
  "slots": [
    {
      "in": "09:00",
      "out": "18:00",
      "userId": 0
    }
  ]
}
```

Placeholders that get replaced:
- `DIARY_ID` → Actual diary ID from API
- `TOKEN_PLACEHOLDER` → Your JWT token
- `"date": "..."` → Actual diary date
- `"userId": 0` → Your user ID

## Use Cases

### Daily Automation
Use `--today` mode for daily automation (perfect for cron jobs or GitHub Actions):

```bash
# Daily cron job at 9 AM
0 9 * * 1-5 cd /path/to/WoffuAutomatizer && python3 woffu_api_cli_v2.py --token "$WOFFU_TOKEN" --today --execute
```

### Monthly Catch-up
Process all missing entries for the current month:

```bash
python3 woffu_api_cli_v2.py --token "your_jwt_token" --execute
```

### Historical Processing
Fill entries for a specific month:

```bash
python3 woffu_api_cli_v2.py --token "your_jwt_token" --year 2025 --month 10 --execute
```

## GitHub Actions Integration (Optional)

If you want to run the automation via GitHub Actions, you can set up your own workflow.

### Quick Setup Steps

1. **Create a workflow file** at `.github/workflows/daily-woffu-automation.yml`
2. **Add your JWT as a repository secret:**
   - Go to your repository Settings > Secrets and variables > Actions
   - Create a new secret named `WOFFU_JWT` with your actual JWT token
3. **Commit and push** the workflow file

### Example Workflow

Here's a sample workflow that runs Monday-Friday at 7PM UTC:

```yaml
name: Daily Woffu Automation

on:
  schedule:
    - cron: '0 19 * * 1-5'  # 7PM UTC, Mon-Fri
  workflow_dispatch:

jobs:
  fill-timesheet:
      runs-on: ubuntu-latest

      steps:
          - name: Checkout repository
            uses: actions/checkout@v4

          - name: Set up Python
            uses: actions/setup-python@v4
            with:
                python-version: '3.x'

          - name: Verify JWT secret is set
            env:
                WOFFU_JWT: ${{ secrets.WOFFU_JWT }}
            run: |
                if [ -z "${WOFFU_JWT}" ]; then
                  echo "ERROR: WOFFU_JWT secret is not set. Add it to repository secrets."
                  echo "Go to: Repository Settings > Secrets and variables > Actions > New repository secret"
                  echo "Name: WOFFU_JWT"
                  echo "Value: your_jwt_token_here"
                  exit 1
                fi
                echo "JWT secret found ✓"

          - name: Fill today's timesheet
            env:
                WOFFU_JWT: ${{ secrets.WOFFU_JWT }}
            run: |
                echo "🕰️  Running daily Woffu automation at $(date)"
                python3 woffu_api_cli_v2.py --token "${WOFFU_JWT}" --today --execute --verbose

          - name: Upload generated HTTP files (on failure)
            if: failure()
            uses: actions/upload-artifact@v4
            with:
                name: woffu-requests-${{ github.run_number }}
                path: requests/
                retention-days: 7
```

### Privacy Considerations

- Use a private repository or fork to a private repo for running the automation

## Output

The tool generates:
- HTTP request files in the output directory
- Detailed logs about the process
- Execution results if `--execute` is used

Example output:
```
2025-11-15 09:00:00 - woffu_api_cli - INFO - Today-only mode: will only process today's entry (2025-11-15)
2025-11-15 09:00:00 - woffu_api_cli - INFO - Found flexible schedule for date 2025-11-15
2025-11-15 09:00:00 - woffu_api_cli - INFO - Created HTTP request file: requests/woffu_request_2025-11-15.http
2025-11-15 09:00:00 - woffu_api_cli - INFO - ✅ Successfully executed request
```

## Troubleshooting

**"No flexible schedule days found"**: This is normal if:
- All your flexible days are already filled
- Today is not a flexible schedule day (in `--today` mode)
- You're checking future dates

**"Permission denied"**: Make sure the script is executable:
```bash
chmod +x woffu_api_cli_v2.py
```

**JWT token issues**: Ensure your token is valid and not expired. You can check the token payload in debug mode.

## License

This project is for personal/internal use. Please respect Woffu's API terms of service.
