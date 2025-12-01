# IServ OAuth2/OpenID Connect Konfiguration für SportOase
# Diese Datei konfiguriert die SSO-Integration mit IServ
# VEREINFACHT: Fokus auf ROLLEN statt Gruppen

import os
import json
from authlib.integrations.flask_client import OAuth


def init_oauth(app):
    """Initialisiert OAuth2 mit IServ-Konfiguration"""
    oauth = OAuth(app)

    # IServ-Instanz-Domain aus Umgebungsvariablen
    iserv_domain = os.environ.get('ISERV_DOMAIN', 'kgs-pattensen.de')
    iserv_base_url = f'https://{iserv_domain}'

    # Registriere IServ als OAuth-Provider
    # Scopes: openid, profile, email, roles für Rollen-Erkennung
    iserv = oauth.register(
        name='iserv',
        client_id=os.environ.get('ISERV_CLIENT_ID'),
        client_secret=os.environ.get('ISERV_CLIENT_SECRET'),
        server_metadata_url=f'{iserv_base_url}/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid profile email roles'})

    return oauth, iserv


def get_admin_email():
    """Gibt die E-Mail-Adresse des Admin-Benutzers zurück"""
    return 'morelli.maurizio@kgs-pattensen.de'


def is_admin_email(email):
    """Prüft, ob die E-Mail-Adresse dem Admin gehört"""
    return email and email.lower().strip() == get_admin_email().lower()


def extract_roles_from_userinfo(userinfo):
    """
    Extrahiert Rollennamen aus IServ userinfo.
    
    IServ-Format laut Dokumentation (Scope: roles):
    {
        "roles": [
            {"uuid": "...", "id": 123, "name": "Lehrer"},
            {"uuid": "...", "id": 456, "name": "Mitarbeiter"}
        ]
    }
    
    Gibt eine Liste von Rollennamen zurück (lowercase).
    """
    roles = []
    
    # IServ liefert Rollen im Feld "roles" als Liste von Objekten
    if 'roles' in userinfo:
        roles_data = userinfo['roles']
        
        if isinstance(roles_data, list):
            for role_item in roles_data:
                if isinstance(role_item, dict):
                    # IServ-Format: {"uuid": "...", "id": 123, "name": "Lehrer"}
                    if 'name' in role_item and isinstance(role_item['name'], str):
                        roles.append(role_item['name'].lower().strip())
                elif isinstance(role_item, str):
                    # Fallback: direkter String
                    roles.append(role_item.lower().strip())
    
    # Entferne Duplikate und leere Strings
    return list(set(r for r in roles if r))


def determine_user_role(userinfo):
    """
    Bestimmt die Rolle des Benutzers basierend auf IServ-ROLLEN.
    
    VEREINFACHTES Regelwerk:
    1. Admin-E-Mail → admin (immer erlaubt)
    2. Rolle "Lehrer" oder "Mitarbeiter" → teacher
    3. Rolle "Schüler" → KEIN ZUGANG
    4. Keine passende Rolle → KEIN ZUGANG
    
    Args:
        userinfo: Dictionary mit Benutzerdaten von IServ
    
    Returns:
        Tuple: (role, iserv_role) wobei:
        - role: 'admin', 'teacher' oder None (kein Zugang)
        - iserv_role: Die erkannte IServ-Rolle
    """
    email = userinfo.get('email', '').lower().strip()

    # === AUSFÜHRLICHES LOGGING ===
    print("=" * 60)
    print(f"🔐 IServ Login-Versuch")
    print(f"   E-Mail: {email}")
    print(f"   UserInfo Keys: {list(userinfo.keys())}")
    
    # Logge die komplette userinfo für Debugging
    print(f"   📋 Komplette UserInfo:")
    for key, value in userinfo.items():
        # Kürze lange Werte
        value_str = str(value)
        if len(value_str) > 200:
            value_str = value_str[:200] + "..."
        print(f"      {key}: {value_str}")
    
    # Extrahiere Rollen
    roles = extract_roles_from_userinfo(userinfo)
    print(f"   🏷️ Extrahierte Rollen: {roles}")
    print("=" * 60)

    # 1. Admin-E-Mail hat immer Admin-Zugang
    if is_admin_email(email):
        print(f"   ✅ Admin erkannt (E-Mail-Match)")
        return 'admin', 'Administrator'

    # Prüfe E-Mail-Domain
    if not email.endswith('@kgs-pattensen.de'):
        print(f"   ❌ KEIN ZUGANG - Keine @kgs-pattensen.de E-Mail")
        return None, None

    # 2. Prüfe auf erlaubte Rollen
    # NUR diese Rollen haben Zugang (nach Kundenwunsch):
    # - Schulleitung
    # - Lehrer
    # - Sozialpädagogen
    # - Pädagogische Mitarbeiter
    # - Mitarbeiter
    allowed_role_keywords = [
        'schulleitung',
        'lehrer',
        'lehrerin',
        'sozialpädagog',
        'sozialpaedagog',
        'sozialpädagogin',
        'pädagogische mitarbeiter',
        'paedagogische mitarbeiter',
        'pädagogischer mitarbeiter',
        'mitarbeiter',
        'mitarbeiterin',
    ]
    
    # Schüler werden blockiert
    blocked_role_keywords = [
        'schüler',
        'schueler',
        'schülerin',
        'schuelerin',
    ]
    
    # Zuerst prüfen ob Schüler-Rolle vorhanden
    for role in roles:
        for blocked in blocked_role_keywords:
            if blocked in role:
                print(f"   ❌ KEIN ZUGANG - Schüler-Rolle erkannt: '{role}'")
                return None, None
    
    # Dann prüfen ob erlaubte Rolle vorhanden
    for role in roles:
        for allowed in allowed_role_keywords:
            if allowed in role:
                print(f"   ✅ Zugang gewährt - Rolle erkannt: '{role}'")
                return 'teacher', role.title()
    
    # Keine passende Rolle gefunden
    if roles:
        print(f"   ❌ KEIN ZUGANG - Keine erlaubte Rolle gefunden")
        print(f"   ℹ️ Gefundene Rollen: {roles}")
        print(f"   ℹ️ Erlaubte Rollen-Keywords: {allowed_role_keywords}")
    else:
        print(f"   ❌ KEIN ZUGANG - Keine Rollen in userinfo gefunden")
    
    return None, None
