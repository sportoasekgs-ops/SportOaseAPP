#!/usr/bin/env python3
"""
Test-Script für E-Mail-Versand via SMTP
Testet, ob Buchungsbenachrichtigungen an sportoase.kgs@gmail.com funktionieren
"""

import os
import sys

# Füge aktuelles Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from email_service import send_booking_notification

def test_email_sending():
    """Testet den E-Mail-Versand mit einem Beispiel-Buchung"""
    
    print("=" * 60)
    print("TEST: E-Mail-Versand für Buchungsbenachrichtigungen")
    print("=" * 60)
    
    # Prüfe SMTP-Konfiguration
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    
    print(f"\n✓ SMTP_USER: {smtp_user if smtp_user else '❌ NICHT GESETZT'}")
    print(f"✓ SMTP_PASS: {'✓ Gesetzt' if smtp_pass else '❌ NICHT GESETZT'}")
    
    if not smtp_user or not smtp_pass:
        print("\n❌ FEHLER: SMTP-Zugangsdaten sind nicht konfiguriert!")
        print("Bitte setzen Sie SMTP_USER und SMTP_PASS in den Replit Secrets.")
        return False
    
    # Test-Buchungsdaten
    booking_data = {
        'teacher_name': 'Max Mustermann',
        'teacher_class': '5A',
        'date': '2025-11-18',
        'weekday': 'Montag',
        'period': 3,
        'offer_label': 'Konflikt-Reset & Deeskalation',
        'offer_type': 'fest',
        'students_json': '[{"name": "Anna Schmidt", "klasse": "5A"}, {"name": "Tom Weber", "klasse": "5B"}]'
    }
    
    admin_email = 'sportoase.kgs@gmail.com'
    
    print(f"\n📧 Sende Test-E-Mail an: {admin_email}")
    print(f"   Lehrkraft: {booking_data['teacher_name']}")
    print(f"   Datum: {booking_data['date']} ({booking_data['weekday']})")
    print(f"   Stunde: {booking_data['period']}. Stunde")
    print(f"   Angebot: {booking_data['offer_label']}")
    
    # E-Mail senden
    success = send_booking_notification(booking_data, admin_email)
    
    if success:
        print("\n✅ E-Mail wurde erfolgreich versendet!")
        print(f"✅ Überprüfen Sie das Postfach: {admin_email}")
        return True
    else:
        print("\n❌ E-Mail-Versand fehlgeschlagen!")
        print("Überprüfen Sie die Logs für Details.")
        return False

if __name__ == '__main__':
    test_email_sending()
