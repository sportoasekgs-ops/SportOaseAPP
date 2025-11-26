# IServ OAuth2/OpenID Connect Konfiguration für SportOase
# Diese Datei konfiguriert die SSO-Integration mit IServ

import os
from authlib.integrations.flask_client import OAuth


def init_oauth(app):
    """Initialisiert OAuth2 mit IServ-Konfiguration"""
    oauth = OAuth(app)

    # IServ-Instanz-Domain aus Umgebungsvariablen
    iserv_domain = os.environ.get('ISERV_DOMAIN', 'kgs-pattensen.de')
    iserv_base_url = f'https://{iserv_domain}'

    # Registriere IServ als OAuth-Provider
    # Scopes: openid, profile, email, groups, roles für Rollen-Erkennung
    # IServ liefert Gruppeninformationen je nach Konfiguration in groups oder roles
    iserv = oauth.register(
        name='iserv',
        client_id=os.environ.get('ISERV_CLIENT_ID'),
        client_secret=os.environ.get('ISERV_CLIENT_SECRET'),
        server_metadata_url=
        f'{iserv_base_url}/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid profile email groups roles'})

    return oauth, iserv


def get_admin_email():
    """Gibt die E-Mail-Adresse des Admin-Benutzers zurück"""
    return 'morelli.maurizio@kgs-pattensen.de'


def is_admin_email(email):
    """Prüft, ob die E-Mail-Adresse dem Admin gehört"""
    return email and email.lower().strip() == get_admin_email().lower()


def check_user_authorization(userinfo):
    """
    Prüft ob der Benutzer berechtigt ist (Lehrer/Mitarbeiter) oder 
    blockiert werden muss (Schüler).
    
    Verwendet einen WHITELIST-Ansatz: Nur bekannte Lehrer-Gruppen haben Zugang.
    Falls keine Gruppeninfo vorhanden ist, wird der Zugang verweigert.
    
    Args:
        userinfo: Dictionary mit Benutzerdaten von IServ
    
    Returns:
        Tuple (is_authorized: bool, reason: str)
    """
    # PRIMÄR: Extrahiere Mitgliedschaften aus roles/groups Feldern (für IServ)
    membership_names = collect_membership_names(userinfo)
    
    # SEKUNDÄR: Extrahiere alle Texte als Fallback
    all_texts = extract_all_text(userinfo)
    all_texts_lower = [
        t.lower().strip() for t in all_texts if isinstance(t, str)
    ]
    
    # Kombiniere beide Listen für vollständige Prüfung
    all_texts_lower = list(set(membership_names + all_texts_lower))

    print(f"   📋 Extrahierte Texte: {all_texts_lower[:20]}..."
          )  # Erste 20 für Debug

    # ===== SCHÜLER-BLACKLIST (werden IMMER blockiert) =====
    student_keywords = [
        'schüler',
        'schueler',
        'schülerin',
        'schuelerin',
        'schülerinnen',
        'schuelerinnen',
        # Oberstufe
        'ef',
        'q1',
        'q2',
        'einführungsphase',
        'qualifikationsphase',
        '11a',
        '11b',
        '11c',
        '11d',
        '11e',
        '11f',
        '12a',
        '12b',
        '12c',
        '12d',
        '12e',
        '12f',
        '13a',
        '13b',
        '13c',
        '13d',
        '13e',
        '13f',
        # Mittelstufe
        '5a',
        '5b',
        '5c',
        '5d',
        '5e',
        '5f',
        '5g',
        '5h',
        '6a',
        '6b',
        '6c',
        '6d',
        '6e',
        '6f',
        '6g',
        '6h',
        '7a',
        '7b',
        '7c',
        '7d',
        '7e',
        '7f',
        '7g',
        '7h',
        '8a',
        '8b',
        '8c',
        '8d',
        '8e',
        '8f',
        '8g',
        '8h',
        '9a',
        '9b',
        '9c',
        '9d',
        '9e',
        '9f',
        '9g',
        '9h',
        '10a',
        '10b',
        '10c',
        '10d',
        '10e',
        '10f',
        '10g',
        '10h',
    ]

    # Hilfsfunktion: Prüft ob ein String eine UUID ist (Format: 8-4-4-4-12)
    import re
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    
    # Prüfe auf Schüler-Schlüsselwörter
    for text in all_texts_lower:
        # Überspringe UUIDs - diese können zufällig Klassennamen enthalten (z.B. "5ca49ea7..." beginnt mit "5c")
        if uuid_pattern.match(text):
            continue
            
        # Überspringe reine Zahlen (IDs wie 10290, 12432)
        if text.isdigit():
            continue
            
        for keyword in student_keywords:
            # Exakte Übereinstimmung oder als eigenes Wort (nicht Teil eines anderen Wortes)
            if text == keyword or f' {keyword}' in f' {text} ' or text.startswith(
                    keyword + ' ') or text.endswith(' ' + keyword):
                # Ausnahme: "schüler" als Teil von "schülerberatung" etc. für Lehrer
                if keyword in ['schüler', 'schueler'] and any(
                        x in text for x in
                    ['beratung', 'vertretung', 'sprecher', 'koordinat']):
                    continue
                print(f"   ⛔ SCHÜLER erkannt: '{text}' enthält '{keyword}'")
                return False, f"Schüler-Gruppe erkannt: {keyword}"

    # ===== LEHRER-WHITELIST (explizit erlaubt) =====
    teacher_keywords = [
        'lehrer',
        'lehrerin',
        'lehrkraft',
        'lehrkräfte',
        'kollegium',
        'mitarbeiter',
        'mitarbeitende',
        'pädagogisch',
        'paedagogisch',
        'pädagogische',
        'paedagogische',
        'sekretariat',
        'verwaltung',
        'schulleitung',
        'leitung',
        'direktor',
        'direktion',
        'referendar',
        'praktikant',
        'fsj',
        'bufdi',
        'bundesfreiwilligendienst',
        'sozialpädagog',
        'sozialpaedagog',
        'sozialpädagogin',
        'sozialarbeit',
        'schulassist',
        'integrationshelfer',
        'administrator',
        'admin',
        'pädagogische mitarbeiter',
        'paedagogische mitarbeiter',
        'päd. mitarbeiter',
        'päd mitarbeiter',
        'pm',
        'beratung',
        'fairplaycoach',
        'fairplay',
        'coach',
    ]

    # Prüfe auf Lehrer-Schlüsselwörter
    is_teacher = False
    teacher_group_found = None
    for text in all_texts_lower:
        for keyword in teacher_keywords:
            if keyword in text:
                print(
                    f"   ✅ LEHRER-Gruppe erkannt: '{text}' enthält '{keyword}'"
                )
                is_teacher = True
                teacher_group_found = text
                break
        if is_teacher:
            break

    if is_teacher:
        return True, f"Lehrer-Gruppe: {teacher_group_found}"

    # ===== FALLBACK: Keine eindeutige Gruppe gefunden =====
    # Wenn keine Gruppeninfo vorhanden ist, Zugang verweigern (sicherer Ansatz)
    # Prüfe ob überhaupt Gruppen-bezogene Daten vorhanden sind
    has_group_data = any(
        key in userinfo
        for key in ['groups', 'roles', 'group', 'role', 'memberOf'])

    if not has_group_data:
        print(f"   ⚠️ KEINE Gruppeninformationen in userinfo gefunden!")
        print(f"   ⚠️ Verfügbare Keys: {list(userinfo.keys())}")
        # Wenn keine Gruppeninfo, verweigern wir den Zugang zur Sicherheit
        return False, "Keine Gruppeninformationen verfügbar - Zugang verweigert"

    # Gruppeninfo vorhanden, aber weder Lehrer noch Schüler erkannt
    print(f"   ⚠️ Weder Lehrer- noch Schüler-Gruppe eindeutig erkannt")
    return False, "Keine autorisierte Gruppe erkannt"


def determine_user_role(userinfo):
    """
    Bestimmt die Rolle des Benutzers MIT robuster Schüler-Blockierung
    
    Regelwerk:
    1. Admin-E-Mail → admin (immer erlaubt)
    2. Schüler-Gruppe erkannt → KEIN ZUGANG
    3. Lehrer-Gruppe erkannt → teacher
    4. Keine Gruppeninfo → KEIN ZUGANG (sicherheitshalber)
    
    Args:
        userinfo: Dictionary mit Benutzerdaten von IServ
    
    Returns:
        'admin', 'teacher' oder None (kein Zugang)
    """
    email = userinfo.get('email', '').lower().strip()

    # Log für Debugging
    print(f"🔍 Bestimme Rolle für: {email}")
    print(f"   UserInfo Keys: {list(userinfo.keys())}")

    # 1. Admin-E-Mail hat immer Admin-Zugang (wird nie blockiert)
    if is_admin_email(email):
        print(f"   → Admin (morelli.maurizio@kgs-pattensen.de)")
        return 'admin'

    # Prüfe E-Mail-Domain
    if not email.endswith('@kgs-pattensen.de'):
        print(f"   → KEIN ZUGANG (keine @kgs-pattensen.de E-Mail)")
        return None

    # 2. Prüfe Autorisierung (Schüler/Lehrer-Erkennung)
    is_authorized, reason = check_user_authorization(userinfo)

    if is_authorized:
        print(f"   → Teacher ({reason})")
        return 'teacher'
    else:
        print(f"   → KEIN ZUGANG ({reason})")
        return None


def collect_membership_names(userinfo):
    """
    Extrahiert ALLE Gruppen- und Rollennamen aus IServ userinfo.
    Speziell für IServ-Format: Durchsucht roles, roleAssignments, groups, memberOf
    und extrahiert displayName/name Felder aus verschachtelten Objekten.
    
    Args:
        userinfo: Dictionary mit Benutzerdaten von IServ
    
    Returns:
        Liste von normalisierten Gruppennamen (lowercase)
    """
    membership_names = []
    
    # Felder, die Gruppeninformationen enthalten können
    membership_fields = ['roles', 'roleAssignments', 'groups', 'memberOf', 'group', 'role']
    
    for field in membership_fields:
        if field not in userinfo:
            continue
            
        data = userinfo[field]
        
        # Wenn es ein String ist, direkt hinzufügen
        if isinstance(data, str):
            membership_names.append(data.lower().strip())
            
        # Wenn es eine Liste ist
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    membership_names.append(item.lower().strip())
                elif isinstance(item, dict):
                    # IServ liefert oft {displayName: "...", name: "...", id: "..."}
                    for name_field in ['displayName', 'display_name', 'name', 'title', 'label']:
                        if name_field in item and isinstance(item[name_field], str):
                            membership_names.append(item[name_field].lower().strip())
                            
        # Wenn es ein Dictionary ist
        elif isinstance(data, dict):
            for name_field in ['displayName', 'display_name', 'name', 'title', 'label']:
                if name_field in data and isinstance(data[name_field], str):
                    membership_names.append(data[name_field].lower().strip())
    
    # Debug-Ausgabe
    print(f"   🏷️ Extrahierte Mitgliedschaften: {membership_names}")
    
    return membership_names


def extract_all_text(data):
    """
    Extrahiert ALLE Textwerte aus beliebigen Datenstrukturen.
    Rekursiv für verschachtelte Strukturen.
    """
    texts = []

    if isinstance(data, str):
        texts.append(data)
    elif isinstance(data, list):
        for item in data:
            texts.extend(extract_all_text(item))
    elif isinstance(data, dict):
        # Extrahiere alle String-Werte aus dem Dictionary
        for key, value in data.items():
            # Key selbst könnte relevant sein (z.B. Gruppenname als Key)
            if isinstance(key, str):
                texts.append(key)
            # Wert rekursiv extrahieren
            texts.extend(extract_all_text(value))

    return texts


def extract_names(data):
    """Extrahiert Namen aus verschiedenen Datenformaten"""
    names = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Format: [{name: "...", displayName: "...", id: "..."}]
                if 'name' in item:
                    names.append(item['name'])
                if 'Name' in item:
                    names.append(item['Name'])
                if 'displayName' in item:
                    names.append(item['displayName'])
            elif isinstance(item, str):
                names.append(item)
    elif isinstance(data, str):
        names.append(data)
    elif isinstance(data, dict):
        # IServ-Format: {'2124': {'id': 2124, 'name': 'Lehrer'}, ...}
        # Durchlaufe alle Werte im Dictionary
        for key, value in data.items():
            if isinstance(value, dict):
                if 'name' in value:
                    names.append(value['name'])
                if 'Name' in value:
                    names.append(value['Name'])
                if 'displayName' in value:
                    names.append(value['displayName'])
            elif isinstance(value, str):
                names.append(value)
        # Falls 'name' oder 'displayName' direkt im Dict ist
        if 'name' in data:
            names.append(data['name'])
        if 'displayName' in data:
            names.append(data['displayName'])
    return names
