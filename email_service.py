import os
import json
import logging
from datetime import datetime

import resend

from config import ADMIN_EMAIL

def get_resend_credentials():
    """Holt Resend API-Key über Replit Connector"""
    hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')
    
    x_replit_token = None
    if os.environ.get('REPL_IDENTITY'):
        x_replit_token = 'repl ' + os.environ.get('REPL_IDENTITY')
    elif os.environ.get('WEB_REPL_RENEWAL'):
        x_replit_token = 'depl ' + os.environ.get('WEB_REPL_RENEWAL')
    
    if not x_replit_token or not hostname:
        print("[EMAIL] Replit Connector nicht verfügbar")
        return None, None
    
    try:
        import requests
        response = requests.get(
            f'https://{hostname}/api/v2/connection?include_secrets=true&connector_names=resend',
            headers={
                'Accept': 'application/json',
                'X_REPLIT_TOKEN': x_replit_token
            },
            timeout=10
        )
        data = response.json()
        connection = data.get('items', [{}])[0] if data.get('items') else {}
        settings = connection.get('settings', {})
        
        api_key = settings.get('api_key')
        from_email = settings.get('from_email')
        
        if api_key:
            print(f"[EMAIL] Resend API-Key gefunden, From: {from_email}")
            return api_key, from_email
        else:
            print("[EMAIL] Resend nicht konfiguriert")
            return None, None
            
    except Exception as e:
        print(f"[EMAIL] Fehler beim Abrufen der Resend-Credentials: {e}")
        return None, None


def send_email_resend(to_email, subject, body_html, body_text=None):
    """Sendet E-Mail über Resend API"""
    logger = logging.getLogger(__name__)
    
    logger.info(f"Versuche E-Mail zu senden an: {to_email}")
    
    try:
        api_key, from_email = get_resend_credentials()
        
        if not api_key:
            print(f"[EMAIL] WARNUNG: Resend nicht konfiguriert - E-Mail an {to_email} nicht gesendet")
            return False
        
        resend.api_key = api_key
        
        params = {
            "from": from_email or "SportOase <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "html": body_html,
        }
        
        if body_text:
            params["text"] = body_text
        
        result = resend.Emails.send(params)
        
        print(f"[EMAIL] Erfolgreich gesendet an {to_email} (ID: {result.get('id', 'unknown')})")
        return True
        
    except Exception as e:
        print(f"[EMAIL] FEHLER beim E-Mail-Versand an {to_email}: {e}")
        return False


def create_booking_notification_email(data):
    """Erstellt eine formatierte E-Mail für Buchungsbenachrichtigungen"""
    teacher = data.get("teacher_name", "Unbekannt")
    teacher_class = data.get("teacher_class", "")
    date = data.get("date", "")
    weekday = data.get("weekday", "")
    period = data.get("period", "")
    offer = data.get("offer_label", "")
    offer_type = data.get("offer_type", "")

    students_json = data.get("students_json", "[]")
    students = json.loads(students_json) if isinstance(students_json, str) else students_json
    count = len(students)

    students_html = "<br>".join(
        [f"• {s['name']} (Klasse {s['klasse']})" for s in students]
    ) if students else "Keine Schüler"
    
    students_list = ", ".join(
        [f"{s['name']} ({s['klasse']})" for s in students]
    ) if students else "Keine Schüler"

    subject = f"SportOase Buchung: {offer} am {date}"

    html = f"""
    <html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 15px 20px; border-radius: 8px; margin: 0 0 20px 0;">
                Neue Buchung – SportOase
            </h2>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                <p style="margin: 10px 0; padding: 12px; background: white; border-radius: 4px; border-left: 4px solid #3b82f6;">
                    <strong style="color: #3b82f6;">Lehrkraft:</strong> {teacher} {f"({teacher_class})" if teacher_class else ""}
                </p>
                <p style="margin: 10px 0; padding: 12px; background: white; border-radius: 4px; border-left: 4px solid #3b82f6;">
                    <strong style="color: #3b82f6;">Datum:</strong> {date} ({weekday})
                </p>
                <p style="margin: 10px 0; padding: 12px; background: white; border-radius: 4px; border-left: 4px solid #3b82f6;">
                    <strong style="color: #3b82f6;">Stunde:</strong> {period}. Stunde
                </p>
                <p style="margin: 10px 0; padding: 12px; background: white; border-radius: 4px; border-left: 4px solid #3b82f6;">
                    <strong style="color: #3b82f6;">Angebot:</strong> {offer} – <span style="background: #3b82f6; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{offer_type.upper()}</span>
                </p>
                <div style="margin: 15px 0; padding: 15px; background: white; border-radius: 4px;">
                    <strong style="color: #3b82f6;">Schüler ({count}):</strong>
                    <div style="margin-top: 10px; margin-left: 10px;">
                        {students_html}
                    </div>
                </div>
            </div>
            <p style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 12px;">
                Diese Nachricht wurde automatisch vom SportOase Buchungssystem generiert.<br>
                Zeit: {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}
            </p>
        </div>
    </body></html>
    """

    text = f"""
Neue Buchung – SportOase

Lehrkraft: {teacher} {f"({teacher_class})" if teacher_class else ""}
Datum: {date} ({weekday})
Stunde: {period}. Stunde
Angebot: {offer} ({offer_type})

Schüler ({count}):
{students_list}

---
Zeit: {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}
Diese Nachricht wurde automatisch vom SportOase Buchungssystem generiert.
    """

    return subject, html, text


def send_booking_notification(data):
    """Sendet Buchungsbenachrichtigung an Admin"""
    subject, html, text = create_booking_notification_email(data)
    return send_email_resend(ADMIN_EMAIL, subject, html, text)


def create_user_confirmation_email(data):
    """Erstellt eine Bestätigungs-E-Mail für den buchenden Benutzer"""
    teacher = data.get("teacher_name", "Unbekannt")
    teacher_class = data.get("teacher_class", "")
    date = data.get("date", "")
    weekday = data.get("weekday", "")
    period = data.get("period", "")
    offer = data.get("offer_label", "")
    offer_type = data.get("offer_type", "")

    students_json = data.get("students_json", "[]")
    students = json.loads(students_json) if isinstance(students_json, str) else students_json
    count = len(students)

    students_html = "<br>".join(
        [f"• {s['name']} (Klasse {s['klasse']})" for s in students]
    ) if students else "Keine Schüler"

    subject = f"Buchungsbestätigung: {offer} am {date}"

    html = f"""
    <html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="background: linear-gradient(135deg, #E91E63 0%, #C2185B 100%); color: white; padding: 15px 20px; border-radius: 8px; margin: 0 0 20px 0;">
                Buchungsbestätigung – SportOase
            </h2>
            <div style="background: #E8F5E9; border: 1px solid #4CAF50; color: #2E7D32; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                <strong>Ihre Buchung wurde erfolgreich gespeichert!</strong>
            </div>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                <p style="margin: 10px 0; padding: 12px; background: white; border-radius: 4px; border-left: 4px solid #E91E63;">
                    <strong style="color: #E91E63;">Lehrkraft:</strong> {teacher} {f"({teacher_class})" if teacher_class else ""}
                </p>
                <p style="margin: 10px 0; padding: 12px; background: white; border-radius: 4px; border-left: 4px solid #E91E63;">
                    <strong style="color: #E91E63;">Datum:</strong> {date} ({weekday})
                </p>
                <p style="margin: 10px 0; padding: 12px; background: white; border-radius: 4px; border-left: 4px solid #E91E63;">
                    <strong style="color: #E91E63;">Stunde:</strong> {period}. Stunde
                </p>
                <p style="margin: 10px 0; padding: 12px; background: white; border-radius: 4px; border-left: 4px solid #E91E63;">
                    <strong style="color: #E91E63;">Angebot:</strong> {offer} – <span style="background: #E91E63; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{offer_type.upper()}</span>
                </p>
                <div style="margin: 15px 0; padding: 15px; background: white; border-radius: 4px;">
                    <strong style="color: #E91E63;">Angemeldete Schüler ({count}):</strong>
                    <div style="margin-top: 10px; margin-left: 10px;">
                        {students_html}
                    </div>
                </div>
            </div>
            <p style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 12px;">
                Bei Fragen wenden Sie sich bitte an: morelli.maurizio@kgs-pattensen.de<br>
                SportOase – Ernst-Reuter-Schule Pattensen
            </p>
        </div>
    </body></html>
    """

    text = f"""
Buchungsbestätigung – SportOase

Ihre Buchung wurde erfolgreich gespeichert!

Lehrkraft: {teacher} {f"({teacher_class})" if teacher_class else ""}
Datum: {date} ({weekday})
Stunde: {period}. Stunde
Angebot: {offer} ({offer_type})

Angemeldete Schüler ({count}):
{", ".join([f"{s['name']} ({s['klasse']})" for s in students])}

---
Bei Fragen wenden Sie sich bitte an: morelli.maurizio@kgs-pattensen.de
SportOase – Ernst-Reuter-Schule Pattensen
    """

    return subject, html, text


def send_user_booking_confirmation(email, data):
    """Sendet Buchungsbestätigung an den buchenden Benutzer"""
    subject, html, text = create_user_confirmation_email(data)
    return send_email_resend(email, subject, html, text)
