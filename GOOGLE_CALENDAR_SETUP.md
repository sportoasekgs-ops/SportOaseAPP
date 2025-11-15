# Google Calendar Integration Setup

Diese Anleitung erklärt, wie Sie die Google Calendar Integration für das SportOase Buchungssystem einrichten.

## Schritt 1: Google Cloud Service Account erstellen

1. Gehen Sie zur [Google Cloud Console](https://console.cloud.google.com/)
2. Erstellen Sie ein neues Projekt oder wählen Sie ein bestehendes aus
3. Aktivieren Sie die **Google Calendar API**:
   - Navigieren Sie zu "APIs & Services" > "Library"
   - Suchen Sie nach "Google Calendar API"
   - Klicken Sie auf "Enable"

## Schritt 2: Service Account erstellen

1. Gehen Sie zu "APIs & Services" > "Credentials"
2. Klicken Sie auf "Create Credentials" > "Service Account"
3. Geben Sie einen Namen ein (z.B. "sportoase-calendar")
4. Klicken Sie auf "Create and Continue"
5. Überspringen Sie die optionalen Schritte und klicken Sie auf "Done"

## Schritt 3: Service Account Key erstellen

1. Klicken Sie auf den neu erstellten Service Account
2. Gehen Sie zum Tab "Keys"
3. Klicken Sie auf "Add Key" > "Create new key"
4. Wählen Sie **JSON** als Schlüsseltyp
5. Klicken Sie auf "Create"
6. Eine JSON-Datei wird heruntergeladen - **bewahren Sie diese sicher auf!**

## Schritt 4: Service Account Zugriff auf Calendar geben

1. Öffnen Sie [Google Calendar](https://calendar.google.com/)
2. Wählen Sie den Kalender aus, in dem die Buchungen erscheinen sollen
3. Klicken Sie auf die drei Punkte neben dem Kalender > "Settings and sharing"
4. Scrollen Sie zu "Share with specific people"
5. Klicken Sie auf "Add people"
6. Geben Sie die **Service Account E-Mail** ein (steht in der JSON-Datei als `client_email`)
7. Wählen Sie die Berechtigung **"Make changes to events"**
8. Klicken Sie auf "Send"

## Schritt 5: Umgebungsvariablen konfigurieren

### Für Replit:
1. Öffnen Sie die **Secrets** in Replit (🔒 Icon in der Sidebar)
2. Fügen Sie folgende Secrets hinzu:

**GOOGLE_CALENDAR_CREDENTIALS**
```
Der komplette Inhalt der JSON-Datei als String
```

**GOOGLE_CALENDAR_ID** (optional)
```
primary
```
(Oder die spezifische Calendar ID, wenn Sie einen anderen Kalender verwenden möchten)

### Für Render / andere Umgebungen:
1. Gehen Sie zu den Environment Variables
2. Fügen Sie hinzu:
   - **GOOGLE_CALENDAR_CREDENTIALS**: Kompletter JSON-Inhalt als String
   - **GOOGLE_CALENDAR_ID**: `primary` (oder spezifische Calendar ID)

## Schritt 6: Datenbank-Migration ausführen

Führen Sie das Migrations-Script aus, um die `calendar_event_id` Spalte hinzuzufügen:

```bash
python migration_add_calendar_event_id.py
```

## Schritt 7: Anwendung neu starten

Starten Sie die Anwendung neu, damit die Änderungen wirksam werden.

## Testen

1. Erstellen Sie eine neue Buchung über die Webseite
2. Überprüfen Sie Ihren Google Calendar - es sollte ein neuer Eintrag erscheinen
3. Die Logs sollten zeigen: `✓ Google Calendar Service erfolgreich initialisiert`

## Fehlersuche

### "Google Calendar nicht konfiguriert"
- Überprüfen Sie, ob die `GOOGLE_CALENDAR_CREDENTIALS` Secret gesetzt ist
- Stellen Sie sicher, dass es gültiges JSON ist

### "403 Forbidden" Fehler
- Überprüfen Sie, ob der Service Account Zugriff auf den Kalender hat
- Stellen Sie sicher, dass die Google Calendar API aktiviert ist

### Kalender-Einträge erscheinen nicht
- Überprüfen Sie die `GOOGLE_CALENDAR_ID` (sollte `primary` sein für den Hauptkalender)
- Prüfen Sie die Logs auf Fehlermeldungen

## Hinweise

- Die Calendar-Integration ist **optional** - die App funktioniert auch ohne sie
- Wenn die Integration nicht konfiguriert ist, werden nur E-Mails versendet
- Bei Buchungslöschungen wird automatisch auch der Calendar-Eintrag gelöscht
- Jeder Calendar-Eintrag enthält:
  - Titel: "SportOase: [Angebot]"
  - Datum und Uhrzeit der Stunde
  - Lehrkraft und Klasse
  - Liste aller gebuchten Schüler
  - Erinnerungen (1 Tag vorher, 1 Stunde vorher)
