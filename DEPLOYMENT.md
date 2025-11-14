# Deployment Guide für Render

Diese Anleitung beschreibt, wie Sie die SportOase-App auf Render deployen.

## Voraussetzungen

- GitHub Repository mit dem Code
- Render Account (kostenlos verfügbar)

## Schritt 1: PostgreSQL-Datenbank erstellen

1. Gehen Sie zu [Render Dashboard](https://dashboard.render.com/)
2. Klicken Sie auf **New +** → **PostgreSQL**
3. Konfiguration:
   - **Name**: `sportoase-db` (oder ein anderer Name)
   - **Database**: Leer lassen (wird automatisch generiert)
   - **User**: Leer lassen (wird automatisch generiert)
   - **Region**: Wählen Sie die nächstgelegene Region
   - **PostgreSQL Version**: 15 oder 16
   - **Plan**: Free (läuft nach 90 Tagen ab, erfordert Backup/Neuaufbau)

4. Klicken Sie auf **Create Database**
5. Notieren Sie sich die **Internal Database URL** (wird später benötigt)
6. **WICHTIG**: Ändern Sie `postgres://` zu `postgresql://` in der URL

## Schritt 2: Web Service erstellen

1. Klicken Sie auf **New +** → **Web Service**
2. Verbinden Sie Ihr GitHub Repository
3. Konfiguration:

| Einstellung | Wert |
|-------------|------|
| **Name** | `sportoase-app` |
| **Region** | Gleiche wie Datenbank |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |
| **Plan** | Free |

## Schritt 3: Umgebungsvariablen konfigurieren

Fügen Sie diese Umgebungsvariablen hinzu (unter **Environment**):

| Variable | Wert | Beschreibung |
|----------|------|--------------|
| `DATABASE_URL` | Internal Database URL von PostgreSQL | **Wichtig**: `postgres://` zu `postgresql://` ändern! |
| `SESSION_SECRET` | Ein zufälliger String | Für Flask Sessions (z.B. 32+ Zeichen) |
| `PYTHON_VERSION` | `3.11` | Python-Version |
| `SMTP_HOST` | SMTP-Server | Optional: Für E-Mail-Benachrichtigungen |
| `SMTP_PORT` | `587` | Optional: SMTP Port |
| `SMTP_USER` | Ihr SMTP Benutzername | Optional |
| `SMTP_PASS` | Ihr SMTP Passwort | Optional |
| `SMTP_FROM` | sportoase@sportoase.de | Optional: Absender-E-Mail |
| `ADMIN_EMAIL` | sportoase.kg@gmail.com | Admin E-Mail für Benachrichtigungen |

### Beispiel für SESSION_SECRET generieren:

```python
import os
print(os.urandom(32).hex())
```

## Schritt 4: Datenbank initialisieren

**WICHTIG**: Nach dem ersten Deployment MUSS die Datenbank initialisiert werden!

1. Verbinden Sie sich mit der Render Shell (im Dashboard unter "Shell")
2. Führen Sie aus:

```bash
python db_setup.py
```

Dies erstellt:
- Alle Datenbank-Tabellen
- Den Admin-Account mit:
  - **Benutzername**: sportoase
  - **Passwort**: mauro123
  - **E-Mail**: sportoase.kg@gmail.com

**WICHTIG**: Ändern Sie das Passwort nach dem ersten Login!

## Schritt 5: Deployment überprüfen

1. Öffnen Sie die URL Ihrer App (z.B. `https://sportoase-app.onrender.com`)
2. Melden Sie sich mit den Admin-Zugangsdaten an
3. Prüfen Sie, ob alles funktioniert

## E-Mail-Konfiguration (optional)

Für E-Mail-Benachrichtigungen bei Buchungen können Sie einen SMTP-Service verwenden:

### Gmail SMTP (für Tests):
- Host: `smtp.gmail.com`
- Port: `587`
- User: Ihre Gmail-Adresse
- Pass: App-spezifisches Passwort (nicht Ihr normales Passwort!)

[Anleitung für Gmail App-Passwort](https://support.google.com/accounts/answer/185833)

### Professionelle Services:
- SendGrid (kostenlos bis 100 E-Mails/Tag)
- Mailgun
- Amazon SES

## Wichtige Hinweise

1. **Free Tier**: 
   - Web Service schläft nach 15 Min Inaktivität
   - Erste Anfrage dauert 30-60s zum Aufwachen
   - PostgreSQL läuft nach 90 Tagen ab (Backup erforderlich!)

2. **Datenbank-Backup**:
   ```bash
   pg_dump DATABASE_URL > backup.sql
   ```

3. **Logs überwachen**:
   - Render Dashboard → Ihre App → Logs
   - Hilft bei der Fehlersuche

4. **Updates deployen**:
   - Pushen Sie zu GitHub
   - Render deployt automatisch
   - **Nach größeren Datenbank-Änderungen**: Führen Sie `python db_setup.py` erneut aus

## Troubleshooting

### App startet nicht:
- Prüfen Sie die Logs in Render Dashboard
- Stellen Sie sicher, dass `DATABASE_URL` mit `postgresql://` beginnt
- Überprüfen Sie, ob alle Pakete in `requirements.txt` sind

### Datenbank-Verbindungsfehler:
- Verwenden Sie die **Internal Database URL** (nicht External)
- Bestätigen Sie, dass die Datenbank "Available" ist
- Prüfen Sie, ob Region von App und DB übereinstimmt
- **Wichtig**: Haben Sie `python db_setup.py` ausgeführt?

### "Tabelle existiert nicht" Fehler:
- Sie haben vergessen, `python db_setup.py` auszuführen!
- Verbinden Sie sich mit der Shell und führen Sie das Skript aus

### E-Mails werden nicht gesendet:
- Überprüfen Sie SMTP-Einstellungen in den Umgebungsvariablen
- Testen Sie SMTP-Zugangsdaten lokal
- Prüfen Sie, ob Port 587 erlaubt ist
- Für Gmail: Verwenden Sie ein App-spezifisches Passwort

## Lokale Entwicklung

Für die lokale Entwicklung:

1. Installieren Sie PostgreSQL lokal
2. Erstellen Sie eine `.env` Datei:
   ```
   DATABASE_URL=postgresql://localhost:5432/sportoase_dev
   SESSION_SECRET=dev-secret-key
   ADMIN_EMAIL=sportoase.kg@gmail.com
   ```
3. Führen Sie aus:
   ```bash
   python db_setup.py
   uv run python app.py
   ```

## Support

Bei Fragen zu Render: https://render.com/docs
