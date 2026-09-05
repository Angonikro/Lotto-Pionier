### Datenbank-Manager
Der Datenbank-Manager akzeptiert jedes Datum. Liegt das Datum nicht auf einem Mittwoch oder Samstag, wird automatisch die nächste Ziehung zugeordnet.

### Kalender-Fix v0.4.34
Der Kalender übergibt das ausgewählte Datum direkt an die vorhandene automatische Ziehungssuche.

### Kalender: automatische Ziehungssuche

Die Kalenderauswahl übergibt das gewählte Datum direkt an die bestehende Datumslogik.

### Kalender und automatische Ziehungssuche

Der Kalender setzt das Datum und startet danach dieselbe automatische Ziehungssuche wie eine manuelle Eingabe.

## v0.4.30

### Datenbank Manager und Kalender
- Neuer Schnellzugriff **„Datenbank Manager“** unter „Lottozahlen ziehen“.
- Zu einem konkreten Mittwoch-/Samstag-Datum werden die gespeicherten Lottozahlen, die Superzahl und die vorhandenen Gewinnquoten angezeigt.
- Datumsauswahl per kleinem integriertem Kalender oder manueller Eingabe.
- Der Kalender ist ohne zusätzliche Python-Abhängigkeit umgesetzt.
- Der Kalender steht auch bei „Mein Lotto-Tipp“ und beim Bearbeiten eines Tipps zur Verfügung.
- Der Manager verändert keine Daten; er zeigt ausschließlich den lokalen Datenbestand an.

# Lotto v0.4.28

Lotto 6 aus 49 mit Superzahl – aktuelle und historische Ziehungen, Gewinnquoten, eigene Tipps, automatische Prüfung, Statistik und Analyse.

## v0.4.28

### Aktuelle Ziehungen stabil
- Die Startseite zeigt immer die chronologisch letzte gespeicherte Mittwoch-Ziehung und die chronologisch letzte gespeicherte Samstag-Ziehung.
- Die Auswahl erfolgt anhand des echten Ziehungsdatums, nicht anhand der Reihenfolge, in der Datensätze importiert wurden.
- Dadurch kann ein später importierter älterer Datensatz die aktuelle Anzeige nicht mehr überschreiben.
- Gewinnzahlen, Superzahl und Gewinnquoten bleiben an die jeweilige konkrete Ziehung gekoppelt.


## Externe Datenbank mit vollständigen Gewinnquoten

- Die große externe Historie liefert die Ziehungen mit sechs Gewinnzahlen und Superzahl.
- Nach dem Import prüft Lotto automatisch den vollständigen verfügbaren 9-Klassen-Quotenbestand ab 01.01.2020 auf fehlende endgültige Gewinnquoten.
- Fehlende Quoten werden aus den datierten LOTTO-Archivseiten ergänzt und mit Gewinnerzahl und Quote je Gewinnklasse gespeichert.
- Bereits vollständige Quoten werden übersprungen.
- Auch wenn der große Datenfeed unverändert ist, werden fehlende Quoten nachgeprüft.
- Der Fortschrittsdialog zeigt jetzt auch den Quotenimport.
- Der Quotenimport arbeitet parallel mit acht vorsichtig begrenzten Abrufen, damit der Erstimport auf einem Raspberry Pi deutlich schneller abgeschlossen wird.
- Bei späteren Starts werden neue Ziehungen automatisch geprüft.
- Beim Ausschalten der externen Datenbank bleiben alle lokalen Daten erhalten.

## Automatische Datenprüfung beim Start

Bei aktivierter externer Datenbank wird bei jedem Programmstart geprüft, ob neue Ziehungen und Quoten verfügbar sind. Nur neue oder geänderte Daten werden lokal übernommen; vorhandene lokale Daten bleiben erhalten.

## v0.4.27

### Quotenimport
- Der externe Zahlenfeed wird weiterhin vollständig lokal übernommen.
- Für die aktuelle 9-Klassen-Struktur werden die Gewinnquoten ab 01.01.2020 automatisch nachgeladen.
- Der Import der fehlenden Quoten läuft parallel und zeigt den Fortschritt im Fenster „Externe Lotto-Datenbank“.
- Einzelne Fehler werden protokolliert und beim nächsten Abgleich erneut versucht.

## v0.4.24

### Externe Lotto-Datenbank – einmal aktivieren, automatisch aktuell
- Die externe Datenbank verwendet jetzt den **automatisch gepflegten LOTTO-6aus49-JSON-Datenfeed** von `lotto-aktuell/lotto-daten-feed`. Der Feed wird nach den Mittwoch- und Samstag-Ziehungen automatisch aktualisiert.
- Beim ersten Aktivieren wird die vollständige verfügbare Ziehungshistorie lokal in `lotto.db` übernommen.
- Danach prüft das Programm die externe Datenbank **bei jedem Start automatisch** auf neue oder geänderte Ziehungen. Ein manuelles Nachladen ist nicht nötig.
- Auch **„Aktualisieren“** stößt denselben Abgleich an.
- Bereits lokal gespeicherte Daten werden nicht gelöscht, wenn die externe Datenbank wieder ausgeschaltet wird.
- Der Datenfeed enthält Gewinnzahlen und Superzahl. Die Gewinnquoten werden weiterhin ergänzend aus den aktuellen Lotto-Archivseiten geladen.
- Die Datenbank wird auf Plausibilität geprüft; bei einem fehlerhaften oder unvollständigen Feed bleibt der vorhandene lokale Datenbestand unverändert.

## v0.4.23

### Aktuelle externe Datenquelle
- Wenn **Einstellungen → Externe Lotto-Datenbank verwenden** aktiviert ist, wird der historische Datenbestand bei jedem Start und bei **Aktualisieren** erneut geprüft und lokal abgeglichen.
- Die **aktuellen** Lottozahlen und Gewinnquoten werden danach zusätzlich aus der aktuellen Quelle abgerufen. So bleiben aktuelle Ziehungen unabhängig vom Aktualisierungsstand des historischen Vollarchivs aktuell.
- Die lokale Datenbank wird nicht gelöscht, wenn die externe Datenbank wieder ausgeschaltet wird.

## v0.4.22

### Externe Lotto-Datenbank
- Unter **Einstellungen** kann die externe Datenbank aktiviert werden.
- Beim ersten Einschalten wird die vollständige verfügbare LOTTO-6aus49-Ziehungshistorie geladen und lokal gespeichert.
- Während des Downloads zeigt ein Fortschrittsfenster den aktuellen Stand.
- Bereits vorhandene lokale Ziehungen werden nicht als Duplikate angelegt.
- Beim Ausschalten bleiben die lokalen Daten erhalten.
- Die verwendete Vollhistorien-CSV enthält Ziehungsdatum, sechs Lottozahlen und Superzahl. Gewinnquoten werden bei Bedarf für konkrete Ziehungen aus den datierten Archivseiten nachgeladen.

### Einstellungen
- **Hell / Dunkel**
- **Externe Lotto-Datenbank verwenden**

## v0.4.13

### Freies Tippdatum
- Für einen eigenen Tipp kann jeder gültige Kalendertag eingegeben werden.
- Das Programm sucht automatisch die nächste passende Mittwoch- oder Samstag-Ziehung.
- Das zugehörige Ziehungsdatum wird vor dem Speichern angezeigt.

# Lotto

Lotto 6 aus 49 mit Superzahl – aktuelle und historische Ziehungen, Gewinnquoten, eigene Tipps, automatische Prüfung, Statistik und Analyse.

Lotto 6 aus 49 mit Superzahl – mit getrennten Mittwoch- und Samstag-Ziehungen, historischen Tipps, Gewinnquoten, Analyse und automatischer Gewinnprüfung.

## v0.4.13

### Historische Tipps
- Das Ziehungsdatum bestimmt automatisch Mittwoch oder Samstag.
- Alte Tipps werden beim Start und über **„Aktualisieren“** gegen ihre konkrete historische Ziehung geprüft.
- Fehlende historische Gewinnzahlen, Superzahlen und Gewinnquoten werden nachgeladen.

### Bedienung
- Neuer Button **„Aktualisieren“**.
- Unter **„Darstellung“** kann zwischen **Hell** und **Dunkel** gewechselt werden.

## v0.4.13

### Statistik
- Die Statistik enthält jetzt einen eigenen Bereich **„Offiziell Superzahl“** für die Superzahlen 0 bis 9 mit Anzahl und prozentualem Anteil der gespeicherten offiziellen Ziehungen.

## v0.4.13

### Daten- und Quotenreparatur
- Die sechs Gewinnzahlen werden jetzt ausschließlich aus dem Bereich „Gewinnzahlen“ gelesen.
- Datum, „6 aus 49“ und andere Seitennummern können nicht mehr als Gewinnzahlen erkannt werden.
- Die Gewinnquoten werden strikt auf den LOTTO-6aus49-Bereich begrenzt; Spiel 77 und SUPER 6 können die Quoten nicht mehr überschreiben.
- Bereits falsch gespeicherte Ziehungen werden beim nächsten Datenabruf automatisch repariert.
- Unveränderte Ziehungen werden weiterhin nicht doppelt gespeichert.
- Die Gewinnquoten werden nur aus der eigentlichen Quotentabelle gelesen; ausgezahlte Gesamtbeträge werden nicht mehr als Einzelquote angezeigt.
- Unbesetzte Gewinnklassen werden korrekt als „unbesetzt“ dargestellt.
- Vorhandene identische Quoten werden nicht erneut gespeichert; fehlerhafte bestehende Werte werden nur in place korrigiert.

## v0.4.13

### Aktuelle Daten
- Die Startseite zeigt immer die jeweils letzte abgeschlossene Mittwoch- und Samstag-Ziehung.
- Gewinnzahlen und Gewinnquoten werden automatisch aus den datierten Archivseiten geladen.
- Neue offizielle Ziehungen werden nur gespeichert, wenn sie noch nicht vorhanden sind.

### Meine Tipps
- Beliebig viele eigene Tipps speichern.
- Mittwoch und Samstag getrennt auswählen.
- Ein konkretes Ziehungsdatum zum Tipp speichern.
- Auch alte Tipps können eingegeben werden.
- Alte Tipps werden immer mit der Gewinnziehung ihres eigenen Datums verglichen.

### Automatische Gewinnmeldung
Beim Start und nach einem Datenabruf werden alle gespeicherten Tipps geprüft. Wenn ein alter oder neuer Tipp gewonnen hat, erscheint eine Gewinnmeldung mit Gewinnklasse und – sofern vorhanden – der Quote dieser konkreten Ziehung.

### Analyse
Die Analyse zeigt gespeicherte Ziehungen, Gewinnquoten und die Ergebnisse der eigenen Tipps.

## Start

```bash
python3 Lotto.py
```

Optional kann der Desktop-Starter über `install_desktop_launcher.sh` installiert werden.

## Hinweis
Die Daten stammen aus öffentlich verfügbaren Lotto-Archivdaten. Für die tatsächliche Spielteilnahme sind die offiziellen Angaben des Veranstalters maßgeblich.


### Einstellungen
Die Darstellung (Hell/Dunkel) wird in `data/settings.ini` gespeichert.


## Sound v0.4.41

Über das neue Menü **Sound** können Gewinn-Sound und Audio-Treiber unabhängig von den übrigen Einstellungen verwaltet werden.

- Gewinn-Sound An/Aus
- Test-Sound
- Sound-Einstellungen
- Treiber: `pulse`, `alsa`, `portaudio`
- automatische Glocke bei einem erkannten Gewinn
- Einstellungen werden dauerhaft gespeichert




## Installation

### Windows

1. ZIP-Datei entpacken.
2. Den Ordner `Lotto` öffnen.
3. Python 3 installieren, falls noch nicht vorhanden.
4. Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

5. Programm starten:

```bash
python Lotto.py
```

Optional kann eine Desktop-Verknüpfung erstellt werden.

### Linux

1. ZIP-Datei entpacken.
2. Terminal im Lotto-Ordner öffnen.
3. Falls benötigt pip installieren:

```bash
sudo apt install python3-pip
```

4. Abhängigkeiten installieren:

```bash
python3 -m pip install -r requirements.txt
```

5. Programm starten:

```bash
python3 Lotto.py
```

### Linux Desktop Launcher

Der Launcher muss zuerst ausführbar gemacht werden:

```bash
chmod +x install_desktop_launcher.sh
```

Danach installieren:

```bash
./install_desktop_launcher.sh
```

Danach kann Lotto Pionier über den Desktop bzw. das Anwendungsmenü gestartet werden.

## Version

Lotto Pionier v0.4.44
