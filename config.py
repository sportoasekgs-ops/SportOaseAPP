# Konfigurationsdatei für die SportOase-Anwendung
# Diese Datei enthält alle wichtigen Einstellungen wie Stundenpläne und Zeitangaben

import os

# Zeitplan der Schulstunden (Beginn und Ende jeder Stunde)
# Format: "HH:MM" für Start und Ende
PERIOD_TIMES = {
    1: {
        "start": "07:50",
        "end": "08:35"
    },
    2: {
        "start": "08:35",
        "end": "09:20"
    },
    3: {
        "start": "09:40",
        "end": "10:25"
    },
    4: {
        "start": "10:25",
        "end": "11:20"
    },
    5: {
        "start": "11:40",
        "end": "12:25"
    },
    6: {
        "start": "12:25",
        "end": "13:10"
    }
}

# Feste Angebote pro Wochentag und Stunde
# "Mon" = Montag, "Tue" = Dienstag, etc.
# Wenn eine Stunde hier nicht aufgeführt ist, ist sie FREI (Lehrkraft wählt Modul)
FIXED_OFFERS = {
    "Mon": {  # Montag
        1: "Wochenstart-Aktivierung",
        3: "Konflikt-Reset & Deeskalation",
        5: "Koordinationszirkel"
    },
    "Tue": {  # Dienstag - alle Stunden frei
    },
    "Wed": {  # Mittwoch
        1: "Sozialtraining / Gruppenreset",
        3: "Aktivierung Mini-Fitness",
        5: "Motorik-Parcours"
    },
    "Thu": {  # Donnerstag
        2: "Konflikt-Reset",
        5: "Turnen + Balance"
    },
    "Fri": {  # Freitag
        2: "Atem & Reflexion",
        4: "Bodyscan Light",
        5: "Ruhezone / Entspannung"
    }
}

# Module, die bei freien Stunden wählbar sind
FREE_MODULES = [
    "Aktivierung", "Regulation / Entspannung", "Konflikt-Reset",
    "Egal / flexibel"
]

# Klassenliste für Dropdown-Auswahl (Schuljahr 2025/2026)
SCHOOL_CLASSES = [
    # Jahrgang 5
    "5a", "5b", "5c", "5d", "5e", "5f",
    # Jahrgang 6 (KES)
    "6a (KES)", "6b (KES)", "6c (KES)", "6d (KES)", "6e (KES)", "6f (KES)",
    # Jahrgang 7 (KES)
    "7a (KES)", "7b (KES)", "7c (KES)", "7d (KES)", "7e (KES)", "7f (KES)",
    # Jahrgang 8
    "G8G1", "G8G2", "G8G3", "H8H", "R8R1", "R8R2",
    # Jahrgang 9
    "G9G1", "G9G2", "G9G3", "H9H", "R9R1", "R9R2", "R9R3",
    # Jahrgang 10
    "G10G1", "G10G2", "G10G3", "H10H", "R10R1", "R10R2",
    # Jahrgang 11
    "G11a", "G11b", "G11c",
    # Jahrgang 12/13
    "G12Q1", "G13Q2"
]

# Maximale Anzahl Schüler pro Stunde
MAX_STUDENTS_PER_PERIOD = 5

# Vorlaufzeit für Buchungen in Minuten
BOOKING_ADVANCE_MINUTES = 60

# SMTP-Konfiguration (aus Umgebungsvariablen/Secrets)
# WICHTIG: SMTP_USER und SMTP_PASS müssen als Secrets gesetzt werden!
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')  # Secret erforderlich
SMTP_PASS = os.environ.get('SMTP_PASS', '')  # Secret erforderlich (Gmail App-Passwort!)
SMTP_FROM = os.environ.get('SMTP_FROM', 'sportoase.kgs@gmail.com')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'sportoase.kgs@gmail.com')

# Flask Session Secret (aus Umgebungsvariable)
SECRET_KEY = os.environ.get('SESSION_SECRET',
                            'dev-secret-key-change-in-production')

# Datenbank-Konfiguration (PostgreSQL)
DATABASE_URL = os.environ.get('DATABASE_URL',
                              'postgresql://localhost/sportoase')
