#!/usr/bin/env python3
"""
Migrations-Script: Fügt calendar_event_id Spalte zur bookings Tabelle hinzu

Dieses Script erweitert die bookings Tabelle um die calendar_event_id Spalte,
die für die Google Calendar Integration benötigt wird.
"""

import os
import psycopg2
from urllib.parse import urlparse

def add_calendar_event_id_column():
    """Fügt die calendar_event_id Spalte zur bookings Tabelle hinzu"""
    
    # Hole DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("FEHLER: DATABASE_URL Umgebungsvariable nicht gesetzt!")
        return False
    
    try:
        # Verbinde zur Datenbank
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("Verbunden mit der Datenbank...")
        
        # Prüfe ob Spalte bereits existiert
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='bookings' AND column_name='calendar_event_id';
        """)
        
        if cursor.fetchone():
            print("✓ Spalte 'calendar_event_id' existiert bereits - keine Migration nötig")
            cursor.close()
            conn.close()
            return True
        
        # Füge Spalte hinzu
        print("Füge Spalte 'calendar_event_id' zur Tabelle 'bookings' hinzu...")
        cursor.execute("""
            ALTER TABLE bookings 
            ADD COLUMN calendar_event_id VARCHAR(200);
        """)
        
        conn.commit()
        print("✓ Migration erfolgreich abgeschlossen!")
        print("  - Spalte 'calendar_event_id' wurde zur Tabelle 'bookings' hinzugefügt")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"FEHLER bei der Migration: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("SportOase - Datenbank Migration")
    print("Fügt calendar_event_id Spalte hinzu")
    print("=" * 60)
    print()
    
    success = add_calendar_event_id_column()
    
    print()
    if success:
        print("✓ Migration erfolgreich abgeschlossen!")
    else:
        print("✗ Migration fehlgeschlagen - bitte Fehler überprüfen")
    print("=" * 60)
