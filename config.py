import os
from dotenv import load_dotenv

# .env Datei laden
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
    },
}

# =====================================================================
#  Feste Angebote
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
    },
}

# =====================================================================
#  Angebotsbeschreibungen
# =====================================================================

OFFER_DESCRIPTIONS = {
    "Wochenstart-Aktivierung": {
        "title": "WOCHENSTART-AKTIV",
        "description": "Aktiver Start in die Woche mit Bewegungs- und Energieübungen, um wach und motiviert in den Montag zu gehen.",
        "icon": "☀️"
    },
    "Freie Wahl": {
        "title": "FREIE WAHL",
        "description": "Offene Stunde: Die Lehrkräfte wählen selbst eine passende Beschäftigung – Rückzug, Spielen, kreative Angebote oder ruhige Aufgaben.",
        "icon": "⭐"
    },
    "Sozialtraining / Gruppenreset": {
        "title": "SOZIALTRAINING / GRUPPENRESET",
        "description": "Gemeinsame Übungen für Teamfähigkeit, Rücksichtnahme und ein positives Miteinander. Stärkt Klassenklima und soziale Kompetenzen.",
        "icon": "👥"
    },
    "Konflikt-Reset & Deeskalation": {
        "title": "KONFLIKT-RESET & DEESKALATION",
        "description": "Training für Selbstkontrolle und Konfliktlösung mit kontrollierten Box-Übungen zum Stressabbau. Danach ruhige Reflexion und Deeskalationsstrategien.",
        "icon": "🥊"
    },
    "Konflikt-Reset": {
        "title": "KONFLIKT-RESET",
        "description": "Kurze Einheit zur Beruhigung: Box-Übungen zur Energieableitung, anschließend Techniken für Ruhe, Klarheit und Selbstbeherrschung.",
        "icon": "🛡️"
    },
    "Atem & Reflexion": {
        "title": "ATEM & REFLEXION",
        "description": "Ruhige Atemübungen und kurze Reflexionsphasen zur Stressreduktion, Selbstwahrnehmung und inneren Balance.",
        "icon": "🌬️"
    },
    "Aktivierung Mini-Fitness": {
        "title": "AKTIVIERUNG MINI-FITNESS",
        "description": "Kurze Fitness- und Bewegungsübungen, um den Kreislauf anzuregen, überschüssige Energie abzubauen und Konzentration zu stärken.",
        "icon": "⚡"
    },
    "Koordinationszirkel": {
        "title": "KOORDINATIONSZIRKEL",
        "description": "Übungen an verschiedenen Stationen für Gleichgewicht, Feinmotorik, Körperkontrolle und Konzentration.",
        "icon": "🎯"
    },
    "Motorik-Parcours": {
        "title": "MOTORIK-PARCOURS",
        "description": "Bewegungsparcours mit Balancieren, Springen und Klettern – fördert Koordination, Mut, Kraft und Motorik.",
        "icon": "🏃"
    },
    "Turnen + Balance": {
        "title": "TURNEN + BALANCE",
        "description": "Turn- und Balanceübungen zur Förderung von Körpergefühl, Stabilität und Gleichgewicht.",
        "icon": "🤸"
    },
    "Ruhezone / Entspannung": {
        "title": "RUHEZONE / ENTSPANNUNG",
        "description": "Sanfte Entspannungsangebote wie leise Spiele, Ruheübungen oder geführte Entspannung – ideal zum Runterkommen.",
        "icon": "🍃"
    },
    "Bodyscan Light": {
        "title": "BODYSCAN LIGHT",
        "description": "Geführte, leichte Körperwahrnehmungsübung zur Entspannung. Hilft Stress abzubauen und Ruhe zu finden.",
        "icon": "🧘"
    },
}

# =====================================================================
#  Module
# =====================================================================

FREE_MODULES = [
    "Aktivierung",
    "Regulation / Entspannung",
    "Konflikt-Reset",
    "Egal / flexibel",
]

# =====================================================================
#  Klassen
# =====================================================================

SCHOOL_CLASSES = [
    "5a",
    "5b",
    "5c",
    "5d",
    "5e",
    "5f",
    "6a (KES)",
    "6b (KES)",
    "6c (KES)",
    "6d (KES)",
    "6e (KES)",
    "6f (KES)",
    "7a (KES)",
    "7b (KES)",
    "7c (KES)",
    "7d (KES)",
    "7e (KES)",
    "7f (KES)",
    "G8G1",
    "G8G2",
    "G8G3",
    "H8H",
    "R8R1",
    "R8R2",
    "G9G1",
    "G9G2",
    "G9G3",
    "H9H",
    "R9R1",
    "R9R2",
    "R9R3",
    "G10G1",
    "G10G2",
    "G10G3",
    "H10H",
    "R10R1",
    "R10R2",
    "G11a",
    "G11b",
    "G11c",
    "G12Q1",
    "G13Q2",
]

# =====================================================================
#  Regeln
# =====================================================================

MAX_STUDENTS_PER_PERIOD = 5
BOOKING_ADVANCE_MINUTES = 60

# =====================================================================
#  SMTP (IServ) — Port 587 + STARTTLS (empfohlen)
# =====================================================================

# !!! Für dich relevant !!!
# Dein SMTP-Server lautet: kgs-pattensen.de

SMTP_HOST = os.getenv("SMTP_HOST", "kgs-pattensen.de")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))  # STARTTLS
SMTP_USER = os.getenv("SMTP_USER", "")  # vollständige IServ-Adresse
SMTP_PASS = os.getenv("SMTP_PASS", "")  # IServ-Login
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", SMTP_USER)

# =====================================================================
#  Flask-Key / DB
# =====================================================================

SECRET_KEY = os.getenv("SESSION_SECRET", "dev-secret-key-change-in-production")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/sportoase")
