# Konfigurationsdatei für die SportOase-Anwendung
# Diese Datei enthält alle wichtigen Einstellungen wie Stundenpläne und Zeitangaben

import os
from dotenv import load_dotenv

# .env laden
load_dotenv()

# =====================================================================
#  Stundenzeiten
# =====================================================================

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

# =====================================================================
#  Feste Angebote pro Wochentag
# =====================================================================

FIXED_OFFERS = {
    "Mon": {
        1: "Wochenstart-Aktivierung",
        3: "Konflikt-Reset & Deeskalation",
        5: "Koordinationszirkel"
    },
    "Tue": {},
    "Wed": {
        1: "Sozialtraining / Gruppenreset",
        3: "Aktivierung Mini-Fitness",
        5: "Motorik-Parcours"
    },
    "Thu": {
        2: "Konflikt-Reset",
        5: "Turnen + Balance"
    },
    "Fri": {
        2: "Atem & Reflexion",
        4: "Bodyscan Light",
        5: "Ruhezone / Entspannung"
    }
}

# =====================================================================
#  Frei wählbare Module
# =====================================================================

FREE_MODULES = [
    "Aktivierung", "Regulation / Entspannung", "Konflikt-Reset",
    "Egal / flexibel"
]

# =====================================================================
#  Klassenliste
# =====================================================================

SCHOOL_CLASSES = [
    "5a", "5b", "5c", "5d", "5e", "5f", "6a (KES)", "6b (KES)", "6c (KES)",
    "6d (KES)", "6e (KES)", "6f (KES)", "7a (KES)", "7b (KES)", "7c (KES)",
    "7d (KES)", "7e (KES)", "7f (KES)", "G8G1", "G8G2", "G8G3", "H8H", "R8R1",
    "R8R2", "G9G1", "G9G2", "G9G3", "H9H", "R9R1", "R9R2", "R9R3", "G10G1",
    "G10G2", "G10G3", "H10H", "R10R1", "R10R2", "G11a", "G11b", "G11c",
    "G12Q1", "G13Q2"
]

# =====================================================================
#  Limitierungen / Regeln
# =====================================================================

MAX_STUDENTS_PER_PERIOD = 5
BOOKING_ADVANCE_MINUTES = 60

# =====================================================================
#  SMTP / Mail – ISERV-KOMPATIBEL
# =====================================================================

# Bei IServ gilt IMMER:
# - Port 465
# - SMTP_SSL (kein STARTTLS auf Port 587)

SMTP_HOST = os.getenv("SMTP_HOST", "")  # z.B. "smtp.kgs-pattensen.de"
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))  # IMMER 465 für IServ
SMTP_USER = os.getenv("SMTP_USER", "")  # vollständige IServ-Mailadresse
SMTP_PASS = os.getenv("SMTP_PASS", "")  # das IServ-Passwort
SMTP_FROM = os.getenv("SMTP_FROM",
                      SMTP_USER)  # sinnvollerweise = IServ-Adresse
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", SMTP_USER)  # Fallback: gleiche Adresse

# =====================================================================
#  Flask Session Key
# =====================================================================

SECRET_KEY = os.getenv("SESSION_SECRET", "dev-secret-key-change-in-production")

# =====================================================================
#  Datenbank
# =====================================================================

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/sportoase")
