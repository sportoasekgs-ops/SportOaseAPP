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
            'scope': 'openid profile email'
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
    
    Args:
        userinfo: Dictionary mit Benutzerdaten von IServ (email, name, groups, etc.)
    
    Returns:
        'admin' oder 'teacher'
    """
    # Prüfe IServ-Gruppen (falls vorhanden)
    groups = userinfo.get('groups', [])
    
    # Wenn groups ein String ist, in Liste konvertieren
    if isinstance(groups, str):
        groups = [groups]
    
    # Administrator-Gruppe hat Admin-Rechte
    if 'Administrator' in groups:
        return 'admin'
    
    # Lehrer und Mitarbeitende haben Teacher-Rechte
    if 'Lehrer' in groups or 'Mitarbeitende' in groups:
        return 'teacher'
    
    # Fallback zu E-Mail-Check für morelli.maurizio@kgs-pattensen.de
    email = userinfo.get('email', '').lower().strip()
    if is_admin_email(email):
        return 'admin'
    
    # Standard: teacher
    return 'teacher'
