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

# Maximale Anzahl Schüler pro Stunde
MAX_STUDENTS_PER_PERIOD = 5

# Vorlaufzeit für Buchungen in Minuten
BOOKING_ADVANCE_MINUTES = 60

# SMTP-Konfiguration (aus Umgebungsvariablen)
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', 'sportoase.kgs@gmail.com')
SMTP_PASS = os.environ.get('SMTP_PASS', 'Unhack85!$')
SMTP_FROM = os.environ.get('SMTP_FROM', 'sportoase.kgs@gmail.com')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'sportoase.kgs@gmail.com')

# Flask Session Secret (aus Umgebungsvariable)
SECRET_KEY = os.environ.get('SESSION_SECRET',
                            'dev-secret-key-change-in-production')

# Datenbank-Konfiguration (PostgreSQL)
DATABASE_URL = os.environ.get('DATABASE_URL',
                              'postgresql://localhost/sportoase')
