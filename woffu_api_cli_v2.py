#!/usr/local/bin/python3
import argparse
import json
import os
import re
import urllib.request
import urllib.error
import urllib.parse
import sys
import time
import ssl
import subprocess
from datetime import datetime, timedelta, date
import calendar
from typing import Dict, Any, List, Optional, Tuple
import logging


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("woffu_api_cli")


class WoffuApiClient:
    """Client for interacting with the Woffu API."""

    def __init__(self, token: str):
        if not token:
            raise ValueError("JWT token is required for API authentication")
        self.token = token
        self.base_url = "https://aetion.woffu.com/api"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.cache = {}
        # Ignore SSL certificate verification
        self.ssl_context = ssl._create_unverified_context()

    def get_users(self) -> List[Dict[str, Any]]:
        """Fetch users from the Woffu API."""
        if "users" in self.cache:
            return self.cache["users"]

        endpoint = f"{self.base_url}/users"
        response = self._make_request("GET", endpoint)
        self.cache["users"] = response
        return response

    def get_user_id_from_token(self) -> int:
        """Extract user ID from the current token or API call without using PyJWT."""
        try:
            # Simple JWT token parsing without external dependencies
            parts = self.token.split(".")
            if len(parts) != 3:
                logger.error("Invalid JWT format: token doesn't have three parts")
                return self._get_user_id_from_api()

            # Decode the payload (second part)
            import base64

            # Add padding if needed
            payload = parts[1]
            padding_needed = len(payload) % 4
            if padding_needed:
                payload += '=' * (4 - padding_needed)

            try:
                # Replace characters that are different in URL-safe base64
                payload = payload.replace("-", "+").replace("_", "/")

                # Decode the payload
                decoded_bytes = base64.b64decode(payload)
                decoded_payload = json.loads(decoded_bytes.decode('utf-8'))

                if "UserId" in decoded_payload:
                    user_id = int(decoded_payload["UserId"])
                    logger.debug(f"Extracted user ID from token: {user_id}")
                    return user_id
                else:
                    logger.error("Token does not contain UserId claim")
                    logger.debug(f"Token claims: {decoded_payload.keys()}")
                    return self._get_user_id_from_api()

            except Exception as e:
                logger.error(f"Error decoding token payload: {e}")
                return self._get_user_id_from_api()

        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
            return self._get_user_id_from_api()

    def _get_user_id_from_api(self) -> Optional[int]:
        """Fallback method to get user ID from API call."""
        logger.info("Attempting to get user information from API...")
        try:
            endpoint = f"{self.base_url}/users/self"
            response = self._make_request("GET", endpoint)
            if response and "id" in response:
                user_id = int(response["id"])
                logger.info(f"Retrieved user ID from API: {user_id}")
                return user_id
            else:
                logger.error("Could not get user ID from API response")
                return None
        except Exception as e:
            logger.error(f"Error fetching user information from API: {e}")
            return None

    def get_monthly_diaries(self, user_id: int, year: int, month: int) -> List[Dict[str, Any]]:
        """Fetch monthly diaries summary for a specific user and month."""
        cache_key = f"monthly_diaries_{user_id}_{year}_{month}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Calculate first and last day of the month
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        # Format dates as YYYY-MM-DD
        from_date = first_day.strftime("%Y-%m-%d")
        to_date = last_day.strftime("%Y-%m-%d")

        endpoint = f"{self.base_url}/svc/core/diariesquery/users/{user_id}/diaries/summary/presence"
        params = {
            "userId": user_id,
            "fromDate": from_date,
            "toDate": to_date,
            "pageSize": calendar.monthrange(year, month)[1],  # Days in month
            "includeHourTypes": "true",
            "includeNotHourTypes": "true",
            "includeDifference": "true"
        }

        try:
            response = self._make_request("GET", endpoint, params=params)

            # Extract the diaries from the response
            if isinstance(response, dict) and "diaries" in response:
                diaries = response["diaries"]
                logger.debug(f"Successfully extracted {len(diaries)} diaries from response")
                self.cache[cache_key] = diaries
                return diaries
            else:
                logger.error("Response doesn't contain 'diaries' field")
                logger.debug(f"Response structure: {response.keys() if isinstance(response, dict) else type(response)}")
                return []

        except Exception as e:
            logger.error(f"Error fetching monthly diaries: {e}")
            return []

    def get_user_diaries(self, user_id: int) -> List[Dict[str, Any]]:
        """Fetch diaries for a specific user."""
        cache_key = f"diaries_{user_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        endpoint = f"{self.base_url}/diaries?userId={user_id}"
        response = self._make_request("GET", endpoint)
        self.cache[cache_key] = response
        return response

    def _make_request(self, method: str, url: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        """Make an HTTP request to the Woffu API using urllib."""
        try:
            # Add query parameters to URL if provided
            if params:
                query_string = urllib.parse.urlencode(params)
                url = f"{url}?{query_string}"

            # Create request with headers
            req = urllib.request.Request(url)
            for key, value in self.headers.items():
                req.add_header(key, value)

            # Set request method
            req.method = method

            # Add data if provided (for POST/PUT)
            if data and method in ["POST", "PUT"]:
                json_data = json.dumps(data).encode('utf-8')
                req.add_header('Content-Length', str(len(json_data)))

            # Make the request
            logger.debug(f"Making {method} request to {url}")
            if data and method in ["POST", "PUT"]:
                response = urllib.request.urlopen(req, data=json_data, context=self.ssl_context)
            else:
                response = urllib.request.urlopen(req, context=self.ssl_context)

            # Parse response
            response_data = response.read().decode('utf-8')
            return json.loads(response_data)

        except urllib.error.HTTPError as e:
            error_msg = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
            logger.error(f"API error ({e.code}): {error_msg}")
            raise
        except urllib.error.URLError as e:
            logger.error(f"URL error: {e.reason}")
            raise
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise


class HttpTemplateProcessor:
    """Process HTTP template files and populate them with data."""

    def __init__(self, template_path: str, api_client: WoffuApiClient):
        self.template_path = template_path
        self.api_client = api_client
        self.template = self._read_template()

    def _read_template(self) -> str:
        """Read the HTTP template file."""
        try:
            with open(self.template_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading template file: {e}")
            sys.exit(1)

    def create_http_request(self, diary: Dict[str, Any], user_id: int, output_dir: str) -> str:
        """Create an HTTP request file for a specific diary entry."""
        # Start with the template content
        processed_content = self.template

        # Extract diary information
        diary_id = diary.get('diaryId')
        diary_date = diary.get('date')

        # Replace all occurrences of DIARY_ID with the actual diary ID
        processed_content = processed_content.replace('DIARY_ID', str(diary_id))

        # Replace TOKEN_PLACEHOLDER with the actual token
        processed_content = processed_content.replace('TOKEN_PLACEHOLDER', self.api_client.token)

        # Replace date placeholder
        processed_content = re.sub(r'"date":\s*"[^"]+"', f'"date": "{diary_date}"', processed_content)

        # Replace all userIds with the actual user ID
        processed_content = re.sub(r'"userId":\s*0', f'"userId": {user_id}', processed_content)

        # Create a filename based on the date
        filename = f"woffu_request_{diary_date}.http"
        output_path = os.path.join(output_dir, filename)

        # Write to output file
        try:
            with open(output_path, 'w') as f:
                f.write(processed_content)
            logger.info(f"Created HTTP request file: {output_path}")
        except Exception as e:
            logger.error(f"Error writing output file: {e}")
            sys.exit(1)

        return output_path

def filter_diaries(diaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter diaries based on the specified criteria."""
    filtered = []
    today = datetime.now().date()

    logger.info(f"Filtering {len(diaries)} diaries")
    logger.info(f"Today is {today}, will only process entries before today")

    # First filter: only keep diaries before today
    diaries_before_today = []
    for diary in diaries:
        diary_date_str = diary.get('date')
        try:
            diary_date = datetime.strptime(diary_date_str, "%Y-%m-%d").date()
            if diary_date >= today:
                logger.info(f"Skipping diary for {diary_date_str} as it's not before today")
                continue
            diaries_before_today.append(diary)
        except (ValueError, TypeError):
            logger.warning(f"Invalid or missing date format in diary: {diary_date_str}")
            continue

    logger.info(f"Found {len(diaries_before_today)} diaries before today out of {len(diaries)} total days")

    # Second filter: check if it's a flexible schedule day that needs to be filled
    for diary in diaries_before_today:
        # Make sure the diary has all the fields we need before accessing them
        if not all(key in diary for key in ['in', 'out', 'isHoliday', 'isWeekend']):
            logger.warning(f"Diary missing required fields: {diary}")
            continue

        # Print the diary for debugging
        logger.debug(f"Examining diary: {json.dumps(diary, indent=2)}")

        # Check if this is a flexible schedule day that needs to be filled
        is_flexible_schedule = (
            diary.get('in') == '_FlexibleSchedule' and
            diary.get('out') == '' and
            not diary.get('isHoliday', False) and
            not diary.get('isWeekend', False)
        )

        if is_flexible_schedule:
            logger.info(f"Found flexible schedule for date {diary.get('date')}")
            filtered.append(diary)

    logger.info(f"Found {len(filtered)} flexible schedule days before today that need to be filled")
    return filtered


def get_current_month_year() -> Tuple[int, int]:
    """Get the current month and year."""
    now = datetime.now()
    return now.year, now.month


def setup_output_directory(base_dir: str) -> str:
    """Set up the output directory for HTTP request files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_dir, f"woffu_requests_{timestamp}")

    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")
    except Exception as e:
        logger.error(f"Error creating output directory: {e}")
        sys.exit(1)

    return output_dir

def execute_http_request(file_path: str) -> Tuple[bool, str]:
   """Execute an HTTP request file using curl.

   Args:
       file_path: Path to the HTTP request file to execute

   Returns:
       A tuple containing (success_flag, result_or_error_message)
   """
   try:
       # Parse the HTTP request file
       with open(file_path, 'r') as f:
           content = f.read()

       # Split the content into headers and body
       parts = content.split('\n\n', 1)
       if len(parts) < 2:
           logger.error(f"Invalid HTTP request format in {file_path} - missing body")
           return False, "Invalid HTTP request format: missing body"

       header_section, body = parts
       header_lines = header_section.split('\n')

       # Extract method and URL from the first line
       method = "POST"  # Default method
       url = None
       for i, line in enumerate(header_lines):
           if i == 0 and line.startswith('//'):  # Skip comment line
               continue
           if i <= 1 and ' ' in line and not line.startswith('//') and not line.startswith('#'):
               parts = line.split(' ', 1)
               method = parts[0]
               url = parts[1]
               logger.debug(f"Extracted method: {method}, URL: {url}")
               break

       if not url:
           logger.error(f"Could not extract URL from {file_path}")
           return False, "Could not extract URL from HTTP file"

       # Extract headers
       headers = []
       for line in header_lines:
           if ': ' in line and not line.startswith('//') and not line.startswith('#'):
               headers.append(f"-H '{line}'")

       # Create a temporary file for the body
       import tempfile
       body_file = tempfile.NamedTemporaryFile(delete=False, mode='w')

       try:
           # Write body to temp file
           body_file.write(body)
           body_file.close()

           # Build curl command with headers and body
           curl_cmd = f"curl -s -S -i -X {method} {' '.join(headers)} -d @{body_file.name} '{url}'"

           logger.debug(f"Executing curl command: {curl_cmd}")

           # Execute the curl command
           result = subprocess.run(
               curl_cmd,
               shell=True,
               capture_output=True,
               text=True,
               check=False
           )

           logger.debug(result)
           # Check if the request was successful
           if result.returncode == 0 and ("200 OK" in result.stdout or "201 Created" in result.stdout or "204" in result.stdout):
               return True, result.stdout
           else:
               error_msg = result.stderr if result.stderr else result.stdout
               logger.error(f"Curl command failed: {error_msg}")
               return False, error_msg

       finally:
           # Clean up the temporary body file
           try:
               os.unlink(body_file.name)
           except Exception as e:
               logger.warning(f"Failed to delete temporary file: {e}")

   except Exception as e:
       logger.error(f"Error executing HTTP request: {e}")
       return False, str(e)


def main():
    parser = argparse.ArgumentParser(description='Generate Woffu API HTTP requests for flexible schedule days')
    parser.add_argument('--token', '-t', required=True,
                        help='JWT Bearer token for Woffu API authentication')
    parser.add_argument('--template', '-temp',
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.http'),
                        help='Path to the HTTP template file')
    parser.add_argument('--output-dir', '-o',
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requests'),
                        help='Directory where HTTP request files will be created')
    parser.add_argument('--year', '-y', type=int, help='Year to check (defaults to current year)')
    parser.add_argument('--month', '-m', type=int, help='Month to check (defaults to current month)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode (extra verbose)')
    parser.add_argument('--execute', '-e', action='store_true', help='Execute the generated HTTP requests')

    args = parser.parse_args()

    # Set logging level - Force root logger and our logger to have same level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        print("Debug mode enabled - You should see detailed logs")
    elif args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logger.setLevel(logging.INFO)
        print("Verbose mode enabled")

    # Create requests directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir, exist_ok=True)
        logger.info(f"Created output directory: {args.output_dir}")

    # Check if template file exists
    if not os.path.exists(args.template):
        logger.error(f"Template file not found: {args.template}")
        sys.exit(1)

    # Get year and month (default to current)
    year, month = args.year, args.month
    if year is None or month is None:
        current_year, current_month = get_current_month_year()
        year = year or current_year
        month = month or current_month

    # Initialize API client
    try:
        api_client = WoffuApiClient(args.token)
        logger.debug("API client initialized successfully with provided token")
    except Exception as e:
        logger.error(f"Failed to initialize API client: {e}")
        sys.exit(1)

    try:
        # Get user ID
        logger.info("Retrieving user ID from Woffu API...")
        user_id = api_client.get_user_id_from_token()
        if not user_id:
            logger.error("Failed to retrieve user ID")
            sys.exit(1)

        logger.info(f"Retrieved user ID: {user_id}")

        # Get monthly diaries
        logger.info(f"Fetching diaries for {year}-{month:02d}")
        monthly_diaries = api_client.get_monthly_diaries(user_id, year, month)

        if not monthly_diaries:
            logger.error("No diaries found for the specified month")
            sys.exit(1)

        logger.debug(f"Found {len(monthly_diaries)} diaries")

        # Print a sample diary for debugging
        if monthly_diaries and len(monthly_diaries) > 0:
            logger.debug(f"Sample diary: {json.dumps(monthly_diaries[0], indent=2)}")

        # Filter diaries based on criteria
        filtered_diaries = filter_diaries(monthly_diaries)

        if not filtered_diaries:
            logger.info("No flexible schedule days found that need to be filled")
            sys.exit(0)

        logger.info(f"Found {len(filtered_diaries)} flexible schedule days that need to be filled")

        # Setup output directory
        output_dir = args.output_dir
        logger.info(f"Using output directory: {output_dir}")

        # Initialize template processor
        processor = HttpTemplateProcessor(args.template, api_client)

        # Create HTTP request files for each filtered diary
        created_files = []
        for diary in filtered_diaries:
            output_path = processor.create_http_request(diary, user_id, output_dir)
            created_files.append(output_path)

        # Print summary
        logger.info("\nSummary:")
        logger.info(f"- User ID: {user_id}")
        logger.info(f"- Month: {year}-{month:02d}")
        logger.info(f"- Flexible schedule days: {len(filtered_diaries)}")
        logger.info(f"- HTTP request files created: {len(created_files)}")
        logger.info(f"- Output directory: {output_dir}")

        # Execute HTTP requests if --execute flag is set
        if args.execute:
            logger.info("\nExecuting HTTP requests...")
            results = []

            for file_path in created_files:
                logger.info(f"Executing request from {os.path.basename(file_path)}...")
                success, result = execute_http_request(file_path)
                results.append((file_path, success, result))

                if success:
                    logger.info(f"✅ Successfully executed request")
                    if args.debug:
                        logger.debug(f"Response: {result}")
                else:
                    logger.error(f"❌ Failed to execute request: {result}")

                # Add a small delay between requests to avoid rate limiting
                time.sleep(1)

            # Summary of execution results
            successful = sum(1 for _, success, _ in results if success)
            logger.info(f"\nExecution Summary:")
            logger.info(f"- Successfully executed: {successful}/{len(results)}")
            if successful < len(results):
                logger.info(f"- Failed: {len(results) - successful}/{len(results)}")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


