import time
import requests

def make_github_api_call(url, headers, params, retries=3, backoff_factor=2):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 500 and attempt < retries - 1:
                sleep_time = backoff_factor ** attempt
                time.sleep(sleep_time)
                continue
            else:
                raise
        except Exception as err:
            raise