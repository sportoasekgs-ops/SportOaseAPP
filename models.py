# Datenbankmodelle für die SportOase-Anwendung
# Diese Datei definiert die Struktur der Datenbank-Tabellen

import sqlite3
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config import DATABASE_PATH

def get_db():
    """Erstellt eine Verbindung zur SQLite-Datenbank"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Ermöglicht Zugriff auf Spalten per Name
    return conn

def init_db():
    """Initialisiert die Datenbank und erstellt alle Tabellen"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabelle für Benutzer (Lehrkräfte und Admins)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('teacher', 'admin'))
        )
    ''')
    
    # Tabelle für Buchungen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            weekday TEXT NOT NULL,
            period INTEGER NOT NULL CHECK(period >= 1 AND period <= 6),
            teacher_id INTEGER NOT NULL,
            teacher_name TEXT,
            teacher_class TEXT,
            students_json TEXT NOT NULL,
            offer_type TEXT NOT NULL CHECK(offer_type IN ('fest', 'frei')),
            offer_label TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (teacher_id) REFERENCES users(id)
        )
    ''')
    
    # Migriere bestehende Tabelle falls nötig (füge neue Spalten hinzu)
    try:
        cursor.execute("ALTER TABLE bookings ADD COLUMN teacher_name TEXT")
    except sqlite3.OperationalError:
        pass  # Spalte existiert bereits
    
    try:
        cursor.execute("ALTER TABLE bookings ADD COLUMN teacher_class TEXT")
    except sqlite3.OperationalError:
        pass  # Spalte existiert bereits
    
    conn.commit()
    conn.close()
    print("Datenbank erfolgreich initialisiert!")

# Funktionen für Benutzer-Verwaltung
def create_user(email, password, role):
    """Erstellt einen neuen Benutzer in der Datenbank"""
    conn = get_db()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    
    try:
        cursor.execute(
            'INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)',
            (email, password_hash, role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None  # E-Mail existiert bereits

def get_user_by_email(email):
    """Sucht einen Benutzer anhand der E-Mail-Adresse"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    """Sucht einen Benutzer anhand der ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def verify_password(user, password):
    """Überprüft, ob das eingegebene Passwort korrekt ist"""
    return check_password_hash(user['password_hash'], password)

def get_all_users():
    """Gibt alle Benutzer zurück (für Admin-Ansicht)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, email, role FROM users ORDER BY role, email')
    users = cursor.fetchall()
    conn.close()
    return users

# Funktionen für Buchungs-Verwaltung
def create_booking(date, weekday, period, teacher_id, students, offer_type, offer_label, teacher_name=None, teacher_class=None):
    """Erstellt eine neue Buchung in der Datenbank"""
    conn = get_db()
    cursor = conn.cursor()
    
    students_json = json.dumps(students, ensure_ascii=False)
    created_at = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO bookings (date, weekday, period, teacher_id, teacher_name, teacher_class, students_json, offer_type, offer_label, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (date, weekday, period, teacher_id, teacher_name, teacher_class, students_json, offer_type, offer_label, created_at))
    
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    return booking_id

def get_bookings_for_date_period(date, period):
    """Gibt alle Buchungen für ein bestimmtes Datum und Stunde zurück"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM bookings 
        WHERE date = ? AND period = ?
        ORDER BY created_at
    ''', (date, period))
    bookings = cursor.fetchall()
    conn.close()
    return bookings

def count_students_for_period(date, period):
    """Zählt die Gesamtzahl der Schüler für eine bestimmte Stunde"""
    bookings = get_bookings_for_date_period(date, period)
    total = 0
    for booking in bookings:
        students = json.loads(booking['students_json'])
        total += len(students)
    return total

def get_all_bookings():
    """Gibt alle Buchungen zurück (für Admin-Ansicht)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, u.email as teacher_email 
        FROM bookings b
        JOIN users u ON b.teacher_id = u.id
        ORDER BY b.date DESC, b.period
    ''')
    bookings = cursor.fetchall()
    conn.close()
    return bookings

def get_bookings_by_date(date):
    """Gibt alle Buchungen für ein bestimmtes Datum zurück"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, u.email as teacher_email 
        FROM bookings b
        JOIN users u ON b.teacher_id = u.id
        WHERE b.date = ?
        ORDER BY b.period
    ''', (date,))
    bookings = cursor.fetchall()
    conn.close()
    return bookings

def get_bookings_for_week(start_date, end_date):
    """Gibt alle Buchungen für eine Woche zurück"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, u.email as teacher_email 
        FROM bookings b
        JOIN users u ON b.teacher_id = u.id
        WHERE b.date >= ? AND b.date <= ?
        ORDER BY b.date, b.period
    ''', (start_date, end_date))
    bookings = cursor.fetchall()
    conn.close()
    return bookings

def get_booking_by_id(booking_id):
    """Gibt eine einzelne Buchung anhand der ID zurück"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, u.email as teacher_email 
        FROM bookings b
        JOIN users u ON b.teacher_id = u.id
        WHERE b.id = ?
    ''', (booking_id,))
    booking = cursor.fetchone()
    conn.close()
    return booking

def update_booking(booking_id, date, weekday, period, teacher_id, students, offer_type, offer_label, teacher_name=None, teacher_class=None):
    """Aktualisiert eine bestehende Buchung in der Datenbank"""
    conn = get_db()
    cursor = conn.cursor()
    
    students_json = json.dumps(students, ensure_ascii=False)
    
    cursor.execute('''
        UPDATE bookings 
        SET date = ?, weekday = ?, period = ?, teacher_id = ?, teacher_name = ?, teacher_class = ?, 
            students_json = ?, offer_type = ?, offer_label = ?
        WHERE id = ?
    ''', (date, weekday, period, teacher_id, teacher_name, teacher_class, students_json, offer_type, offer_label, booking_id))
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def delete_booking(booking_id):
    """Löscht eine Buchung aus der Datenbank"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0
