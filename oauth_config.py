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
            'scope': 'openid profile email groups'
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
    Bestimmt die Rolle des Benutzers basierend auf IServ-Gruppen oder E-Mail
    
    Args:
        userinfo: Dictionary mit Benutzerdaten von IServ (email, name, groups, etc.)
    
    Returns:
        'admin' oder 'teacher'
    """
    email = userinfo.get('email', '').lower().strip()
    
    # Log für Debugging
    print(f"🔍 Bestimme Rolle für: {email}")
    
    # Prüfe IServ-Gruppen (falls vorhanden)
    groups = userinfo.get('groups', [])
    print(f"   Gruppen: {groups}")
    
    # Extrahiere Gruppennamen (IServ gibt [{name: "...", id: "..."}] zurück)
    group_names = []
    if isinstance(groups, list):
        for g in groups:
            if isinstance(g, dict):
                group_names.append(g.get('name', ''))
            elif isinstance(g, str):
                group_names.append(g)
    elif isinstance(groups, str):
        group_names = [groups]
    
    print(f"   Gruppennamen: {group_names}")
    
    # Administrator-Gruppe hat Admin-Rechte
    if 'Administrator' in group_names or 'Administratoren' in group_names:
        print(f"   → Admin (Gruppen-Match: Administrator)")
        return 'admin'
    
    # Lehrer und Mitarbeitende haben Teacher-Rechte
    if 'Lehrer' in group_names or 'Mitarbeitende' in group_names:
        print(f"   → Teacher (Gruppen-Match)")
        return 'teacher'
    
    # Fallback zu E-Mail-Check für morelli.maurizio@kgs-pattensen.de
    if is_admin_email(email):
        print(f"   → Admin (E-Mail-Fallback)")
        return 'admin'
    
    # Alle Benutzer mit @kgs-pattensen.de bekommen teacher-Rechte
    if email.endswith('@kgs-pattensen.de'):
        print(f"   → Teacher (KGS-Domain)")
        return 'teacher'
    
    # Fallback: teacher
    print(f"   → Teacher (Fallback)")
    return 'teacher'
