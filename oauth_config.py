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
    Bestimmt die Rolle des Benutzers basierend auf IServ-Gruppen und Rollen
    
    Nur Benutzer mit diesen Rollen/Gruppen haben Zugang:
    - Administrator → admin
    - Lehrer → teacher
    - Mitarbeitende → teacher
    
    Args:
        userinfo: Dictionary mit Benutzerdaten von IServ
    
    Returns:
        'admin', 'teacher' oder None (kein Zugang)
    """
    email = userinfo.get('email', '').lower().strip()
    
    # Log für Debugging - zeige alle UserInfo-Daten
    print(f"🔍 Bestimme Rolle für: {email}")
    print(f"   Komplette UserInfo: {userinfo}")
    
    # Sammle alle Gruppen- und Rollennamen aus verschiedenen möglichen Feldern
    all_names = []
    
    # Prüfe 'groups' Feld
    groups = userinfo.get('groups', [])
    print(f"   groups: {groups}")
    all_names.extend(extract_names(groups))
    
    # Prüfe 'roles' Feld (IServ könnte Rollen separat senden)
    roles = userinfo.get('roles', [])
    print(f"   roles: {roles}")
    all_names.extend(extract_names(roles))
    
    # Prüfe 'role' Feld (einzelne Rolle)
    role = userinfo.get('role', '')
    if role:
        all_names.append(role)
    
    # Prüfe 'memberOf' Feld (LDAP-Style)
    member_of = userinfo.get('memberOf', [])
    all_names.extend(extract_names(member_of))
    
    # Lowercase für Vergleich
    all_names_lower = [n.lower() for n in all_names if n]
    print(f"   Alle gefundenen Namen (lowercase): {all_names_lower}")
    
    # Admin-E-Mail hat immer Zugang (Fallback für morelli.maurizio@kgs-pattensen.de)
    if is_admin_email(email):
        print(f"   → Admin (E-Mail-Fallback)")
        return 'admin'
    
    # Administrator-Gruppe hat Admin-Rechte (case-insensitive)
    if 'administrator' in all_names_lower or 'administratoren' in all_names_lower:
        print(f"   → Admin (Gruppen-Match: Administrator)")
        return 'admin'
    
    # Lehrer und Mitarbeitende haben Teacher-Rechte (case-insensitive)
    if 'lehrer' in all_names_lower or 'mitarbeitende' in all_names_lower:
        print(f"   → Teacher (Gruppen-Match)")
        return 'teacher'
    
    # Kein Zugang für andere Benutzer (z.B. Schüler)
    print(f"   → KEIN ZUGANG (keine berechtigte Gruppe)")
    return None


def extract_names(data):
    """Extrahiert Namen aus verschiedenen Datenformaten"""
    names = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Format: [{name: "...", id: "..."}]
                if 'name' in item:
                    names.append(item['name'])
                if 'Name' in item:
                    names.append(item['Name'])
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
            elif isinstance(value, str):
                names.append(value)
        # Falls 'name' direkt im Dict ist
        if 'name' in data:
            names.append(data['name'])
    return names
