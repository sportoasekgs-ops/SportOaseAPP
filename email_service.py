import os
import json
import logging
from datetime import datetime

import resend

from config import ADMIN_EMAIL


def format_date_german(date_str):
    """Konvertiert YYYY-MM-DD zu TT.MM.JJJJ"""
    try:
        if '-' in str(date_str):
            parts = str(date_str).split('-')
            if len(parts) == 3:
                return f"{parts[2]}.{parts[1]}.{parts[0]}"
    except:
        pass
    return str(date_str)


def get_german_weekday(weekday_abbr):
    """Konvertiert englische Wochentag-Abkürzung zu deutschem Namen"""
    weekday_map = {
        'Mon': 'Montag',
        'Tue': 'Dienstag',
        'Wed': 'Mittwoch',
        'Thu': 'Donnerstag',
        'Fri': 'Freitag',
        'Sat': 'Samstag',
        'Sun': 'Sonntag'
    }
    return weekday_map.get(weekday_abbr, weekday_abbr)


def get_resend_credentials():
    """Holt Resend API-Key - zuerst aus ENV, dann über Replit Connector"""

    # 1. Prüfe direkte Environment Variable (für Render)
    env_api_key = os.environ.get('RESEND_API_KEY')
    env_from_email = os.environ.get('RESEND_FROM_EMAIL',
                                    'SportOase <mauro@sportoase.app>')

    if env_api_key:
        print(f"[EMAIL] Resend API-Key aus Environment Variable gefunden")
        return env_api_key, env_from_email

    # 2. Versuche Replit Connector (für Replit)
    hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')

    x_replit_token = None
    if os.environ.get('REPL_IDENTITY'):
        x_replit_token = 'repl ' + os.environ.get('REPL_IDENTITY')
    elif os.environ.get('WEB_REPL_RENEWAL'):
        x_replit_token = 'depl ' + os.environ.get('WEB_REPL_RENEWAL')

    if not x_replit_token or not hostname:
        print("[EMAIL] Weder ENV noch Replit Connector verfügbar")
        return None, None

    try:
        import requests
        response = requests.get(
            f'https://{hostname}/api/v2/connection?include_secrets=true&connector_names=resend',
            headers={
                'Accept': 'application/json',
                'X_REPLIT_TOKEN': x_replit_token
            },
            timeout=10)
        data = response.json()
        connection = data.get('items', [{}])[0] if data.get('items') else {}
        settings = connection.get('settings', {})

        api_key = settings.get('api_key')
        from_email = settings.get('from_email')

        if api_key:
            print(f"[EMAIL] Resend API-Key über Replit Connector gefunden")
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
            print(
                f"[EMAIL] WARNUNG: Resend nicht konfiguriert - E-Mail an {to_email} nicht gesendet"
            )
            return False

        resend.api_key = api_key

        # Verwende immer die Resend Test-Adresse (keine Domain-Verifizierung nötig)
        from_address = "SportOase <mauro@sportoase.app>"

        params = {
            "from": from_address,
            "to": [to_email],
            "subject": subject,
            "html": body_html,
        }

        if body_text:
            params["text"] = body_text

        print(f"[EMAIL] Sende von {from_address} an {to_email}...")
        result = resend.Emails.send(params)

        print(
            f"[EMAIL] Erfolgreich gesendet an {to_email} (ID: {result.get('id', 'unknown')})"
        )
        return True

    except Exception as e:
        print(f"[EMAIL] FEHLER beim E-Mail-Versand an {to_email}: {e}")
        return False


def create_booking_notification_email(data):
    """Erstellt eine formatierte E-Mail für Buchungsbenachrichtigungen"""
    teacher = data.get("teacher_name", "Unbekannt")
    teacher_class = data.get("teacher_class", "")
    date_raw = data.get("date", "")
    date = format_date_german(date_raw)
    weekday_raw = data.get("weekday", "")
    weekday = get_german_weekday(weekday_raw)
    period = data.get("period", "")
    offer = data.get("offer_label", "")
    offer_type = data.get("offer_type", "")

    students_json = data.get("students_json", "[]")
    students = json.loads(students_json) if isinstance(students_json,
                                                       str) else students_json
    count = len(students)

    students_html = "<br>".join(
        [f"• {s['name']} (Klasse {s['klasse']})"
         for s in students]) if students else "Keine Schüler"

    students_list = ", ".join(
        [f"{s['name']} ({s['klasse']})"
         for s in students]) if students else "Keine Schüler"

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
    date_raw = data.get("date", "")
    date = format_date_german(date_raw)
    weekday_raw = data.get("weekday", "")
    weekday = get_german_weekday(weekday_raw)
    period = data.get("period", "")
    offer = data.get("offer_label", "")
    offer_type = data.get("offer_type", "")

    students_json = data.get("students_json", "[]")
    students = json.loads(students_json) if isinstance(students_json,
                                                       str) else students_json
    count = len(students)

    students_html = "<br>".join(
        [f"• {s['name']} (Klasse {s['klasse']})"
         for s in students]) if students else "Keine Schüler"

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


def send_exclusive_approved_email(teacher_email, teacher_name, student_name,
                                  date_str, period):
    """Sendet Bestätigungs-E-Mail wenn eine exklusive Buchung genehmigt wurde"""
    from config import PERIOD_TIMES

    period_time = PERIOD_TIMES.get(period, "")
    date_formatted = format_date_german(date_str)

    subject = f"✅ Exklusive Buchung genehmigt – SportOase"

    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #E91E63; margin: 0;">🎉 Exklusive Buchung genehmigt!</h2>
        </div>
        <div style="background: #d4edda; border-radius: 8px; padding: 20px; border-left: 4px solid #28a745;">
            <p>Hallo <strong>{teacher_name}</strong>,</p>
            <p>Ihre exklusive Buchung wurde <strong>von Mauro genehmigt</strong>.</p>
            <p>Der gesamte Slot ist jetzt für Ihren Schüler reserviert:</p>
            <ul style="list-style: none; padding: 0;">
                <li>📅 <strong>Datum:</strong> {date_formatted}</li>
                <li>⏰ <strong>Stunde:</strong> {period}. Stunde ({period_time})</li>
                <li>👤 <strong>Schüler:</strong> {student_name}</li>
            </ul>
            <p style="color: #155724; font-weight: bold;">
                Der Slot ist jetzt vollständig für Ihren Schüler reserviert.
            </p>
        </div>
        <p style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 12px;">
            Bei Fragen wenden Sie sich bitte an: morelli.maurizio@kgs-pattensen.de<br>
            SportOase – Ernst-Reuter-Schule Pattensen
        </p>
    </body></html>
    """

    text = f"""
Exklusive Buchung genehmigt – SportOase

Hallo {teacher_name},

Ihre exklusive Buchung wurde von Mauro genehmigt.

Datum: {date_formatted}
Stunde: {period}. Stunde ({period_time})
Schüler: {student_name}

Der Slot ist jetzt vollständig für Ihren Schüler reserviert.

---
Bei Fragen wenden Sie sich bitte an: morelli.maurizio@kgs-pattensen.de
SportOase – Ernst-Reuter-Schule Pattensen
    """

    return send_email_resend(teacher_email, subject, html, text)


def send_exclusive_rejected_email(teacher_email, teacher_name, student_name,
                                  date_str, period, rejection_reason=None):
    """Sendet Ablehnungs-E-Mail wenn eine exklusive Buchung abgelehnt wurde"""
    from config import PERIOD_TIMES

    period_time = PERIOD_TIMES.get(period, "")
    date_formatted = format_date_german(date_str)
    
    reason_html = ""
    reason_text = ""
    if rejection_reason:
        reason_html = f"""
            <div style="background: #fff3cd; border-radius: 6px; padding: 12px; margin: 15px 0; border-left: 4px solid #ffc107;">
                <strong>Begründung von Mauro:</strong><br>
                {rejection_reason}
            </div>
        """
        reason_text = f"\nBegründung von Mauro:\n{rejection_reason}\n"

    subject = f"❌ Exklusive Buchung abgelehnt – SportOase"

    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #E91E63; margin: 0;">Exklusive Buchung abgelehnt</h2>
        </div>
        <div style="background: #f8d7da; border-radius: 8px; padding: 20px; border-left: 4px solid #dc3545;">
            <p>Hallo <strong>{teacher_name}</strong>,</p>
            <p>Leider wurde Ihre exklusive Buchung <strong>von Mauro abgelehnt</strong>:</p>
            <ul style="list-style: none; padding: 0;">
                <li>📅 <strong>Datum:</strong> {date_formatted}</li>
                <li>⏰ <strong>Stunde:</strong> {period}. Stunde ({period_time})</li>
                <li>👤 <strong>Schüler:</strong> {student_name}</li>
            </ul>
            {reason_html}
            <p style="color: #721c24;">
                Die Buchung wurde storniert. Sie können den Schüler gerne regulär (ohne exklusive Reservierung) anmelden, falls Plätze verfügbar sind.
            </p>
            <p>
                Bei Fragen oder Rückfragen wenden Sie sich bitte direkt an Mauro.
            </p>
        </div>
        <p style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 12px;">
            Bei Fragen wenden Sie sich bitte an: morelli.maurizio@kgs-pattensen.de<br>
            SportOase – Ernst-Reuter-Schule Pattensen
        </p>
    </body></html>
    """

    text = f"""
Exklusive Buchung abgelehnt – SportOase

Hallo {teacher_name},

Leider wurde Ihre exklusive Buchung von Mauro abgelehnt:

Datum: {date_formatted}
Stunde: {period}. Stunde ({period_time})
Schüler: {student_name}
{reason_text}
Die Buchung wurde storniert. Sie können den Schüler gerne regulär (ohne exklusive Reservierung) anmelden, falls Plätze verfügbar sind.

Bei Fragen oder Rückfragen wenden Sie sich bitte direkt an Mauro.

---
Bei Fragen wenden Sie sich bitte an: morelli.maurizio@kgs-pattensen.de
SportOase – Ernst-Reuter-Schule Pattensen
    """

    return send_email_resend(teacher_email, subject, html, text)
