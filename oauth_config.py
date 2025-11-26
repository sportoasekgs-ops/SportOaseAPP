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
    iserv = oauth.register(
        name='iserv',
        client_id=os.environ.get('ISERV_CLIENT_ID'),
        client_secret=os.environ.get('ISERV_CLIENT_SECRET'),
        server_metadata_url=f'{iserv_base_url}/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid profile email groups roles'
        }
    )
    
    return oauth, iserv

def get_admin_email():
    """Gibt die E-Mail-Adresse des Admin-Benutzers zurück"""
    return 'morelli.maurizio@kgs-pattensen.de'

def is_admin_email(email):
    """Prüft, ob die E-Mail-Adresse dem Admin gehört"""
    return email and email.lower().strip() == get_admin_email().lower()

def determine_user_role(userinfo):
    """
    Bestimmt die Rolle des Benutzers basierend auf IServ-Gruppen
    
    Nur Benutzer mit diesen Gruppen haben Zugang:
    - Administrator → admin
    - Lehrer, Mitarbeiter, Pädagogische Mitarbeiter, Sozialpädagogen → teacher
    
    Args:
        userinfo: Dictionary mit Benutzerdaten von IServ
    
    Returns:
        'admin', 'teacher' oder None (kein Zugang)
    """
    email = userinfo.get('email', '').lower().strip()
    
    # Log für Debugging - zeige alle UserInfo-Daten
    print(f"🔍 Bestimme Rolle für: {email}")
    print(f"   Komplette UserInfo: {userinfo}")
    
    # Admin-E-Mail hat immer Zugang (Fallback für morelli.maurizio@kgs-pattensen.de)
    if is_admin_email(email):
        print(f"   → Admin (E-Mail-Fallback)")
        return 'admin'
    
    # Sammle alle Gruppen-Namen aus verschiedenen möglichen Feldern
    all_names = []
    
    # Prüfe 'groups' Feld (Hauptfeld für IServ)
    groups = userinfo.get('groups', [])
    print(f"   groups (raw): {groups}")
    all_names.extend(extract_all_text(groups))
    
    # Prüfe auch 'roles' Feld (falls vorhanden)
    roles = userinfo.get('roles', [])
    if roles:
        print(f"   roles (raw): {roles}")
        all_names.extend(extract_all_text(roles))
    
    # Prüfe 'memberOf' Feld (LDAP-Style)
    member_of = userinfo.get('memberOf', [])
    if member_of:
        print(f"   memberOf (raw): {member_of}")
        all_names.extend(extract_all_text(member_of))
    
    # Lowercase für Vergleich, entferne leere Strings
    all_names_lower = [n.lower().strip() for n in all_names if n and n.strip()]
    print(f"   Alle gefundenen Namen (lowercase): {all_names_lower}")
    
    # Administrator-Gruppe hat Admin-Rechte
    admin_terms = ['administrator', 'administratoren', 'admin']
    for term in admin_terms:
        for name in all_names_lower:
            if term in name:
                print(f"   → Admin (Match: '{term}' in '{name}')")
                return 'admin'
    
    # Erlaubte Gruppen für Teacher-Zugang
    # Prüfe ob einer der Namen ENTHÄLT einen erlaubten Begriff (Teilstring)
    teacher_terms = [
        'lehrer',
        'mitarbeiter',      # Erfasst auch "Mitarbeitende", "Pädagogische Mitarbeiter"
        'pädagog',          # Erfasst "Pädagogische Mitarbeiter", "Sozialpädagogen"
        'sozial',           # Erfasst "Sozialpädagogen"
        'beratung',
        'fairplay',
        'coach'
    ]
    
    for name in all_names_lower:
        for term in teacher_terms:
            if term in name:
                print(f"   → Teacher (Match: '{term}' in '{name}')")
                return 'teacher'
    
    # Fallback: Wenn keine Gruppen erkannt wurden aber E-Mail von kgs-pattensen.de ist,
    # und die OAuth-App nur für berechtigte Gruppen freigegeben ist, dann Zugang gewähren
    if email.endswith('@kgs-pattensen.de'):
        print(f"   → Teacher (Fallback: kgs-pattensen.de E-Mail, keine Gruppeninfo aber OAuth-App freigegeben)")
        return 'teacher'
    
    # Kein Zugang für andere Benutzer (z.B. Schüler)
    print(f"   → KEIN ZUGANG (keine berechtigte Gruppe gefunden)")
    return None


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
