import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, ADMIN_EMAIL


def send_email_smtp(to_email, subject, body_html, body_text=None):
    """Sendet E-Mail über SMTP"""
    try:
        if not SMTP_USER or not SMTP_PASS:
            print(f"WARNUNG: SMTP nicht konfiguriert - E-Mail an {to_email} wird nicht gesendet")
            print(f"Betreff: {subject}")
            print(f"Body: {body_text or body_html[:200]}")
            return False
        
        message = MIMEMultipart('alternative')
        message['From'] = SMTP_FROM
        message['To'] = to_email
        message['Subject'] = subject
        
        if body_text:
            part1 = MIMEText(body_text, 'plain', 'utf-8')
            message.attach(part1)
        
        part2 = MIMEText(body_html, 'html', 'utf-8')
        message.attach(part2)
        
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(message)
        server.quit()
        
        print(f"E-Mail erfolgreich gesendet an {to_email}")
        return True
        
    except Exception as e:
        print(f"FEHLER beim E-Mail-Versand an {to_email}: {e}")
        return False


def create_booking_notification_email(booking_data):
    """Erstellt eine formatierte E-Mail für Buchungsbenachrichtigungen"""
    teacher_name = booking_data.get('teacher_name', 'Unbekannt')
    teacher_class = booking_data.get('teacher_class', '')
    date = booking_data.get('date', '')
    weekday = booking_data.get('weekday', '')
    period = booking_data.get('period', '')
    offer_label = booking_data.get('offer_label', '')
    offer_type = booking_data.get('offer_type', '')
    
    students = []
    try:
        students_json = booking_data.get('students_json', '[]')
        if isinstance(students_json, str):
            students = json.loads(students_json)
        else:
            students = students_json
    except:
        students = []
    
    students_count = len(students)
    
    if students:
        students_names = ', '.join([f"{s['name']} ({s['klasse']})" for s in students])
        students_list_html = '<br>'.join([f"• {s['name']} (Klasse {s['klasse']})" for s in students])
    else:
        students_names = 'Keine Schüler angegeben'
        students_list_html = 'Keine Schüler angegeben'
    
    subject = f"📅 SportOase Buchung: {offer_label} am {date}"
    
    body_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #38bdf8 0%, #3b82f6 100%); 
                       color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center; }}
            .header h2 {{ margin: 0; }}
            .content {{ background: #f8f9fa; padding: 20px; border-radius: 8px; }}
            .info-row {{ margin: 10px 0; padding: 12px; background: white; border-radius: 4px; border-left: 4px solid #38bdf8; }}
            .label {{ font-weight: bold; color: #38bdf8; }}
            .students-section {{ margin-top: 15px; padding: 15px; background: white; border-radius: 4px; }}
            .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; 
                      text-align: center; color: #666; font-size: 12px; }}
            .badge {{ background: #38bdf8; color: white; padding: 4px 10px; 
                     border-radius: 12px; font-size: 11px; margin-left: 8px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🏫 SportOase - Neue Buchung</h2>
            </div>
            <div class="content">
                <div class="info-row">
                    <span class="label">👤 Lehrkraft:</span> {teacher_name}
                    {f' (Klasse {teacher_class})' if teacher_class else ''}
                </div>
                <div class="info-row">
                    <span class="label">📅 Datum:</span> {date} ({weekday})
                </div>
                <div class="info-row">
                    <span class="label">🕐 Stunde:</span> {period}. Stunde
                </div>
                <div class="info-row">
                    <span class="label">📋 Angebot:</span> {offer_label}
                    <span class="badge">{offer_type.upper()}</span>
                </div>
                <div class="students-section">
                    <div><span class="label">👥 Schüler ({students_count}):</span></div>
                    <div style="margin-top: 10px; margin-left: 10px;">
                        {students_list_html}
                    </div>
                </div>
            </div>
            <div class="footer">
                <p>Diese Nachricht wurde automatisch vom SportOase Buchungssystem generiert.</p>
                <p>Zeit: {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    body_text = f"""
SportOase - Neue Buchung

Lehrkraft: {teacher_name} {f'(Klasse {teacher_class})' if teacher_class else ''}
Datum: {date} ({weekday})
Stunde: {period}. Stunde
Angebot: {offer_label} ({offer_type.upper()})

Schüler ({students_count}):
{students_names}

Zeit: {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}

---
Diese Nachricht wurde automatisch vom SportOase Buchungssystem generiert.
    """
    
    return subject, body_html, body_text


def send_booking_notification(booking_data, admin_email=None):
    """Sendet Buchungsbenachrichtigung an Admin"""
    try:
        if not admin_email:
            admin_email = ADMIN_EMAIL
        
        subject, body_html, body_text = create_booking_notification_email(booking_data)
        return send_email_smtp(admin_email, subject, body_html, body_text)
        
    except Exception as e:
        print(f"Fehler beim Senden der Buchungsbenachrichtigung: {e}")
        return False
