from googleapiclient.discovery import build
import logging

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'


def create_yt_service(api_key):
    try:
        # Get credentials and create an API client
        service = build(API_SERVICE_NAME, API_VERSION, developerKey=api_key)
        print(API_SERVICE_NAME, 'service created successfully')
        return service
    except Exception as e:
        print('Unable to connect.')
        print(e)
        return None


def check_api(api_key):
    try:
        # Get credentials and create an API client
        build(API_SERVICE_NAME, API_VERSION, developerKey=api_key)
        return "API access successful"
    except Exception as e:
        print('Unable to connect.')
        return e