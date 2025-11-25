# Render Deployment Guide - SportOase Buchungssystem

## 🚀 Deployment-Anleitung für Render

### 1. Environment Variables in Render konfigurieren

Folgende Environment Variables müssen in Render unter **Environment** eingetragen werden:

#### Datenbank
```
DATABASE_URL=<Ihre PostgreSQL Connection String>
```
*Wird automatisch von Render PostgreSQL gesetzt*

#### Session Security
```
SESSION_SECRET=<Ein zufälliger 64-stelliger String>
```
*Generieren mit: `python -c "import secrets; print(secrets.token_hex(32))"`*

#### IServ OAuth (Single Sign-On)
```
ISERV_CLIENT_ID=<Client ID aus IServ>
ISERV_CLIENT_SECRET=<Client Secret aus IServ>
ISERV_DOMAIN=kgs-pattensen.de
```

#### E-Mail Versand (SMTP)
```
SMTP_USER=sportoase.kgs@gmail.com
SMTP_PASS=<App-Passwort von Gmail>
```

#### Google Calendar (Optional)
```
GOOGLE_CALENDAR_CREDENTIALS=<JSON Service Account Key>
GOOGLE_CALENDAR_ID=sportoase.kgs@gmail.com
```

### 2. Build & Start Commands

#### Build Command (optional):
```bash
pip install -r requirements.txt
```

#### Start Command:
```bash
gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 main:app
```

### 3. Wichtige Einstellungen in Render

- **Runtime**: Python 3.11 oder höher
- **Plan**: Starter oder höher (für Always-On)
- **Region**: Frankfurt (gleiche Region wie PostgreSQL)
- **Auto-Deploy**: Ja (bei Git-Push automatisch deployen)

### 4. IServ OAuth Konfiguration

In IServ Admin-Panel (Single-Sign-On → SportOase Buchungssystem):

**Weiterleitungs-URIs:**
```
https://sportoase.app/oauth/callback
https://<ihre-render-url>.onrender.com/oauth/callback
```

**Auf Scopes einschränken:**
- openid
- profile
- email

**Gruppen-Berechtigung:**
- Administrator
- Lehrer
- Mitarbeitende

### 5. Datenbank Setup

Nach dem ersten Deployment:

```bash
# In Render Shell ausführen:
python db_setup.py
```

Oder über die Render Shell:
1. Gehe zu Shell im Render Dashboard
2. Führe `python db_setup.py` aus
3. Verifiziere die Tabellen mit `python -c "from app import db; print(db.engine.table_names())"`

### 6. Health Check

Render prüft automatisch die Verfügbarkeit über:
```
https://sportoase.app/
```

Falls der Health Check fehlschlägt:
- Prüfe die Logs in Render Dashboard
- Verifiziere alle Environment Variables
- Stelle sicher, dass DATABASE_URL korrekt ist

### 7. Custom Domain einrichten

1. Gehe zu Settings → Custom Domain
2. Füge `sportoase.app` hinzu
3. Konfiguriere DNS bei deinem Domain-Provider:
   - CNAME Record: `www` → `<deine-app>.onrender.com`
   - A Record: `@` → (Render IP-Adresse)

### 8. SSL/TLS

- SSL wird automatisch von Render bereitgestellt (Let's Encrypt)
- Erzwinge HTTPS: Ist standardmäßig aktiviert

### 9. Monitoring & Logs

- **Logs ansehen**: Render Dashboard → Logs
- **Metrics**: Render Dashboard → Metrics
- **Alerts**: Konfigurierbar über Render Dashboard

### 10. Troubleshooting

#### Problem: App startet nicht
- Prüfe Logs: `gunicorn` Fehler?
- Verifiziere `requirements.txt` Syntax
- Stelle sicher, dass `main.py` existiert

#### Problem: Database Connection Error
- Prüfe `DATABASE_URL` in Environment Variables
- Stelle sicher, dass PostgreSQL läuft
- Verifiziere Firewall/Netzwerk-Einstellungen

#### Problem: IServ Login funktioniert nicht
- Prüfe `ISERV_CLIENT_ID` und `ISERV_CLIENT_SECRET`
- Verifiziere Weiterleitungs-URI in IServ
- Prüfe Logs auf OAuth-Fehler

#### Problem: E-Mails werden nicht versendet
- Prüfe `SMTP_USER` und `SMTP_PASS`
- Stelle sicher, dass Gmail App-Passwort korrekt ist
- Verifiziere Gmail-Einstellungen (2FA aktiviert?)

### 11. Backup & Recovery

#### Datenbank Backup:
```bash
# In Render Shell:
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

#### Restore:
```bash
psql $DATABASE_URL < backup_YYYYMMDD.sql
```

### 12. Skalierung

- **Horizontal**: Erhöhe Worker-Anzahl in Start Command
- **Vertical**: Upgrade auf höheren Plan in Render
- **Database**: Upgrade PostgreSQL Plan für mehr Connections

### 13. Sicherheit

✅ **Implementiert:**
- HTTPS erzwungen
- CSRF-Schutz aktiviert
- Password Hashing (Werkzeug)
- SQL Injection Schutz (SQLAlchemy ORM)
- XSS-Schutz (Jinja2 Auto-Escaping)
- Session Security (secure cookies)

### 14. Performance-Optimierungen

- **Gunicorn Workers**: 2-4 (je nach Traffic)
- **Timeout**: 120 Sekunden
- **Database Connection Pool**: Pre-ping aktiviert
- **Static Files**: Werden von Flask ausgeliefert

---

## 📋 Deployment-Checkliste

- [ ] Alle Environment Variables in Render gesetzt
- [ ] PostgreSQL Datenbank erstellt und verbunden
- [ ] Build Command konfiguriert
- [ ] Start Command konfiguriert
- [ ] IServ OAuth Weiterleitungs-URIs aktualisiert
- [ ] `db_setup.py` ausgeführt
- [ ] Erster Admin-Account erstellt
- [ ] Custom Domain konfiguriert (optional)
- [ ] SSL/HTTPS aktiviert
- [ ] Health Check erfolgreich
- [ ] E-Mail-Versand getestet
- [ ] IServ Login getestet
- [ ] Buchungsfunktion getestet

---

## 🎯 Live-URL

Nach erfolgreichem Deployment:
- **Render URL**: `https://<ihre-app>.onrender.com`
- **Custom Domain**: `https://sportoase.app`

---

**Hinweis**: Diese Anleitung wurde für Render.com optimiert. Bei Fragen wenden Sie sich an Mauro Morelli.
