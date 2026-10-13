## 0.4.47 – Startkorrektur
- Fehler beim Start behoben: Das Datenverzeichnis unter `~/.local/share/lotto-pionier/` wird vor dem Öffnen der SQLite-Datenbank angelegt.
- Versionsnummer bleibt unverändert bei 0.4.47.

# CHANGELOG

## v0.4.47

- Fehler behoben, durch den das gewählte helle/dunkle Theme nach einem Neustart nicht zuverlässig erhalten blieb.
- Einstellungen werden konsistent in `~/.config/lotto-pionier/settings.ini` gespeichert.
- Vorhandene Einstellungen werden bei Bedarf aus dem alten Programmordner übernommen.
- Beim Speichern bleiben weitere INI-Abschnitte, darunter die Anbieterauswahl, erhalten.
- Temporäre Datei und atomisches Ersetzen verhindern unvollständige INI-Dateien.


## v0.4.46

- Entfernt: doppelter Menüpunkt „Datenbank Manager“ unter „Statistiken“. Der bestehende Eintrag unter „Datenbank“ bleibt erhalten.
- Aktuelle Samstag-Ziehung wird auch dann gespeichert und angezeigt, wenn die Gewinnquoten noch nicht veröffentlicht sind.
- Windows-Sound über `winsound` unterstützt.
- Sound-Treiber „Auto“ ergänzt.

## v0.4.45

### Anbieter-Wechsel
- Anbieter-Auswahl eingebaut
- Gewählter Anbieter wird in settings.ini gespeichert
- Letzter Anbieter wird beim Programmstart wieder geladen
- Aktualisierungsanzeige verwendet den gewählten Anbieter

### Stabilität
- Keine Änderungen an Datenbank, Ziehungen oder Gewinn-Glocke
- Bestehende Funktionen bleiben unverändert

## v0.4.44

### Design Plus 2 Update
- Neues farbigeres Oberflächen-Design
- Schnellzugriff-Buttons optisch verbessert
- Theme-Menü und Datenbank-Menü bleiben erhalten
