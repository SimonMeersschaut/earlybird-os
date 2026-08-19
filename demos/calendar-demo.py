import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Read-only scope for calendar events
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

GOOGLE_CALENDAR_SECRET = "secret.env"

def get_calendar_service():
    creds = None
    # Token file stores access and refresh tokens after first authorization
    if os.path.exists(GOOGLE_CALENDAR_SECRET):
        creds = Credentials.from_authorized_user_file(GOOGLE_CALENDAR_SECRET, SCOPES)
        
    # Prompt login if credentials are invalid or don't exist
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save credentials for future runs
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

def get_next_event():
    service = get_calendar_service()

    # Get current time in ISO format (required by Google API)
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    
    # Fetch the next upcoming event
    events_result = service.events().list(
        calendarId='primary', 
        timeMin=now,
        maxResults=1, 
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
        return None

    event = events[0]
    start = event['start'].get('dateTime', event['start'].get('date'))
    summary = event.get('summary', 'No Title')
    
    print(f"Next Event: {summary} at {start}")
    return {"summary": summary, "start": start}

if __name__ == '__main__':
    get_next_event()