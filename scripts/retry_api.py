import time
import requests

def retry_api_request(url, params, retries=5, backoff_factor=1):
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f'Request failed: {e}')
            if attempt < retries - 1:
                sleep_time = backoff_factor * (2 ** attempt)
                print(f'Retrying in {sleep_time} seconds...')
                time.sleep(sleep_time)
            else:
                raise

# Example usage:
# url = 'https://api.github.com/repos/SuperInstance/zero-poc/issues'
# params = {'state': 'open'}
# try:
#     issues = retry_api_request(url, params)
#     print(issues)
# except Exception as e:
#     print(f'Failed to retrieve issues: {e}')