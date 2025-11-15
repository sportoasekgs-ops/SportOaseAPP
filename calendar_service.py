"""
Google Calendar Service für SportOase Buchungssystem
Erstellt automatisch Kalendereinträge bei Buchungen
"""

import os
import json
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Globale Variablen für Calendar Service
_calendar_service = None
_calendar_enabled = False

def init_calendar_service():
    """
    Initialisiert den Google Calendar Service mit Service Account Credentials
    Gibt True zurück wenn erfolgreich, False wenn Kalender deaktiviert ist
    """
    global _calendar_service, _calendar_enabled
    
    # Prüfe ob Google Calendar Credentials vorhanden sind
    credentials_json = os.environ.get('GOOGLE_CALENDAR_CREDENTIALS')
    
    if not credentials_json:
        print("INFO: Google Calendar nicht konfiguriert (GOOGLE_CALENDAR_CREDENTIALS fehlt)")
        _calendar_enabled = False
        return False
    
    try:
        # Parse die Service Account Credentials aus dem JSON String
        credentials_info = json.loads(credentials_json)
        
        # Erstelle Credentials Objekt
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        # Erstelle Calendar Service
        _calendar_service = build('calendar', 'v3', credentials=credentials)
        _calendar_enabled = True
        print("✓ Google Calendar Service erfolgreich initialisiert")
        return True
        
    except json.JSONDecodeError as e:
        print(f"FEHLER: Google Calendar Credentials sind kein gültiges JSON: {e}")
        _calendar_enabled = False
        return False
    except Exception as e:
        print(f"FEHLER: Google Calendar Service konnte nicht initialisiert werden: {e}")
        _calendar_enabled = False
        return False

def is_calendar_enabled():
    """Gibt True zurück wenn Google Calendar aktiviert ist"""
    return _calendar_enabled

def create_booking_event(booking_data):
    """
    Erstellt einen Google Calendar Eintrag für eine Buchung
    
    Args:
        booking_data: Dictionary mit Buchungsdaten
            - date: Datum als String (YYYY-MM-DD)
            - period: Stundennummer (1-6)
            - teacher_name: Name der Lehrkraft
            - teacher_class: Klasse der Lehrkraft
            - students: Liste von Schülern [{'name': '...', 'class': '...'}, ...]
            - offer_label: Label des Angebots
    
    Returns:
        Dictionary mit 'success' (True/False) und 'event_id' oder 'error'
    """
    global _calendar_service, _calendar_enabled
    
    # Wenn Calendar nicht aktiviert, gebe Warnung zurück
    if not _calendar_enabled:
        return {
            'success': False,
            'error': 'Google Calendar ist nicht konfiguriert'
        }
    
    try:
        from config import PERIOD_TIMES
        
        # Hole Zeitdaten für die Stunde
        period = booking_data['period']
        period_time = PERIOD_TIMES[period]
        
        # Erstelle Start- und End-Datetime
        booking_date = datetime.strptime(booking_data['date'], '%Y-%m-%d')
        
        # Parse Start- und Endzeit
        start_hour, start_minute = map(int, period_time['start'].split(':'))
        end_hour, end_minute = map(int, period_time['end'].split(':'))
        
        start_datetime = booking_date.replace(hour=start_hour, minute=start_minute)
        end_datetime = booking_date.replace(hour=end_hour, minute=end_minute)
        
        # Formatiere für Google Calendar (ISO 8601)
        start_time = start_datetime.isoformat()
        end_time = end_datetime.isoformat()
        
        # Erstelle Schülerliste für Beschreibung
        students_list = '\n'.join([
            f"  • {s['name']} ({s.get('klasse', s.get('class', 'N/A'))})" 
            for s in booking_data['students']
        ])
        
        # Erstelle Event
        event = {
            'summary': f"SportOase: {booking_data['offer_label']}",
            'description': f"""SportOase Buchung
            
Lehrkraft: {booking_data['teacher_name']} ({booking_data['teacher_class']})
Angebot: {booking_data['offer_label']}
Stunde: {period}. Stunde ({period_time['start']} - {period_time['end']})

Schüler ({len(booking_data['students'])}):
{students_list}

--- 
Erstellt durch SportOase Buchungssystem
""",
            'start': {
                'dateTime': start_time,
                'timeZone': 'Europe/Berlin',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Europe/Berlin',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 Tag vorher
                    {'method': 'popup', 'minutes': 60},       # 1 Stunde vorher
                ],
            },
        }
        
        # Hole Calendar ID aus Umgebungsvariablen (default: primary)
        calendar_id = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')
        
        # Erstelle Event in Google Calendar
        created_event = _calendar_service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        print(f"✓ Google Calendar Eintrag erstellt: {created_event.get('htmlLink')}")
        
        return {
            'success': True,
            'event_id': created_event['id'],
            'event_link': created_event.get('htmlLink')
        }
        
    except HttpError as error:
        error_msg = f"Google Calendar API Fehler: {error}"
        print(f"FEHLER: {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"Fehler beim Erstellen des Calendar Eintrags: {e}"
        print(f"FEHLER: {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }

def delete_booking_event(event_id):
    """
    Löscht einen Google Calendar Eintrag
    
    Args:
        event_id: Die Google Calendar Event ID
    
    Returns:
        Dictionary mit 'success' (True/False) und optional 'error'
    """
    global _calendar_service, _calendar_enabled
    
    if not _calendar_enabled:
        return {
            'success': False,
            'error': 'Google Calendar ist nicht konfiguriert'
        }
    
    if not event_id:
        return {
            'success': False,
            'error': 'Keine Event ID angegeben'
        }
    
    try:
        calendar_id = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')
        
        _calendar_service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        print(f"✓ Google Calendar Eintrag gelöscht: {event_id}")
        
        return {'success': True}
        
    except HttpError as error:
        error_msg = f"Google Calendar API Fehler: {error}"
        print(f"FEHLER: {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"Fehler beim Löschen des Calendar Eintrags: {e}"
        print(f"FEHLER: {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }
