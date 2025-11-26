# Haupt-Anwendungsdatei für die SportOase-Buchungssystem
# Diese Datei enthält alle Routen (URLs) und die Logik der Webanwendung

from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, jsonify
from datetime import datetime, timedelta, date
from werkzeug.middleware.proxy_fix import ProxyFix
import pytz
import json
import os
import queue
import threading

# Flask-App erstellen
app = Flask(__name__)

# Session-Secret aus Umgebungsvariable (MUSS gesetzt sein!)
session_secret = os.environ.get('SESSION_SECRET')
if not session_secret:
    raise RuntimeError(
        "SESSION_SECRET Umgebungsvariable ist nicht gesetzt! "
        "Bitte setzen Sie einen sicheren, zufälligen Wert in Replit Secrets."
    )
app.secret_key = session_secret
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Cookie-Einstellungen für iFrame-Kompatibilität (IServ Embed)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True

@app.after_request
def add_iframe_headers(response):
    """Erlaubt Einbettung in IServ iFrame"""
    # Erlaube Einbettung von kgs-pattensen.de
    response.headers['X-Frame-Options'] = 'ALLOW-FROM https://kgs-pattensen.de'
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self' https://kgs-pattensen.de"
    return response

# SSE Broadcaster für Echtzeit-Benachrichtigungen
notification_subscribers = []
subscribers_lock = threading.Lock()

def broadcast_notification(notification_data):
    """Sendet eine Benachrichtigung an alle verbundenen SSE-Clients"""
    with subscribers_lock:
        dead_queues = []
        for q in notification_subscribers:
            try:
                q.put_nowait(notification_data)
            except queue.Full:
                dead_queues.append(q)
        
        for q in dead_queues:
            notification_subscribers.remove(q)

# CSRF-Token Generierung und Validierung
import secrets

def generate_csrf_token():
    """Generiert ein CSRF-Token und speichert es in der Session"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

def validate_csrf_token(token):
    """Validiert das CSRF-Token"""
    return token == session.get('csrf_token')

@app.context_processor
def inject_csrf_token():
    """Macht csrf_token in allen Templates verfügbar"""
    return dict(csrf_token=generate_csrf_token())

# Datenbank-Konfiguration
db_uri = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")

# Strip whitespace from database URL (in case of accidental spaces)
if db_uri:
    db_uri = db_uri.strip()

if not db_uri:
    raise RuntimeError(
        "Keine DB-URL gefunden. Bitte DATABASE_URL "
        "oder SQLALCHEMY_DATABASE_URI setzen."
    )

app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
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
    update_booking, delete_booking, User, Booking,
    create_notification, get_unread_notifications, get_recent_notifications,
    mark_notification_as_read, mark_all_notifications_as_read,
    get_unread_notification_count, get_booking_by_id, check_student_double_booking,
    change_user_password, get_or_create_oauth_user
)
from config import *
from email_service import send_booking_notification

# IServ OAuth-Integration initialisieren
from oauth_config import init_oauth, determine_user_role
oauth_instance, iserv_client = init_oauth(app)

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
    from models import get_custom_slot_name
    
    if weekday in FIXED_OFFERS and period in FIXED_OFFERS[weekday]:
        custom_label = get_custom_slot_name(weekday, period)
        label = custom_label if custom_label else FIXED_OFFERS[weekday][period]
        return {
            'type': 'fest',
            'label': label
        }
    else:
        return {
            'type': 'frei',
            'label': 'Freie Wahl'
        }

# Hilfsfunktion: Prüft, ob ein Datum in der Vergangenheit liegt
def is_past_date(check_date, period=None):
    """
    Prüft, ob ein Datum (und optional eine Stunde) in der Vergangenheit liegt
    """
    berlin_tz = get_berlin_tz()
    now = datetime.now(berlin_tz)
    
    if period is not None:
        # Prüfe mit spezifischer Stunde
        period_start_time = PERIOD_TIMES[period]['start']
        hour, minute = map(int, period_start_time.split(':'))
        period_datetime = berlin_tz.localize(
            datetime.combine(check_date, datetime.min.time()).replace(hour=hour, minute=minute)
        )
        return period_datetime < now
    else:
        # Prüfe nur Datum
        today = now.date()
        return check_date < today

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

# Route: Startseite (leitet direkt zu IServ weiter)
@app.route('/')
def index():
    """Startseite - leitet zum Dashboard oder IServ-Login weiter"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_iserv'))

# Route: Direkter IServ-Embed Login (für iFrame-Integration)
@app.route('/iserv/embed')
def iserv_embed_login():
    """
    Direkter Login für IServ-Embed (iFrame) Integration.
    IServ sendet Benutzer-Informationen über URL-Parameter:
    - %user% → user Parameter
    - %email% → email Parameter
    - %domain% → domain Parameter (zur Verifizierung)
    
    Sicherheit:
    - Nur @kgs-pattensen.de E-Mails
    - Nur bereits registrierte Benutzer (neue müssen OAuth nutzen)
    - Zusätzliche Token-Validierung über ISERV_EMBED_SECRET
    """
    import hmac
    import hashlib
    import time
    
    user = request.args.get('user', '').strip()
    email = request.args.get('email', '').strip().lower()
    domain = request.args.get('domain', '').strip().lower()
    token = request.args.get('token', '').strip()
    timestamp = request.args.get('ts', '').strip()
    
    # Debug-Log
    print(f"🔐 IServ Embed Versuch: user={user}, email={email}, domain={domain}")
    
    # Prüfe ob alle Parameter vorhanden sind
    if not user or not email:
        flash('Ungültige IServ-Anmeldung.', 'error')
        return render_template('login.html')
    
    # Prüfe ob E-Mail zur Schule gehört (wichtigste Sicherheitsprüfung)
    if not email.endswith('@kgs-pattensen.de'):
        flash('Nur @kgs-pattensen.de E-Mail-Adressen sind erlaubt.', 'error')
        return render_template('login.html')
    
    # Optional: HMAC-Token Validierung (wenn ISERV_EMBED_SECRET gesetzt ist)
    embed_secret = os.environ.get('ISERV_EMBED_SECRET')
    if embed_secret:
        # Wenn Secret konfiguriert, muss Token gültig sein
        if not token or not timestamp:
            print(f"⚠️ IServ Embed: Token fehlt für {email}")
            flash('Ungültige Anmeldung (Token fehlt).', 'error')
            return render_template('login.html')
        
        # Prüfe Zeitstempel (max 5 Minuten alt)
        try:
            ts = int(timestamp)
            if abs(time.time() - ts) > 300:
                print(f"⚠️ IServ Embed: Token abgelaufen für {email}")
                flash('Anmeldung abgelaufen. Bitte erneut versuchen.', 'error')
                return render_template('login.html')
        except ValueError:
            flash('Ungültige Anmeldung.', 'error')
            return render_template('login.html')
        
        # Validiere HMAC
        expected = hmac.new(
            embed_secret.encode(),
            f"{email}:{timestamp}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(token, expected):
            print(f"⚠️ IServ Embed: Ungültiger Token für {email}")
            flash('Ungültige Anmeldung.', 'error')
            return render_template('login.html')
    
    # Hole bestehenden Benutzer aus der Datenbank
    existing_user = get_user_by_email(email)
    
    if existing_user:
        # Benutzer existiert bereits - direkt einloggen
        session['user_id'] = existing_user['id']
        session['user_username'] = existing_user['username']
        session['user_email'] = existing_user['email']
        session['user_role'] = existing_user['role']
        
        print(f"🔐 IServ Embed Login: {email} (bestehender Benutzer)")
        return redirect(url_for('dashboard'))
    else:
        # Neuer Benutzer - muss sich erst über OAuth registrieren
        flash('Bitte melden Sie sich einmalig über "Mit IServ anmelden" an.', 'info')
        return render_template('login.html')

# Route: Login-Seite (nur IServ-Button)
@app.route('/login')
def login():
    """Login-Seite - zeigt nur IServ-Login-Button"""
    return render_template('login.html')

# Route: IServ SSO Login initiieren
@app.route('/login/iserv')
def login_iserv():
    """Startet den IServ OAuth2-Login-Flow"""
    if not iserv_client:
        flash('IServ-Login ist nicht konfiguriert.', 'error')
        return redirect(url_for('login'))
    
    redirect_uri = url_for('oauth_callback', _external=True)
    return iserv_client.authorize_redirect(redirect_uri)

# Route: OAuth Callback von IServ
@app.route('/oauth/callback')
def oauth_callback():
    """Callback-Route für IServ OAuth2"""
    if not iserv_client:
        flash('IServ-Login ist nicht konfiguriert.', 'error')
        return redirect(url_for('login'))
    
    try:
        token = iserv_client.authorize_access_token()
        userinfo = token.get('userinfo')
        
        if not userinfo:
            userinfo = iserv_client.userinfo(token=token)
        
        email = userinfo.get('email')
        sub = userinfo.get('sub')
        name = userinfo.get('name', email)
        
        if not email or not sub:
            flash('Fehler beim Abrufen der Benutzerdaten von IServ.', 'error')
            return redirect(url_for('login'))
        
        role = determine_user_role(userinfo)
        
        # Log OAuth-Daten für Debugging
        print(f"🔐 IServ Login: {email}")
        print(f"   Sub-ID: {sub}")
        print(f"   Rolle: {role}")
        print(f"   UserInfo: {userinfo}")
        
        # Prüfe ob Benutzer Zugang hat (nur Lehrer, Mitarbeitende, Administrator)
        if role is None:
            flash('Kein Zugang. Nur Lehrer und Mitarbeitende können sich anmelden.', 'error')
            print(f"❌ Zugang verweigert für: {email} (keine berechtigte Gruppe)")
            return redirect(url_for('login'))
        
        # Verwende E-Mail direkt als Username für OAuth-Benutzer
        user = get_or_create_oauth_user(
            email=email,
            username=email,  # E-Mail als Username (vermeidet Unique-Constraint-Fehler)
            oauth_provider='iserv',
            oauth_id=sub,
            role=role
        )
        
        if not user:
            flash('Fehler beim Erstellen des Benutzers.', 'error')
            return redirect(url_for('login'))
        
        session['user_id'] = user['id']
        session['user_username'] = user['username']
        session['user_email'] = user['email']
        session['user_role'] = user['role']
        
        flash(f'Willkommen, {name}!', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        print(f"OAuth Fehler: {e}")
        flash('Fehler beim IServ-Login. Bitte versuchen Sie es erneut.', 'error')
        return redirect(url_for('login'))

# Route: Logout
@app.route('/logout')
def logout():
    """Meldet den Benutzer ab"""
    session.clear()
    flash('Sie wurden abgemeldet.', 'info')
    return redirect(url_for('login'))

# Route: Passwort ändern
@app.route('/change_password', methods=['GET', 'POST'])
@admin_required
def change_password():
    """Ermöglicht Admins Passwörter zu ändern"""
    if request.method == 'POST':
        # CSRF-Token Validierung
        csrf_token = request.form.get('csrf_token', '')
        if not validate_csrf_token(csrf_token):
            flash('Ungültiges Sicherheits-Token. Bitte versuchen Sie es erneut.', 'error')
            return redirect(url_for('change_password'))
        
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validierung
        if not old_password or not new_password or not confirm_password:
            flash('Bitte füllen Sie alle Felder aus.', 'error')
            return redirect(url_for('change_password'))
        
        if new_password != confirm_password:
            flash('Die neuen Passwörter stimmen nicht überein.', 'error')
            return redirect(url_for('change_password'))
        
        if len(new_password) < 6:
            flash('Das neue Passwort muss mindestens 6 Zeichen lang sein.', 'error')
            return redirect(url_for('change_password'))
        
        # Passwort ändern
        result = change_user_password(session['user_id'], old_password, new_password)
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(result['error'], 'error')
            return redirect(url_for('change_password'))
    
    return render_template('change_password.html')

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
    from models import is_slot_blocked, get_blocked_slot
    schedule = []
    for period in range(1, 7):
        period_info = get_period_info(weekday, period)
        student_count = count_students_for_period(selected_date_str, period)
        available = MAX_STUDENTS_PER_PERIOD - student_count
        
        # Prüfe, ob Slot blockiert ist
        blocked_slot = get_blocked_slot(selected_date_str, period)
        is_blocked = blocked_slot is not None
        
        # Prüfe, ob Termin in der Vergangenheit liegt
        is_past = is_past_date(selected_date, period)
        
        # Prüfe, ob es ein Wochenende ist
        is_weekend = selected_date.weekday() in [5, 6]
        
        # Prüfe, ob Buchung zeitlich möglich ist
        can_book, time_message = check_booking_time(selected_date, period)
        
        # can_book muss False sein für vergangene Termine oder Wochenenden
        if is_past:
            can_book = False
            if not time_message:
                time_message = "Dieser Termin liegt in der Vergangenheit."
        elif is_weekend:
            can_book = False
            if not time_message:
                time_message = "Buchungen sind am Wochenende nicht möglich."
        
        schedule.append({
            'period': period,
            'time': f"{PERIOD_TIMES[period]['start']} - {PERIOD_TIMES[period]['end']}",
            'type': period_info['type'],
            'label': period_info['label'],
            'booked': student_count,
            'available': available,
            'can_book': can_book and available > 0 and not is_blocked and not is_past and not is_weekend,
            'time_message': time_message,
            'blocked': blocked_slot,
            'blocked_reason': blocked_slot.get('reason', 'Beratung') if blocked_slot else None,
            'blocked_icon': blocked_slot.get('icon', '🔧') if blocked_slot else None,
            'is_past': is_past,
            'is_weekend': is_weekend
        })
    
    # Erstelle Wochenübersicht (Montag-Freitag) mit Buchungsdaten
    from models import get_bookings_for_week, get_blocked_slots_for_week, is_slot_blocked
    
    # Berechne Montag und Freitag der aktuellen Woche
    days_since_monday = selected_date.weekday()
    monday = selected_date - timedelta(days=days_since_monday)
    friday = monday + timedelta(days=4)
    
    # Berechne Kalenderwoche
    calendar_week = monday.isocalendar()[1]
    calendar_year = monday.isocalendar()[0]
    
    # Berechne vorherige und nächste Woche für Navigation
    prev_week_monday = monday - timedelta(days=7)
    next_week_monday = monday + timedelta(days=7)
    
    # Hole alle Buchungen für diese Woche
    week_bookings = get_bookings_for_week(monday.strftime('%Y-%m-%d'), friday.strftime('%Y-%m-%d'))
    
    # Hole alle blockierten Slots für diese Woche
    blocked_slots = get_blocked_slots_for_week(monday.strftime('%Y-%m-%d'), friday.strftime('%Y-%m-%d'))
    
    # Organisiere blockierte Slots nach Datum und Stunde
    blocked_by_date_period = {}
    for blocked in blocked_slots:
        key = f"{blocked['date']}_{blocked['period']}"
        blocked_by_date_period[key] = blocked
    
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
            'teacher_id': booking_dict.get('teacher_id'),
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
            blocked_slot = blocked_by_date_period.get(key)
            
            total_students = sum(b['student_count'] for b in period_bookings)
            available = MAX_STUDENTS_PER_PERIOD - total_students
            
            # Prüfe, ob Termin in der Vergangenheit liegt
            is_past = is_past_date(day_date, period)
            
            # Prüfe, ob es ein Wochenende ist
            is_weekend = day_date.weekday() in [5, 6]
            
            # Prüfe, ob Buchung für diesen Slot möglich ist
            can_book, _ = check_booking_time(day_date, period)
            can_book = can_book and available > 0 and not blocked_slot and not is_past and not is_weekend
            
            day_schedule.append({
                'period': period,
                'type': info['type'],
                'label': info['label'],
                'bookings': period_bookings,
                'total_students': total_students,
                'available': available,
                'can_book': can_book,
                'blocked': blocked_slot,
                'blocked_reason': blocked_slot.get('reason', 'Beratung') if blocked_slot else None,
                'blocked_icon': blocked_slot.get('icon', '🔧') if blocked_slot else None,
                'is_past': is_past,
                'is_weekend': is_weekend
            })
        # Prüfe ob heute
        today = datetime.now(get_berlin_tz()).date()
        is_today = day_date == today
        
        week_overview.append({
            'weekday': wd,
            'name': weekday_names[i],
            'date': day_date_str,
            'date_formatted': day_date.strftime('%d.%m.'),
            'schedule': day_schedule,
            'is_today': is_today
        })
    
    return render_template('dashboard.html',
                         selected_date=selected_date,
                         weekday=weekday_name_de,
                         schedule=schedule,
                         week_overview=week_overview,
                         user_role=session.get('user_role'),
                         current_user_id=session.get('user_id'),
                         calendar_week=calendar_week,
                         calendar_year=calendar_year,
                         prev_week_date=prev_week_monday.strftime('%Y-%m-%d'),
                         next_week_date=next_week_monday.strftime('%Y-%m-%d'),
                         monday_date=monday.strftime('%d.%m.%Y'),
                         friday_date=friday.strftime('%d.%m.%Y'))

# Route: Buchungsseite
@app.route('/book/<date_str>/<int:period>', methods=['GET', 'POST'])
@login_required
def book(date_str, period):
    """Seite zum Erstellen einer neuen Buchung"""
    from config import SCHOOL_CLASSES
    
    # Hole den Benutzernamen aus der Session für das Formular
    user_display_name = session.get('user_username', '')
    # Falls E-Mail als Username verwendet wird, extrahiere den Namen
    if '@' in user_display_name:
        user_display_name = user_display_name.split('@')[0].replace('.', ' ').title()
    
    # Validiere Datum und Stunde
    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        flash('Ungültiges Datum.', 'error')
        return redirect(url_for('dashboard'))
    
    if period < 1 or period > 6:
        flash('Ungültige Stunde.', 'error')
        return redirect(url_for('dashboard'))
    
    # Prüfe, ob Termin in der Vergangenheit liegt
    if is_past_date(booking_date, period):
        flash('Dieser Termin liegt in der Vergangenheit und kann nicht gebucht werden.', 'error')
        return redirect(url_for('dashboard'))
    
    # Prüfe, ob es ein Wochenende ist (Samstag=5, Sonntag=6)
    if booking_date.weekday() in [5, 6]:
        flash('Buchungen sind am Wochenende nicht möglich.', 'error')
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
    
    # Prüfe, ob Slot für Beratung blockiert ist (nur Admins können blockierte Slots sehen)
    from models import is_slot_blocked, get_blocked_slot
    if is_slot_blocked(date_str, period):
        blocked_info = get_blocked_slot(date_str, period)
        reason = blocked_info.get('reason', 'Beratung') if blocked_info else 'Beratung'
        flash(f'Dieser Slot ist für {reason} blockiert und kann nicht gebucht werden.', 'error')
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
                                 free_modules=FREE_MODULES,
                                 user_name=user_display_name,
                                 school_classes=SCHOOL_CLASSES)
        
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
                                 free_modules=FREE_MODULES,
                                 user_name=user_display_name,
                                 school_classes=SCHOOL_CLASSES)
        
        # Prüfe erneut verfügbare Plätze
        if num_students > available_spots:
            flash(f'Nicht genug Plätze verfügbar. Nur noch {available_spots} Plätze frei.', 'error')
            return redirect(url_for('dashboard', date=date_str))
        
        # Sammle Schülerdaten und prüfe Doppelbuchungen
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
                                     free_modules=FREE_MODULES,
                                     user_name=user_display_name,
                                     school_classes=SCHOOL_CLASSES)
            
            # Prüfe auf Doppelbuchung
            double_booking = check_student_double_booking(name, klasse, date_str, period)
            if double_booking['is_booked']:
                flash(f'⚠️ Doppelbuchung verhindert: {double_booking["booking_info"]}', 'error')
                return render_template('book.html', 
                                     date_str=date_str,
                                     period=period,
                                     period_info=period_info,
                                     period_time=PERIOD_TIMES[period],
                                     available_spots=available_spots,
                                     free_modules=FREE_MODULES,
                                     user_name=user_display_name,
                                     school_classes=SCHOOL_CLASSES)
            
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
                                     free_modules=FREE_MODULES,
                                     user_name=user_display_name,
                                     school_classes=SCHOOL_CLASSES)
            offer_label = selected_module
        else:
            offer_label = period_info['label']
        
        # Hole optionale Notizen
        notes = request.form.get('notes', '').strip()
        
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
            teacher_class=teacher_class,
            notes=notes if notes else None
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
                'teacher_class': teacher_class,
                'students_json': json.dumps(students, ensure_ascii=False)
            }
            # Erstelle Notification in der Datenbank
            notification_message = f"Neue Buchung: {teacher_name} hat {len(students)} Schüler für {offer_label} am {date_str} (Stunde {period}) angemeldet."
            notification_id = create_notification(
                booking_id=booking_id,
                message=notification_message,
                notification_type='new_booking',
                recipient_role='admin',
                metadata={
                    'teacher_name': teacher_name,
                    'teacher_class': teacher_class,
                    'date': date_str,
                    'period': period,
                    'offer_label': offer_label,
                    'students_count': len(students)
                }
            )
            
            # Sende E-Mail-Benachrichtigung an Admin (SMTP)
            try:
                send_booking_notification(booking_data)
            except Exception as e:
                print(f"E-Mail-Benachrichtigung fehlgeschlagen: {e}")
            
            # Sende E-Mail-Bestätigung an Lehrer (nur wenn Checkbox aktiviert)
            send_email_confirmation = request.form.get('send_email_confirmation') == '1'
            
            # Hole E-Mail direkt aus der Datenbank (zuverlässiger als Session)
            user_id = session.get('user_id')
            user_email = ''
            if user_id:
                user_data = get_user_by_id(user_id)
                if user_data:
                    user_email = user_data.get('email', '')
            
            print(f"[BUCHUNG] E-Mail-Checkbox aktiviert: {send_email_confirmation}")
            print(f"[BUCHUNG] User ID: {user_id}")
            print(f"[BUCHUNG] User E-Mail (aus DB): {user_email}")
            
            if send_email_confirmation and user_email:
                print(f"[BUCHUNG] Versuche E-Mail-Bestätigung an {user_email} zu senden...")
                try:
                    from email_service import send_user_booking_confirmation
                    result = send_user_booking_confirmation(user_email, booking_data)
                    print(f"[BUCHUNG] E-Mail-Versand Ergebnis: {result}")
                except Exception as e:
                    print(f"[BUCHUNG] Benutzer-E-Mail-Bestätigung fehlgeschlagen: {e}")
            else:
                print(f"[BUCHUNG] Keine E-Mail gesendet (Checkbox: {send_email_confirmation}, Email vorhanden: {bool(user_email)})")
            
            # Broadcast an SSE-Clients
            if notification_id:
                unread_count = get_unread_notification_count(recipient_role='admin')
                broadcast_notification({
                    'type': 'new_booking',
                    'notification_id': notification_id,
                    'message': notification_message,
                    'booking_data': {
                        'date': date_str,
                        'period': period,
                        'teacher_name': teacher_name,
                        'offer_label': offer_label,
                        'students_count': len(students)
                    },
                    'unread_count': unread_count
                })
            
            flash(f'Buchung erfolgreich! {len(students)} Schüler für {offer_label} angemeldet.', 'success')
            return redirect(url_for('dashboard', date=date_str))
        else:
            flash('Fehler beim Erstellen der Buchung.', 'error')
    
    # Hole E-Mail aus der Datenbank für die Anzeige
    display_user_email = ''
    user_id = session.get('user_id')
    if user_id:
        user_data = get_user_by_id(user_id)
        if user_data:
            display_user_email = user_data.get('email', '')
    
    return render_template('book.html',
                         date_str=date_str,
                         period=period,
                         period_info=period_info,
                         period_time=PERIOD_TIMES[period],
                         available_spots=available_spots,
                         free_modules=FREE_MODULES,
                         user_name=user_display_name,
                         user_email=display_user_email,
                         school_classes=SCHOOL_CLASSES)

# Hilfsfunktion: Prüft ob eine Buchung noch bearbeitet/gelöscht werden kann
def can_modify_booking(booking_date_str, period):
    """
    Prüft ob eine Buchung noch bearbeitet/gelöscht werden kann.
    Änderungen sind bis 1 Stunde vor dem Termin möglich.
    
    Returns:
        Tuple (can_modify: bool, reason: str or None)
    """
    try:
        booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        now = datetime.now(get_berlin_tz())
        today = now.date()
        
        # Vergangenes Datum?
        if booking_date < today:
            return False, "Vergangener Termin"
        
        # Heute: Prüfe ob weniger als 1 Stunde bis zum Termin
        if booking_date == today:
            period_start_str = PERIOD_TIMES[period]['start']
            period_start_time = datetime.strptime(period_start_str, '%H:%M').time()
            period_start = datetime.combine(today, period_start_time)
            period_start = get_berlin_tz().localize(period_start)
            
            # 1 Stunde vor Beginn
            cutoff_time = period_start - timedelta(hours=1)
            
            if now >= cutoff_time:
                return False, "Weniger als 1 Stunde vor Termin"
        
        return True, None
    except Exception as e:
        print(f"Fehler bei can_modify_booking: {e}")
        return False, "Fehler bei der Prüfung"

# Route: Meine Buchungen
@app.route('/meine-buchungen')
@login_required
def meine_buchungen():
    """Zeigt alle Buchungen des Benutzers (oder alle für Admin)"""
    from models import get_all_bookings, Booking
    
    user_id = session['user_id']
    is_admin = session.get('user_role') == 'admin'
    
    # Admin sieht alle Buchungen, normale Benutzer nur ihre eigenen
    if is_admin:
        all_bookings = get_all_bookings()
    else:
        bookings_query = Booking.query.filter_by(teacher_id=user_id).order_by(Booking.date.desc(), Booking.period).all()
        all_bookings = [b.to_dict() for b in bookings_query]
    
    # Deutsche Wochentagsnamen
    weekday_names_de = {
        'Mon': 'Montag', 'Tue': 'Dienstag', 'Wed': 'Mittwoch',
        'Thu': 'Donnerstag', 'Fri': 'Freitag', 'Sat': 'Samstag', 'Sun': 'Sonntag'
    }
    
    bookings_display = []
    for booking in all_bookings:
        booking_dict = dict(booking)
        students = json.loads(booking_dict['students_json']) if booking_dict.get('students_json') else []
        
        # Prüfe ob Buchung bearbeitet/gelöscht werden kann
        can_modify, modify_reason = can_modify_booking(booking_dict['date'], booking_dict['period'])
        
        # Admin kann immer bearbeiten
        if is_admin:
            can_modify = True
            modify_reason = None
        
        # Datum formatieren
        try:
            booking_date = datetime.strptime(booking_dict['date'], '%Y-%m-%d').date()
            date_formatted = booking_date.strftime('%d.%m.%Y')
            is_past = booking_date < datetime.now(get_berlin_tz()).date()
        except:
            date_formatted = booking_dict['date']
            is_past = False
        
        # Created_at formatieren
        created_at = booking_dict.get('created_at', '')
        if created_at:
            try:
                if isinstance(created_at, str):
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_dt = created_at
                created_at_formatted = created_dt.strftime('%d.%m.%Y %H:%M')
            except:
                created_at_formatted = str(created_at)
        else:
            created_at_formatted = '-'
        
        bookings_display.append({
            'id': booking_dict['id'],
            'date': booking_dict['date'],
            'date_formatted': date_formatted,
            'weekday': booking_dict['weekday'],
            'weekday_name': weekday_names_de.get(booking_dict['weekday'], booking_dict['weekday']),
            'period': booking_dict['period'],
            'period_time': f"{PERIOD_TIMES[booking_dict['period']]['start']} - {PERIOD_TIMES[booking_dict['period']]['end']}",
            'teacher_name': booking_dict.get('teacher_name', 'N/A'),
            'teacher_class': booking_dict.get('teacher_class', 'N/A'),
            'offer_label': booking_dict['offer_label'],
            'offer_type': booking_dict['offer_type'],
            'students': students,
            'can_modify': can_modify,
            'modify_reason': modify_reason,
            'is_past': is_past,
            'created_at_formatted': created_at_formatted
        })
    
    return render_template('meine_buchungen.html',
                         bookings=bookings_display,
                         is_admin=is_admin)

# Route: Eigene Buchung bearbeiten
@app.route('/meine-buchungen/bearbeiten/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def edit_my_booking(booking_id):
    """Benutzer kann eigene Buchung bearbeiten (bis 1 Stunde vorher)"""
    from models import get_booking_by_id, update_booking, Booking
    
    user_id = session['user_id']
    is_admin = session.get('user_role') == 'admin'
    
    booking_row = get_booking_by_id(booking_id)
    if not booking_row:
        flash('Buchung nicht gefunden.', 'error')
        return redirect(url_for('meine_buchungen'))
    
    booking = dict(booking_row)
    
    # Prüfe Berechtigung: Eigene Buchung oder Admin
    if booking['teacher_id'] != user_id and not is_admin:
        flash('Sie können nur Ihre eigenen Buchungen bearbeiten.', 'error')
        return redirect(url_for('meine_buchungen'))
    
    # Prüfe ob Bearbeitung noch möglich ist (außer Admin)
    if not is_admin:
        can_modify, modify_reason = can_modify_booking(booking['date'], booking['period'])
        if not can_modify:
            flash(f'Diese Buchung kann nicht mehr bearbeitet werden: {modify_reason}', 'error')
            return redirect(url_for('meine_buchungen'))
    
    # Deutsche Wochentagsnamen
    weekday_names_de = {
        'Mon': 'Montag', 'Tue': 'Dienstag', 'Wed': 'Mittwoch',
        'Thu': 'Donnerstag', 'Fri': 'Freitag', 'Sat': 'Samstag', 'Sun': 'Sonntag'
    }
    
    students = json.loads(booking['students_json']) if booking.get('students_json') else []
    
    # Berechne verfügbare Plätze (ohne die aktuelle Buchung)
    current_students = count_students_for_period(booking['date'], booking['period'])
    available_spots = MAX_STUDENTS_PER_PERIOD - (current_students - len(students))
    
    # Datum formatieren
    try:
        booking_date = datetime.strptime(booking['date'], '%Y-%m-%d').date()
        date_formatted = booking_date.strftime('%d.%m.%Y')
    except:
        date_formatted = booking['date']
    
    if request.method == 'POST':
        # CSRF-Token Validierung
        csrf_token = request.form.get('csrf_token', '')
        if not validate_csrf_token(csrf_token):
            flash('Ungültiges Sicherheits-Token. Bitte versuchen Sie es erneut.', 'error')
            return redirect(url_for('edit_my_booking', booking_id=booking_id))
        
        try:
            num_students = int(request.form.get('num_students', 1))
        except (ValueError, TypeError):
            flash('Ungültige Schüleranzahl.', 'error')
            return redirect(url_for('edit_my_booking', booking_id=booking_id))
        
        if num_students < 1 or num_students > available_spots:
            flash(f'Bitte wählen Sie zwischen 1 und {available_spots} Schüler*innen.', 'error')
            return redirect(url_for('edit_my_booking', booking_id=booking_id))
        
        # Sammle Schülerdaten
        new_students = []
        for i in range(num_students):
            name = request.form.get(f'student_name_{i}', '').strip()
            klasse = request.form.get(f'student_class_{i}', '').strip()
            
            if not name or not klasse:
                flash('Bitte füllen Sie alle Schülerfelder aus.', 'error')
                return redirect(url_for('edit_my_booking', booking_id=booking_id))
            
            # Prüfe auf Doppelbuchung (außer bei der aktuellen Buchung)
            double_booking = check_student_double_booking(name, klasse, booking['date'], booking['period'], exclude_booking_id=booking_id)
            if double_booking['is_booked']:
                flash(f'⚠️ Doppelbuchung verhindert: {double_booking["booking_info"]}', 'error')
                return redirect(url_for('edit_my_booking', booking_id=booking_id))
            
            new_students.append({'name': name, 'klasse': klasse})
        
        # Hole Modul-Wahl (nur bei freien Stunden)
        if booking['offer_type'] == 'frei':
            selected_module = request.form.get('module', '')
            if selected_module not in FREE_MODULES:
                flash('Bitte wählen Sie ein Modul.', 'error')
                return redirect(url_for('edit_my_booking', booking_id=booking_id))
            offer_label = selected_module
        else:
            offer_label = booking['offer_label']
        
        # Aktualisiere Buchung (Notizen bleiben unverändert bei Lehrer-Bearbeitung)
        if update_booking(
            booking_id=booking_id,
            date=booking['date'],
            weekday=booking['weekday'],
            period=booking['period'],
            teacher_id=booking['teacher_id'],
            students=new_students,
            offer_type=booking['offer_type'],
            offer_label=offer_label,
            teacher_name=booking.get('teacher_name'),
            teacher_class=booking.get('teacher_class'),
            notes=booking.get('notes')
        ):
            flash('Buchung erfolgreich aktualisiert!', 'success')
            return redirect(url_for('meine_buchungen'))
        else:
            flash('Fehler beim Aktualisieren der Buchung.', 'error')
    
    # Booking-Objekt für Template vorbereiten
    booking_display = {
        'id': booking['id'],
        'date': booking['date'],
        'date_formatted': date_formatted,
        'weekday': booking['weekday'],
        'weekday_name': weekday_names_de.get(booking['weekday'], booking['weekday']),
        'period': booking['period'],
        'offer_label': booking['offer_label'],
        'offer_type': booking['offer_type'],
        'students': students
    }
    
    return render_template('edit_my_booking.html',
                         booking=booking_display,
                         period_times=PERIOD_TIMES,
                         free_modules=FREE_MODULES,
                         school_classes=SCHOOL_CLASSES,
                         max_students=available_spots,
                         available_spots=available_spots - len(students))

# Route: Eigene Buchung löschen
@app.route('/meine-buchungen/loeschen/<int:booking_id>', methods=['POST'])
@login_required
def delete_my_booking(booking_id):
    """Benutzer kann eigene Buchung löschen (bis 1 Stunde vorher)"""
    from models import get_booking_by_id, delete_booking
    
    # CSRF-Token Validierung
    csrf_token = request.form.get('csrf_token', '')
    if not validate_csrf_token(csrf_token):
        flash('Ungültiges Sicherheits-Token. Bitte versuchen Sie es erneut.', 'error')
        return redirect(url_for('meine_buchungen'))
    
    user_id = session['user_id']
    is_admin = session.get('user_role') == 'admin'
    
    booking_row = get_booking_by_id(booking_id)
    if not booking_row:
        flash('Buchung nicht gefunden.', 'error')
        return redirect(url_for('meine_buchungen'))
    
    booking = dict(booking_row)
    
    # Prüfe Berechtigung: Eigene Buchung oder Admin
    if booking['teacher_id'] != user_id and not is_admin:
        flash('Sie können nur Ihre eigenen Buchungen löschen.', 'error')
        return redirect(url_for('meine_buchungen'))
    
    # Prüfe ob Löschen noch möglich ist (außer Admin)
    if not is_admin:
        can_modify, modify_reason = can_modify_booking(booking['date'], booking['period'])
        if not can_modify:
            flash(f'Diese Buchung kann nicht mehr gelöscht werden: {modify_reason}', 'error')
            return redirect(url_for('meine_buchungen'))
    
    # Lösche Buchung
    if delete_booking(booking_id):
        flash('Buchung erfolgreich gelöscht.', 'success')
    else:
        flash('Buchung konnte nicht gelöscht werden.', 'error')
    
    return redirect(url_for('meine_buchungen'))

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
            'student_count': len(students),
            'notes': booking_dict.get('notes')
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
        
        # Hole optionale Notizen (Admin-Buchungen)
        notes = request.form.get('notes', '').strip()
        
        booking_id = create_booking(
            date=date_str,
            weekday=weekday,
            period=period,
            teacher_id=teacher_id,
            students=students,
            offer_type=period_info['type'],
            offer_label=offer_label,
            teacher_name=teacher_name,
            teacher_class=teacher_class,
            notes=notes if notes else None
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
        
        # Hole optionale Notizen (Admin kann Notizen bearbeiten)
        notes = request.form.get('notes', '').strip()
        
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
            teacher_class=teacher_class,
            notes=notes if notes else None
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
    
    # Lösche Buchung
    if delete_booking(booking_id):
        flash('Buchung erfolgreich gelöscht.', 'success')
    else:
        flash('Buchung konnte nicht gelöscht werden.', 'error')
    
    return redirect(url_for('admin'))

# Route: Slots verwalten (nur Admin)
@app.route('/admin/manage_slots', methods=['GET', 'POST'])
@admin_required
def manage_slots():
    """Admin kann feste Slot-Namen umbenennen"""
    from models import update_slot_name
    
    if request.method == 'POST':
        weekday = request.form.get('weekday')
        period_str = request.form.get('period')
        period = int(period_str) if period_str else 0
        label = request.form.get('label', '').strip()
        
        if weekday and period and label:
            if update_slot_name(weekday, period, label):
                flash(f'Slot-Name erfolgreich aktualisiert!', 'success')
            else:
                flash('Fehler beim Aktualisieren des Slot-Namens.', 'error')
        else:
            flash('Bitte füllen Sie alle Felder aus.', 'error')
        
        return redirect(url_for('manage_slots'))
    
    fixed_slots = []
    weekdays = {
        'Mon': 'Montag',
        'Tue': 'Dienstag', 
        'Wed': 'Mittwoch',
        'Thu': 'Donnerstag',
        'Fri': 'Freitag'
    }
    
    for weekday_code, weekday_name in weekdays.items():
        if weekday_code in FIXED_OFFERS:
            for period, default_label in FIXED_OFFERS[weekday_code].items():
                period_info = get_period_info(weekday_code, period)
                fixed_slots.append({
                    'weekday_code': weekday_code,
                    'weekday_name': weekday_name,
                    'period': period,
                    'period_time': f"{PERIOD_TIMES[period]['start']} - {PERIOD_TIMES[period]['end']}",
                    'default_label': default_label,
                    'current_label': period_info['label']
                })
    
    return render_template('admin_manage_slots.html', 
                         fixed_slots=fixed_slots)

@app.route('/admin/block_slot', methods=['POST'])
@admin_required
def admin_block_slot():
    """Admin blockiert einen Slot für Beratungsgespräche"""
    from models import block_slot, is_slot_blocked
    
    # CSRF-Token Validierung
    csrf_token = request.form.get('csrf_token', '')
    if not validate_csrf_token(csrf_token):
        flash('Ungültiges Sicherheits-Token. Bitte versuchen Sie es erneut.', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    
    date_str = request.form.get('date', '').strip()
    period = request.form.get('period', type=int)
    reason = request.form.get('reason', 'Beratung').strip()
    icon = request.form.get('icon', '🔧').strip()
    
    # Validiere Grund-Länge
    if reason and len(reason) > 200:
        reason = reason[:200]
    
    # Validiere Icon
    allowed_icons = ['🔧', '💬', '📚', '🏖️', '🎉', '⚠️']
    if icon not in allowed_icons:
        icon = '🔧'
    
    if not date_str or not period:
        flash('Ungültige Slot-Daten.', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    
    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        weekday = booking_date.strftime('%a')
    except:
        flash('Ungültiges Datum.', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    
    if is_slot_blocked(date_str, period):
        flash('Dieser Slot ist bereits blockiert.', 'warning')
    else:
        admin_id = session.get('user_id')
        if block_slot(date_str, weekday, period, admin_id, reason, icon):
            flash(f'Slot erfolgreich für {reason} blockiert.', 'success')
        else:
            flash('Fehler beim Blockieren des Slots.', 'error')
    
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/admin/unblock_slot', methods=['POST'])
@admin_required
def admin_unblock_slot():
    """Admin gibt einen blockierten Slot wieder frei"""
    from models import unblock_slot
    
    # CSRF-Token Validierung
    csrf_token = request.form.get('csrf_token', '')
    if not validate_csrf_token(csrf_token):
        flash('Ungültiges Sicherheits-Token. Bitte versuchen Sie es erneut.', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    
    date_str = request.form.get('date', '').strip()
    period = request.form.get('period', type=int)
    
    if not date_str or not period:
        flash('Ungültige Slot-Daten.', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    
    if unblock_slot(date_str, period):
        flash('Slot erfolgreich freigegeben.', 'success')
    else:
        flash('Fehler beim Freigeben des Slots.', 'error')
    
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/admin/bulk_block', methods=['GET', 'POST'])
@admin_required
def admin_bulk_block():
    """Admin kann mehrere Slots auf einmal sperren (z.B. für Ferien)"""
    from models import bulk_block_slots, bulk_unblock_slots, get_all_blocked_slots
    
    blocked_slots = get_all_blocked_slots()
    
    if request.method == 'POST':
        # CSRF-Token Validierung
        csrf_token = request.form.get('csrf_token', '')
        if not validate_csrf_token(csrf_token):
            flash('Ungültiges Sicherheits-Token. Bitte versuchen Sie es erneut.', 'error')
            return redirect(url_for('admin_bulk_block'))
        
        action = request.form.get('action', 'block')
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()
        reason = request.form.get('reason', 'Ferien').strip()
        
        # Stunden auswählen (Checkboxen)
        periods = request.form.getlist('periods', type=int)
        if not periods:
            periods = None  # Alle Stunden
        
        # Validierung
        if not start_date or not end_date:
            flash('Bitte Start- und Enddatum angeben.', 'error')
            return redirect(url_for('admin_bulk_block'))
        
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            if start > end:
                flash('Startdatum muss vor dem Enddatum liegen.', 'error')
                return redirect(url_for('admin_bulk_block'))
        except:
            flash('Ungültiges Datumsformat.', 'error')
            return redirect(url_for('admin_bulk_block'))
        
        admin_id = session.get('user_id')
        
        if action == 'block':
            result = bulk_block_slots(start_date, end_date, admin_id, reason, periods)
            if result['success']:
                flash(f"✅ {result['blocked_count']} Slots erfolgreich gesperrt ({result['skipped_count']} bereits gesperrt übersprungen).", 'success')
            else:
                flash(f"Fehler beim Sperren: {result.get('error', 'Unbekannter Fehler')}", 'error')
        elif action == 'unblock':
            result = bulk_unblock_slots(start_date, end_date, periods)
            if result['success']:
                flash(f"✅ {result['unblocked_count']} Slots erfolgreich freigegeben.", 'success')
            else:
                flash(f"Fehler beim Freigeben: {result.get('error', 'Unbekannter Fehler')}", 'error')
        
        return redirect(url_for('admin_bulk_block'))
    
    return render_template('admin_bulk_block.html', blocked_slots=blocked_slots)

# ============================================================================
# Notifications & Server-Sent Events (SSE) Routes
# ============================================================================

# SSE deaktiviert - verursacht Worker-Timeouts in Produktion mit Gunicorn
# @app.route('/notifications/stream')
# @admin_required
# def notifications_stream():
#     """SSE-Endpunkt für Echtzeit-Benachrichtigungen (nur für Admins)"""
#     def event_stream():
#         """Generator für Server-Sent Events"""
#         q = queue.Queue(maxsize=50)
#         
#         with subscribers_lock:
#             notification_subscribers.append(q)
#         
#         try:
#             while True:
#                 try:
#                     message = q.get(timeout=30)
#                     yield f"data: {json.dumps(message)}\n\n"
#                 except queue.Empty:
#                     yield f"data: {json.dumps({'type': 'ping'})}\n\n"
#         finally:
#             with subscribers_lock:
#                 if q in notification_subscribers:
#                     notification_subscribers.remove(q)
#     
#     return Response(event_stream(), mimetype='text/event-stream')

@app.route('/api/notifications/recent', methods=['GET'])
@admin_required
def api_get_recent_notifications():
    """Holt die neuesten Benachrichtigungen"""
    limit = request.args.get('limit', 10, type=int)
    limit = min(limit, 50)
    
    notifications = get_recent_notifications(recipient_role='admin', limit=limit)
    return jsonify({
        'success': True,
        'notifications': notifications
    })

@app.route('/api/notifications/unread_count', methods=['GET'])
@admin_required
def api_get_unread_count():
    """Holt die Anzahl der ungelesenen Benachrichtigungen"""
    count = get_unread_notification_count(recipient_role='admin')
    return jsonify({
        'success': True,
        'count': count
    })

@app.route('/api/notifications/<int:notification_id>/mark_read', methods=['POST'])
@admin_required
def api_mark_notification_read(notification_id):
    """Markiert eine Benachrichtigung als gelesen"""
    csrf_token = request.json.get('csrf_token', '') if request.json else ''
    if not validate_csrf_token(csrf_token):
        return jsonify({
            'success': False,
            'error': 'Invalid CSRF token'
        }), 403
    
    success = mark_notification_as_read(notification_id)
    return jsonify({
        'success': success
    })

@app.route('/api/notifications/mark_all_read', methods=['POST'])
@admin_required
def api_mark_all_notifications_read():
    """Markiert alle Benachrichtigungen als gelesen"""
    csrf_token = request.json.get('csrf_token', '') if request.json else ''
    if not validate_csrf_token(csrf_token):
        return jsonify({
            'success': False,
            'error': 'Invalid CSRF token'
        }), 403
    
    success = mark_all_notifications_as_read(recipient_role='admin')
    return jsonify({
        'success': success
    })

# Error-Handler für Production mit Fallback
@app.errorhandler(404)
def not_found_error(error):
    """Handler für 404 Not Found Fehler"""
    try:
        return render_template('errors/404.html'), 404
    except Exception:
        return '<h1>404 - Seite nicht gefunden</h1><p><a href="/">Zur Startseite</a></p>', 404

@app.errorhandler(500)
def internal_error(error):
    """Handler für 500 Internal Server Error"""
    try:
        db.session.rollback()
    except Exception:
        pass
    try:
        return render_template('errors/500.html'), 500
    except Exception:
        return '<h1>500 - Interner Serverfehler</h1><p>Bitte versuchen Sie es später erneut.</p>', 500

@app.errorhandler(403)
def forbidden_error(error):
    """Handler für 403 Forbidden Fehler"""
    try:
        return render_template('errors/403.html'), 403
    except Exception:
        return '<h1>403 - Zugriff verweigert</h1><p><a href="/">Zur Startseite</a></p>', 403

# Logging-Konfiguration für Production
import logging
from logging.handlers import RotatingFileHandler
import os

if os.environ.get('FLASK_ENV') == 'production' or not os.environ.get('FLASK_DEBUG'):
    if not os.path.exists('logs'):
        try:
            os.mkdir('logs')
        except OSError:
            pass
    
    try:
        file_handler = RotatingFileHandler('logs/sportoase.log', maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('SportOase Buchungssystem gestartet (Production Mode)')
    except Exception as e:
        print(f"Fehler beim Einrichten des Logging-Handlers: {e}")

if __name__ == '__main__':
    # Starte die Anwendung
    app.run(host='0.0.0.0', port=5000, debug=True)
