# Haupt-Anwendungsdatei für die SportOase-Buchungssystem
# Diese Datei enthält alle Routen (URLs) und die Logik der Webanwendung

from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta, date
from werkzeug.middleware.proxy_fix import ProxyFix
import pytz
import json
import os

# Flask-App erstellen
app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Datenbank-Konfiguration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Importiere zentrale Datenbank-Instanz
from database import db

# Initialisiere SQLAlchemy mit der App
db.init_app(app)

# Importiere Modelle und Hilfsfunktionen
from models import (
    create_user, get_user_by_username, get_user_by_email, 
    get_user_by_id, verify_password, get_all_users, create_booking,
    get_bookings_for_date_period, count_students_for_period, get_all_bookings,
    get_bookings_by_date, get_bookings_for_week, get_booking_by_id,
    update_booking, delete_booking, User, Booking
)
from config import *
from email_service import send_booking_notification

# Schema-Erstellung erfolgt explizit über db_setup.py
# Nicht automatisch bei jedem Import!

# Hilfsfunktion: Zeitzone Europe/Berlin
def get_berlin_tz():
    """Gibt die Zeitzone Europe/Berlin zurück"""
    return pytz.timezone('Europe/Berlin')

# Hilfsfunktion: Prüft, ob Benutzer eingeloggt ist
def login_required(f):
    """Decorator-Funktion: Schützt Routen, sodass nur eingeloggte Benutzer darauf zugreifen können"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bitte melden Sie sich an.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Hilfsfunktion: Prüft, ob Benutzer Admin ist
def admin_required(f):
    """Decorator-Funktion: Schützt Routen, sodass nur Admins darauf zugreifen können"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bitte melden Sie sich an.', 'error')
            return redirect(url_for('login'))
        user = get_user_by_id(session['user_id'])
        if not user or user['role'] != 'admin':
            flash('Zugriff verweigert. Nur Admins haben Zugriff.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Hilfsfunktion: Gibt Informationen über eine Stunde zurück
def get_period_info(weekday, period):
    """
    Gibt Informationen über eine Stunde zurück (fest/frei, Bezeichnung)
    weekday: z.B. "Mon", "Tue", ...
    period: 1-6
    """
    if weekday in FIXED_OFFERS and period in FIXED_OFFERS[weekday]:
        return {
            'type': 'fest',
            'label': FIXED_OFFERS[weekday][period]
        }
    else:
        return {
            'type': 'frei',
            'label': 'Freie Wahl'
        }

# Hilfsfunktion: Prüft, ob eine Buchung zeitlich möglich ist
def check_booking_time(booking_date, period):
    """
    Prüft, ob die Buchung mindestens 60 Minuten in der Zukunft liegt
    Gibt (True, None) zurück wenn OK, sonst (False, Fehlermeldung)
    """
    berlin_tz = get_berlin_tz()
    now = datetime.now(berlin_tz)
    
    # Erstelle Datetime-Objekt für den Stundenbeginn
    period_start_time = PERIOD_TIMES[period]['start']
    hour, minute = map(int, period_start_time.split(':'))
    
    # Kombiniere Datum und Zeit
    period_datetime = berlin_tz.localize(
        datetime.combine(booking_date, datetime.min.time()).replace(hour=hour, minute=minute)
    )
    
    # Berechne Zeitdifferenz
    time_diff = period_datetime - now
    
    if time_diff.total_seconds() < BOOKING_ADVANCE_MINUTES * 60:
        return False, f"Buchungen sind nur bis {BOOKING_ADVANCE_MINUTES} Minuten vor Stundenbeginn möglich."
    
    return True, None

# Route: Startseite (leitet zum Dashboard weiter)
@app.route('/')
def index():
    """Startseite - leitet zum Dashboard oder Login weiter"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Route: Login-Seite
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login-Seite für Lehrkräfte und Admins"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Suche Benutzer in Datenbank
        user = get_user_by_username(username)
        
        if user and verify_password(user, password):
            # Login erfolgreich - speichere in Session
            session['user_id'] = user['id']
            session['user_username'] = user['username']
            session['user_email'] = user['email'] if user['email'] else ''
            session['user_role'] = user['role']
            flash(f'Willkommen, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Ungültiger Benutzername oder Passwort.', 'error')
    
    return render_template('login.html')

# Route: Logout
@app.route('/logout')
def logout():
    """Meldet den Benutzer ab"""
    session.clear()
    flash('Sie wurden abgemeldet.', 'info')
    return redirect(url_for('login'))

# Route: Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    """Hauptseite - zeigt Wochenplan und Buchungsmöglichkeiten"""
    # Hole aktuelles Datum oder gewähltes Datum
    selected_date_str = request.args.get('date', datetime.now(get_berlin_tz()).strftime('%Y-%m-%d'))
    
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except:
        selected_date = datetime.now(get_berlin_tz()).date()
    
    # Wochentag ermitteln (Mon, Tue, ...)
    weekday = selected_date.strftime('%a')
    weekday_name = selected_date.strftime('%A')  # Ausgeschriebener Name
    
    # Deutsche Wochentagsnamen
    weekday_names_de = {
        'Monday': 'Montag',
        'Tuesday': 'Dienstag',
        'Wednesday': 'Mittwoch',
        'Thursday': 'Donnerstag',
        'Friday': 'Freitag',
        'Saturday': 'Samstag',
        'Sunday': 'Sonntag'
    }
    weekday_name_de = weekday_names_de.get(weekday_name, weekday_name)
    
    # Erstelle Stundenplan für den Tag
    schedule = []
    for period in range(1, 7):
        period_info = get_period_info(weekday, period)
        student_count = count_students_for_period(selected_date_str, period)
        available = MAX_STUDENTS_PER_PERIOD - student_count
        
        # Prüfe, ob Buchung zeitlich möglich ist
        can_book, time_message = check_booking_time(selected_date, period)
        
        schedule.append({
            'period': period,
            'time': f"{PERIOD_TIMES[period]['start']} - {PERIOD_TIMES[period]['end']}",
            'type': period_info['type'],
            'label': period_info['label'],
            'booked': student_count,
            'available': available,
            'can_book': can_book and available > 0,
            'time_message': time_message
        })
    
    # Erstelle Wochenübersicht (Montag-Freitag) mit Buchungsdaten
    from models import get_bookings_for_week
    
    # Berechne Montag und Freitag der aktuellen Woche
    days_since_monday = selected_date.weekday()
    monday = selected_date - timedelta(days=days_since_monday)
    friday = monday + timedelta(days=4)
    
    # Hole alle Buchungen für diese Woche
    week_bookings = get_bookings_for_week(monday.strftime('%Y-%m-%d'), friday.strftime('%Y-%m-%d'))
    
    # Organisiere Buchungen nach Datum und Stunde
    bookings_by_date_period = {}
    for booking in week_bookings:
        booking_dict = dict(booking)
        key = f"{booking_dict['date']}_{booking_dict['period']}"
        if key not in bookings_by_date_period:
            bookings_by_date_period[key] = []
        
        students = json.loads(booking_dict['students_json']) if booking_dict.get('students_json') else []
        bookings_by_date_period[key].append({
            'teacher_name': booking_dict.get('teacher_name', 'N/A'),
            'teacher_class': booking_dict.get('teacher_class', 'N/A'),
            'student_count': len(students),
            'students': students,
            'offer_label': booking_dict.get('offer_label', 'N/A')
        })
    
    week_overview = []
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    weekday_names = ['Mo', 'Di', 'Mi', 'Do', 'Fr']
    
    for i, wd in enumerate(weekdays):
        day_date = monday + timedelta(days=i)
        day_date_str = day_date.strftime('%Y-%m-%d')
        
        day_schedule = []
        for period in range(1, 7):
            info = get_period_info(wd, period)
            key = f"{day_date_str}_{period}"
            period_bookings = bookings_by_date_period.get(key, [])
            
            total_students = sum(b['student_count'] for b in period_bookings)
            
            day_schedule.append({
                'period': period,
                'type': info['type'],
                'label': info['label'],
                'bookings': period_bookings,
                'total_students': total_students
            })
        week_overview.append({
            'weekday': wd,
            'name': weekday_names[i],
            'date': day_date_str,
            'date_formatted': day_date.strftime('%d.%m.'),
            'schedule': day_schedule
        })
    
    return render_template('dashboard.html',
                         selected_date=selected_date,
                         weekday=weekday_name_de,
                         schedule=schedule,
                         week_overview=week_overview,
                         user_role=session.get('user_role'))

# Route: Buchungsseite
@app.route('/book/<date_str>/<int:period>', methods=['GET', 'POST'])
@login_required
def book(date_str, period):
    """Seite zum Erstellen einer neuen Buchung"""
    
    # Validiere Datum und Stunde
    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        flash('Ungültiges Datum.', 'error')
        return redirect(url_for('dashboard'))
    
    if period < 1 or period > 6:
        flash('Ungültige Stunde.', 'error')
        return redirect(url_for('dashboard'))
    
    # Ermittle Wochentag und Stundeninfo
    weekday = booking_date.strftime('%a')
    period_info = get_period_info(weekday, period)
    
    # Prüfe verfügbare Plätze
    current_students = count_students_for_period(date_str, period)
    available_spots = MAX_STUDENTS_PER_PERIOD - current_students
    
    if available_spots <= 0:
        flash('Diese Stunde ist bereits voll belegt.', 'error')
        return redirect(url_for('dashboard', date=date_str))
    
    # Prüfe Zeitfenster
    can_book, time_message = check_booking_time(booking_date, period)
    if not can_book:
        flash(time_message or 'Buchung nicht möglich.', 'error')
        return redirect(url_for('dashboard', date=date_str))
    
    if request.method == 'POST':
        # Hole Lehrkraft-Informationen
        teacher_name = request.form.get('teacher_name', '').strip()
        teacher_class = request.form.get('teacher_class', '').strip()
        
        if not teacher_name or not teacher_class:
            flash('Bitte geben Sie Ihren Namen und Ihre Klasse ein.', 'error')
            return render_template('book.html', 
                                 date_str=date_str,
                                 period=period,
                                 period_info=period_info,
                                 period_time=PERIOD_TIMES[period],
                                 available_spots=available_spots,
                                 free_modules=FREE_MODULES)
        
        # Hole Anzahl der Schüler
        num_students = int(request.form.get('num_students', 1))
        
        if num_students < 1 or num_students > 5:
            flash('Bitte wählen Sie zwischen 1 und 5 Schülern.', 'error')
            return render_template('book.html', 
                                 date_str=date_str,
                                 period=period,
                                 period_info=period_info,
                                 period_time=PERIOD_TIMES[period],
                                 available_spots=available_spots,
                                 free_modules=FREE_MODULES)
        
        # Prüfe erneut verfügbare Plätze
        if num_students > available_spots:
            flash(f'Nicht genug Plätze verfügbar. Nur noch {available_spots} Plätze frei.', 'error')
            return redirect(url_for('dashboard', date=date_str))
        
        # Sammle Schülerdaten
        students = []
        for i in range(num_students):
            name = request.form.get(f'student_name_{i}', '').strip()
            klasse = request.form.get(f'student_class_{i}', '').strip()
            
            if not name or not klasse:
                flash('Bitte füllen Sie alle Schülerfelder aus.', 'error')
                return render_template('book.html', 
                                     date_str=date_str,
                                     period=period,
                                     period_info=period_info,
                                     period_time=PERIOD_TIMES[period],
                                     available_spots=available_spots,
                                     free_modules=FREE_MODULES)
            
            students.append({'name': name, 'klasse': klasse})
        
        # Hole Modul-Wahl (nur bei freien Stunden)
        if period_info['type'] == 'frei':
            selected_module = request.form.get('module', '')
            if selected_module not in FREE_MODULES:
                flash('Bitte wählen Sie ein Modul.', 'error')
                return render_template('book.html', 
                                     date_str=date_str,
                                     period=period,
                                     period_info=period_info,
                                     period_time=PERIOD_TIMES[period],
                                     available_spots=available_spots,
                                     free_modules=FREE_MODULES)
            offer_label = selected_module
        else:
            offer_label = period_info['label']
        
        # Erstelle Buchung in Datenbank
        booking_id = create_booking(
            date=date_str,
            weekday=weekday,
            period=period,
            teacher_id=session['user_id'],
            students=students,
            offer_type=period_info['type'],
            offer_label=offer_label,
            teacher_name=teacher_name,
            teacher_class=teacher_class
        )
        
        if booking_id:
            # Sende E-Mail-Benachrichtigung
            booking_data = {
                'date': date_str,
                'weekday': weekday,
                'period': period,
                'students': students,
                'offer_type': period_info['type'],
                'offer_label': offer_label,
                'teacher_name': teacher_name,
                'teacher_class': teacher_class
            }
            send_booking_notification(booking_data, session.get('user_email', 'system'))
            
            flash(f'Buchung erfolgreich! {len(students)} Schüler für {offer_label} angemeldet.', 'success')
            return redirect(url_for('dashboard', date=date_str))
        else:
            flash('Fehler beim Erstellen der Buchung.', 'error')
    
    return render_template('book.html',
                         date_str=date_str,
                         period=period,
                         period_info=period_info,
                         period_time=PERIOD_TIMES[period],
                         available_spots=available_spots,
                         free_modules=FREE_MODULES)

# Route: Admin-Bereich
@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin():
    """Admin-Seite für Benutzerverwaltung und Buchungsübersicht"""
    
    if request.method == 'POST':
        # Neue Lehrkraft anlegen
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()
        
        if not username or not password:
            flash('Bitte füllen Sie alle Felder aus.', 'error')
        else:
            user_id = create_user(username, password, 'teacher', email if email else None)
            if user_id:
                flash(f'Lehrkraft {username} erfolgreich angelegt.', 'success')
            else:
                flash('Benutzername existiert bereits.', 'error')
    
    # Hole alle Benutzer
    users = get_all_users()
    
    # Hole alle Buchungen
    filter_date = request.args.get('filter_date', '')
    if filter_date:
        bookings = get_bookings_by_date(filter_date)
    else:
        bookings = get_all_bookings()
    
    # Konvertiere Buchungen für Anzeige
    bookings_display = []
    for booking in bookings:
        booking_dict = dict(booking)
        students = json.loads(booking_dict['students_json']) if booking_dict.get('students_json') else []
        bookings_display.append({
            'id': booking_dict['id'],
            'date': booking_dict['date'],
            'weekday': booking_dict['weekday'],
            'period': booking_dict['period'],
            'teacher_email': booking_dict['teacher_email'],
            'teacher_name': booking_dict.get('teacher_name', 'N/A'),
            'teacher_class': booking_dict.get('teacher_class', 'N/A'),
            'offer_label': booking_dict['offer_label'],
            'offer_type': booking_dict['offer_type'],
            'students': students,
            'student_count': len(students)
        })
    
    return render_template('admin.html',
                         users=users,
                         bookings=bookings_display,
                         filter_date=filter_date)

# Route: Buchung erstellen (nur Admin)
@app.route('/admin/create_booking', methods=['GET', 'POST'])
@admin_required
def admin_create_booking():
    """Admin kann Buchungen für beliebige Lehrkräfte erstellen"""
    from models import get_booking_by_id
    
    if request.method == 'POST':
        date_str = request.form.get('date', '').strip()
        
        try:
            period = int(request.form.get('period', 1))
            teacher_id = int(request.form.get('teacher_id', 0))
            num_students = int(request.form.get('num_students', 1))
        except (ValueError, TypeError):
            flash('Ungültige Eingabe für Stunde, Lehrkraft oder Schüleranzahl.', 'error')
            users = get_all_users()
            return render_template('admin_edit_booking.html',
                                 booking=None,
                                 users=users,
                                 free_modules=FREE_MODULES,
                                 period_times=PERIOD_TIMES)
        
        teacher_name = request.form.get('teacher_name', '').strip()
        teacher_class = request.form.get('teacher_class', '').strip()
        
        if not date_str or not teacher_id or not teacher_name or not teacher_class or num_students < 1 or num_students > 5:
            flash('Bitte füllen Sie alle Pflichtfelder aus und wählen Sie 1-5 Schüler.', 'error')
            users = get_all_users()
            return render_template('admin_edit_booking.html',
                                 booking=None,
                                 users=users,
                                 free_modules=FREE_MODULES,
                                 period_times=PERIOD_TIMES)
        
        try:
            booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            flash('Ungültiges Datum.', 'error')
            users = get_all_users()
            return render_template('admin_edit_booking.html',
                                 booking=None,
                                 users=users,
                                 free_modules=FREE_MODULES,
                                 period_times=PERIOD_TIMES)
        
        weekday = booking_date.strftime('%a')
        period_info = get_period_info(weekday, period)
        
        # Prüfe Kapazität vor dem Erstellen der Buchung
        current_students = count_students_for_period(date_str, period)
        available_spots = MAX_STUDENTS_PER_PERIOD - current_students
        
        if num_students > available_spots:
            flash(f'Nicht genug Plätze verfügbar. Nur noch {available_spots} Plätze frei.', 'error')
            users = get_all_users()
            return render_template('admin_edit_booking.html',
                                 booking=None,
                                 users=users,
                                 free_modules=FREE_MODULES,
                                 period_times=PERIOD_TIMES)
        
        students = []
        for i in range(num_students):
            name = request.form.get(f'student_name_{i}', '').strip()
            klasse = request.form.get(f'student_class_{i}', '').strip()
            
            if not name or not klasse:
                flash('Bitte füllen Sie alle Schülerfelder aus.', 'error')
                users = get_all_users()
                return render_template('admin_edit_booking.html',
                                     booking=None,
                                     users=users,
                                     free_modules=FREE_MODULES,
                                     period_times=PERIOD_TIMES)
            
            students.append({'name': name, 'klasse': klasse})
        
        if period_info['type'] == 'frei':
            selected_module = request.form.get('module', '')
            if selected_module not in FREE_MODULES:
                flash('Bitte wählen Sie ein Modul.', 'error')
                users = get_all_users()
                return render_template('admin_edit_booking.html',
                                     booking=None,
                                     users=users,
                                     free_modules=FREE_MODULES,
                                     period_times=PERIOD_TIMES)
            offer_label = selected_module
        else:
            offer_label = period_info['label']
        
        booking_id = create_booking(
            date=date_str,
            weekday=weekday,
            period=period,
            teacher_id=teacher_id,
            students=students,
            offer_type=period_info['type'],
            offer_label=offer_label,
            teacher_name=teacher_name,
            teacher_class=teacher_class
        )
        
        if booking_id:
            flash(f'Buchung erfolgreich erstellt! {len(students)} Schüler für {offer_label} angemeldet.', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Fehler beim Erstellen der Buchung.', 'error')
    
    users = get_all_users()
    return render_template('admin_edit_booking.html',
                         booking=None,
                         users=users,
                         free_modules=FREE_MODULES,
                         period_times=PERIOD_TIMES)

# Route: Buchung bearbeiten (nur Admin)
@app.route('/admin/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_booking(booking_id):
    """Admin kann bestehende Buchungen bearbeiten"""
    from models import get_booking_by_id, update_booking
    
    booking_row = get_booking_by_id(booking_id)
    if not booking_row:
        flash('Buchung nicht gefunden.', 'error')
        return redirect(url_for('admin'))
    
    booking = dict(booking_row)
    
    if request.method == 'POST':
        date_str = request.form.get('date', '').strip()
        
        try:
            period = int(request.form.get('period', 1))
            teacher_id = int(request.form.get('teacher_id', 0))
            num_students = int(request.form.get('num_students', 1))
        except (ValueError, TypeError):
            flash('Ungültige Eingabe für Stunde, Lehrkraft oder Schüleranzahl.', 'error')
            users = get_all_users()
            students = json.loads(booking['students_json']) if booking.get('students_json') else []
            booking_display = dict(booking)
            booking_display['students'] = students
            return render_template('admin_edit_booking.html',
                                 booking=booking_display,
                                 users=users,
                                 free_modules=FREE_MODULES,
                                 period_times=PERIOD_TIMES)
        
        teacher_name = request.form.get('teacher_name', '').strip()
        teacher_class = request.form.get('teacher_class', '').strip()
        
        if not date_str or not teacher_id or not teacher_name or not teacher_class or num_students < 1 or num_students > 5:
            flash('Bitte füllen Sie alle Pflichtfelder aus und wählen Sie 1-5 Schüler.', 'error')
            users = get_all_users()
            students = json.loads(booking['students_json']) if booking.get('students_json') else []
            booking_display = dict(booking)
            booking_display['students'] = students
            return render_template('admin_edit_booking.html',
                                 booking=booking_display,
                                 users=users,
                                 free_modules=FREE_MODULES,
                                 period_times=PERIOD_TIMES)
        
        try:
            booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            flash('Ungültiges Datum.', 'error')
            users = get_all_users()
            students = json.loads(booking['students_json']) if booking.get('students_json') else []
            booking_display = dict(booking)
            booking_display['students'] = students
            return render_template('admin_edit_booking.html',
                                 booking=booking_display,
                                 users=users,
                                 free_modules=FREE_MODULES,
                                 period_times=PERIOD_TIMES)
        
        weekday = booking_date.strftime('%a')
        period_info = get_period_info(weekday, period)
        
        # Prüfe Kapazität: Berechne verfügbare Plätze ohne die aktuelle Buchung
        current_students = count_students_for_period(date_str, period)
        old_booking_students = len(json.loads(booking['students_json']) if booking.get('students_json') else [])
        available_spots = MAX_STUDENTS_PER_PERIOD - (current_students - old_booking_students)
        
        if num_students > available_spots:
            flash(f'Nicht genug Plätze verfügbar. Nur noch {available_spots} Plätze frei.', 'error')
            users = get_all_users()
            students = json.loads(booking['students_json']) if booking.get('students_json') else []
            booking_display = dict(booking)
            booking_display['students'] = students
            return render_template('admin_edit_booking.html',
                                 booking=booking_display,
                                 users=users,
                                 free_modules=FREE_MODULES,
                                 period_times=PERIOD_TIMES)
        
        students = []
        for i in range(num_students):
            name = request.form.get(f'student_name_{i}', '').strip()
            klasse = request.form.get(f'student_class_{i}', '').strip()
            
            if not name or not klasse:
                flash('Bitte füllen Sie alle Schülerfelder aus.', 'error')
                users = get_all_users()
                students = json.loads(booking['students_json']) if booking.get('students_json') else []
                booking_display = dict(booking)
                booking_display['students'] = students
                return render_template('admin_edit_booking.html',
                                     booking=booking_display,
                                     users=users,
                                     free_modules=FREE_MODULES,
                                     period_times=PERIOD_TIMES)
            
            students.append({'name': name, 'klasse': klasse})
        
        if period_info['type'] == 'frei':
            selected_module = request.form.get('module', '')
            if selected_module not in FREE_MODULES:
                flash('Bitte wählen Sie ein Modul.', 'error')
                users = get_all_users()
                students = json.loads(booking['students_json']) if booking.get('students_json') else []
                booking_display = dict(booking)
                booking_display['students'] = students
                return render_template('admin_edit_booking.html',
                                     booking=booking_display,
                                     users=users,
                                     free_modules=FREE_MODULES,
                                     period_times=PERIOD_TIMES)
            offer_label = selected_module
        else:
            offer_label = period_info['label']
        
        if update_booking(
            booking_id=booking_id,
            date=date_str,
            weekday=weekday,
            period=period,
            teacher_id=teacher_id,
            students=students,
            offer_type=period_info['type'],
            offer_label=offer_label,
            teacher_name=teacher_name,
            teacher_class=teacher_class
        ):
            flash(f'Buchung erfolgreich aktualisiert!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Fehler beim Aktualisieren der Buchung.', 'error')
    
    users = get_all_users()
    students = json.loads(booking['students_json']) if booking.get('students_json') else []
    booking_display = dict(booking)
    booking_display['students'] = students
    
    return render_template('admin_edit_booking.html',
                         booking=booking_display,
                         users=users,
                         free_modules=FREE_MODULES,
                         period_times=PERIOD_TIMES)

# Route: Buchung löschen (nur Admin)
@app.route('/admin/delete_booking/<int:booking_id>', methods=['POST'])
@admin_required
def delete_booking_route(booking_id):
    """Löscht eine Buchung"""
    from models import delete_booking
    
    if delete_booking(booking_id):
        flash('Buchung erfolgreich gelöscht.', 'success')
    else:
        flash('Buchung konnte nicht gelöscht werden.', 'error')
    
    return redirect(url_for('admin'))

if __name__ == '__main__':
    # Starte die Anwendung
    app.run(host='0.0.0.0', port=5000, debug=True)
