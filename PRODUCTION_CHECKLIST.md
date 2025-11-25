# 🚀 Production Checklist - SportOase Buchungssystem

## Vor dem Deployment

### Render Environment Variables
- [ ] `DATABASE_URL` - Automatisch von Render PostgreSQL gesetzt
- [ ] `SESSION_SECRET` - Generiert mit `secrets.token_hex(32)`
- [ ] `ISERV_CLIENT_ID` - Aus IServ Admin-Panel
- [ ] `ISERV_CLIENT_SECRET` - Aus IServ Admin-Panel
- [ ] `ISERV_DOMAIN` - `kgs-pattensen.de`
- [ ] `SMTP_USER` - `sportoase.kgs@gmail.com`
- [ ] `SMTP_PASS` - Gmail App-Passwort
- [ ] `GOOGLE_CALENDAR_CREDENTIALS` - Service Account JSON (optional)
- [ ] `GOOGLE_CALENDAR_ID` - `sportoase.kgs@gmail.com` (optional)

### IServ OAuth Konfiguration
- [ ] Client erstellt in IServ Admin (Single-Sign-On)
- [ ] Weiterleitungs-URI gesetzt: `https://sportoase.app/oauth/callback`
- [ ] Scopes konfiguriert: `openid profile email`
- [ ] Gruppen berechtigt: Administrator, Lehrer, Mitarbeitende
- [ ] Client als "Vertrauenswürdig" markiert

### Datenbank Setup
- [ ] PostgreSQL Datenbank in Render erstellt
- [ ] DATABASE_URL in Environment Variables gesetzt
- [ ] Datenbank initialisiert mit `python db_setup.py`
- [ ] Tabellen verifiziert: users, bookings, slot_names, blocked_slots, notifications
- [ ] Admin-Account erstellt (via IServ Login)

### Code & Deployment
- [ ] `requirements.txt` bereinigt (keine Duplikate)
- [ ] `.gitignore` aktualisiert (logs/, .env ausgeschlossen)
- [ ] `render.yaml` erstellt für automatisches Deployment
- [ ] Start Command gesetzt: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 main:app`
- [ ] Python Version: 3.11 oder höher
- [ ] Region: Frankfurt (gleiche wie Database)

## Nach dem Deployment

### Funktionstest
- [ ] Website erreichbar unter `https://sportoase.app`
- [ ] SSL/HTTPS funktioniert (grünes Schloss)
- [ ] IServ Login funktioniert
- [ ] Dashboard lädt korrekt
- [ ] Wochenübersicht wird angezeigt
- [ ] Buchung erstellen funktioniert
- [ ] E-Mail-Benachrichtigung wird versendet
- [ ] Google Calendar Event wird erstellt (falls konfiguriert)
- [ ] Admin-Funktionen zugänglich (nur für Administrator-Gruppe)
- [ ] Slot-Blockierung funktioniert
- [ ] Buchung ändern/löschen funktioniert

### Benutzer-Rollen Test
- [ ] Administrator-Gruppe → Admin-Rechte
- [ ] Lehrer-Gruppe → Teacher-Rechte
- [ ] Mitarbeitende-Gruppe → Teacher-Rechte
- [ ] Fallback: morelli.maurizio@kgs-pattensen.de → Admin

### Performance & Monitoring
- [ ] Render Logs zeigen keine Fehler
- [ ] Response Time < 1 Sekunde
- [ ] Database Connection Pool funktioniert
- [ ] Gunicorn Workers starten korrekt (2 Workers)
- [ ] Keine Timeout-Errors

### Sicherheit
- [ ] HTTPS erzwungen
- [ ] CSRF-Schutz aktiv
- [ ] SQL Injection Schutz (SQLAlchemy ORM)
- [ ] XSS-Schutz (Jinja2 Auto-Escaping)
- [ ] Passwort-Hashing (Werkzeug)
- [ ] Secrets nicht im Code hardcoded
- [ ] `.env` in `.gitignore`

### Mobile Responsive
- [ ] Login-Seite auf Mobile getestet
- [ ] Dashboard auf Mobile responsive
- [ ] Buchungsformular auf Mobile nutzbar
- [ ] Touch-Targets mindestens 44px
- [ ] Tabellen horizontal scrollbar auf kleinen Screens

## Custom Domain (sportoase.app)

### DNS Konfiguration
- [ ] CNAME Record: `www` → `<ihre-app>.onrender.com`
- [ ] A Record: `@` → Render IP-Adresse
- [ ] SSL-Zertifikat von Render automatisch bereitgestellt
- [ ] HTTPS-Weiterleitung aktiviert

### IServ Weiterleitungs-URI aktualisiert
- [ ] `https://sportoase.app/oauth/callback` in IServ hinzugefügt
- [ ] Alte URLs entfernt (falls vorhanden)

## Backup & Recovery

- [ ] Datenbank-Backup-Strategie dokumentiert
- [ ] Render automatische Backups aktiviert (je nach Plan)
- [ ] Restore-Prozedur getestet
- [ ] Code in Git Repository gesichert

## Monitoring & Alerts

- [ ] Render Dashboard Metrics aktiviert
- [ ] Email-Alerts bei Downtime konfiguriert (optional)
- [ ] Logs regelmäßig überprüfen
- [ ] Performance-Metriken überwachen

## Dokumentation

- [ ] `RENDER_DEPLOYMENT.md` vollständig
- [ ] `.env.example` mit allen benötigten Variables
- [ ] Deployment-Prozess dokumentiert
- [ ] Troubleshooting-Anleitung vorhanden

## Support & Wartung

- [ ] Admin-Kontakt hinterlegt: Mauro Morelli
- [ ] Support-Email konfiguriert: sportoase.kgs@gmail.com
- [ ] Update-Prozess dokumentiert
- [ ] Rollback-Strategie definiert

---

## 🎯 Deployment Status

**Aktueller Status**: ⏳ Bereit für Production

**Nächste Schritte**:
1. Alle Checkboxen abhaken
2. IServ OAuth Weiterleitungs-URI aktualisieren
3. Datenbank mit `db_setup.py` initialisieren
4. Ersten Admin-Login via IServ durchführen
5. Vollständigen Funktionstest durchführen

**Deployment-Datum**: _____________

**Verantwortlich**: Mauro Morelli

---

**Hinweis**: Diese Checklist sollte bei jedem Deployment durchgegangen werden.
