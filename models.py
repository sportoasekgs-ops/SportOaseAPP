# Datenbankmodelle für die SportOase-Anwendung mit Flask-SQLAlchemy
# Diese Datei definiert die Struktur der Datenbank-Tabellen für PostgreSQL

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from database import db

class User(db.Model):
    """Benutzer-Modell für Lehrkräfte und Admins"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120))
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    
    bookings = db.relationship('Booking', backref='teacher', lazy=True)
    
    def set_password(self, password):
        """Setzt das Passwort (gehasht)"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Überprüft das Passwort"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Konvertiert User zu Dictionary für Kompatibilität"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'role': self.role
        }

class Booking(db.Model):
    """Buchungs-Modell"""
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False, index=True)
    weekday = db.Column(db.String(3), nullable=False)
    period = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    teacher_name = db.Column(db.String(100))
    teacher_class = db.Column(db.String(50))
    students_json = db.Column(db.Text, nullable=False)
    offer_type = db.Column(db.String(10), nullable=False)
    offer_label = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        """Konvertiert Booking zu Dictionary für Kompatibilität"""
        return {
            'id': self.id,
            'date': self.date,
            'weekday': self.weekday,
            'period': self.period,
            'teacher_id': self.teacher_id,
            'teacher_name': self.teacher_name,
            'teacher_class': self.teacher_class,
            'students_json': self.students_json,
            'offer_type': self.offer_type,
            'offer_label': self.offer_label,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'teacher_email': self.teacher.email if self.teacher else None
        }

# Hilfsfunktionen für Kompatibilität mit dem alten Code

def create_user(username, password, role, email=None):
    """Erstellt einen neuen Benutzer in der Datenbank"""
    try:
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id
    except Exception as e:
        db.session.rollback()
        print(f"Fehler beim Erstellen des Benutzers: {e}")
        return None

def get_user_by_username(username):
    """Sucht einen Benutzer anhand des Benutzernamens"""
    user = User.query.filter_by(username=username).first()
    return user.to_dict() if user else None

def get_user_by_email(email):
    """Sucht einen Benutzer anhand der E-Mail-Adresse"""
    user = User.query.filter_by(email=email).first()
    return user.to_dict() if user else None

def get_user_by_id(user_id):
    """Sucht einen Benutzer anhand der ID"""
    user = User.query.get(user_id)
    return user.to_dict() if user else None

def verify_password(user_dict, password):
    """Überprüft, ob das eingegebene Passwort korrekt ist"""
    user = User.query.get(user_dict['id'])
    return user.check_password(password) if user else False

def get_all_users():
    """Gibt alle Benutzer zurück (für Admin-Ansicht)"""
    users = User.query.order_by(User.role, User.username).all()
    return [u.to_dict() for u in users]

def create_booking(date, weekday, period, teacher_id, students, offer_type, offer_label, teacher_name=None, teacher_class=None):
    """Erstellt eine neue Buchung in der Datenbank"""
    try:
        students_json = json.dumps(students, ensure_ascii=False)
        booking = Booking(
            date=date,
            weekday=weekday,
            period=period,
            teacher_id=teacher_id,
            teacher_name=teacher_name,
            teacher_class=teacher_class,
            students_json=students_json,
            offer_type=offer_type,
            offer_label=offer_label,
            created_at=datetime.now()
        )
        db.session.add(booking)
        db.session.commit()
        return booking.id
    except Exception as e:
        db.session.rollback()
        print(f"Fehler beim Erstellen der Buchung: {e}")
        return None

def get_bookings_for_date_period(date, period):
    """Gibt alle Buchungen für ein bestimmtes Datum und Stunde zurück"""
    bookings = Booking.query.filter_by(date=date, period=period).order_by(Booking.created_at).all()
    return [b.to_dict() for b in bookings]

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
    bookings = Booking.query.order_by(Booking.date.desc(), Booking.period).all()
    return [b.to_dict() for b in bookings]

def get_bookings_by_date(date):
    """Gibt alle Buchungen für ein bestimmtes Datum zurück"""
    bookings = Booking.query.filter_by(date=date).order_by(Booking.period).all()
    return [b.to_dict() for b in bookings]

def get_bookings_for_week(start_date, end_date):
    """Gibt alle Buchungen für eine Woche zurück"""
    bookings = Booking.query.filter(Booking.date >= start_date, Booking.date <= end_date).order_by(Booking.date, Booking.period).all()
    return [b.to_dict() for b in bookings]

def get_booking_by_id(booking_id):
    """Gibt eine einzelne Buchung anhand der ID zurück"""
    booking = Booking.query.get(booking_id)
    return booking.to_dict() if booking else None

def update_booking(booking_id, date, weekday, period, teacher_id, students, offer_type, offer_label, teacher_name=None, teacher_class=None):
    """Aktualisiert eine bestehende Buchung in der Datenbank"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return False
        
        booking.date = date
        booking.weekday = weekday
        booking.period = period
        booking.teacher_id = teacher_id
        booking.teacher_name = teacher_name
        booking.teacher_class = teacher_class
        booking.students_json = json.dumps(students, ensure_ascii=False)
        booking.offer_type = offer_type
        booking.offer_label = offer_label
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Fehler beim Aktualisieren der Buchung: {e}")
        return False

def delete_booking(booking_id):
    """Löscht eine Buchung aus der Datenbank"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return False
        
        db.session.delete(booking)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Fehler beim Löschen der Buchung: {e}")
        return False
