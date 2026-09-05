# CHANGELOG

## v0.4.44

### Design Plus 2 Update
- Neues farbigeres Oberflächen-Design
- Schnellzugriff-Buttons optisch verbessert
- Theme-Menü und Datenbank-Menü bleiben erhalten
- Fehlerkorrektur: Aktualisieren-Meldung funktioniert auch mit aktivierter Datenbank
- Gewinn-Glocke weiterhin integriert

## v0.4.43 – Originale Glocke als win_bell.wav

- Grundlage exakt v0.4.41 mit funktionierendem Sound-Menü.
- Die vom Benutzer gelieferte Glocke wird als `data/win_bell.wav` eingebunden.
- Die App erzeugt keine künstliche `win_bell.wav` mehr.
- Die vorhandene Soundlogik, Datenbank und Kalenderfunktion bleiben erhalten.

# CHANGELOG

## v0.4.41
- Neues eigenes Menü „Sound“ in der Menüleiste.
- Gewinn-Sound kann dauerhaft an/aus geschaltet werden.
- Test-Sound direkt im Sound-Menü und in den Sound-Einstellungen.
- Auswahl der Sound-Treiber pulse, alsa und portaudio.
- Verfügbare Linux-Audio-Backends werden in den Sound-Einstellungen angezeigt.
- Bei einem erkannten Gewinn wird automatisch eine Glocke abgespielt.
- Sound-Einstellungen werden dauerhaft in `data/settings.ini` gespeichert.

## v0.4.35 – Datenbank-Manager Datumssuche

- Beliebige Kalenderdaten werden wie im Tippfenster der nächsten Mittwoch-/Samstag-Ziehung zugeordnet.
- Kalender und manuelle Eingabe verwenden im Datenbank-Manager dieselbe Logik.

## v0.4.34 – Kalender übergibt Datum direkt

- Kalender ruft die bestehende Datums-/Ziehungssuche jetzt direkt auf.
- Keine Abhängigkeit mehr von künstlichen Tastaturereignissen.
- Versionsanzeige in `Lotto.py` korrigiert und auf v0.4.34 angehoben.

## v0.4.33 – Kalender direkt mit Datumslogik verbunden

- Kalender ruft die vorhandene Datums-/Ziehungssuche direkt auf.
- Keine künstlichen Tastaturereignisse mehr nötig.
- Manuelle Datumseingabe bleibt unverändert.

## v0.4.32 – Kalender-Callback repariert

- Kalenderauswahl ruft die konkrete Datumsverarbeitung direkt auf.
- Automatische Ziehungssuche funktioniert jetzt auch nach Kalenderauswahl.
- Datenbank-Manager und Tipp-Eingabe verwenden dieselbe zuverlässige Kalender-Anbindung.

## v0.4.31 – Kalender übernimmt Datum korrekt

- Kalenderdatum wird jetzt exakt über denselben Suchweg verarbeitet wie manuell eingegebene Daten.
- Die bestehende automatische Ziehungssuche bleibt unverändert.

## v0.4.30 – Tippdatum findet die konkrete Ziehung wieder

- Die automatische Zuordnung eines Tippdatums zu einer konkreten Mittwoch-/Samstag-Ziehung wurde stabilisiert.
- Auch historische Tippdaten werden jetzt unabhängig von der aktuell auf der Startseite angezeigten Ziehung korrekt zugeordnet.
- Ist die zugehörige Ziehung bereits lokal gespeichert, werden Lottozahlen und Superzahl direkt im Tippfenster angezeigt.
- Fehlt die Ziehung lokal, wird sie beim Speichern des Tipps gezielt für dieses Datum aus dem Archiv nachgeladen.
- Das Eingabefenster bleibt danach für den nächsten Tipp geöffnet.
- Der Kalender und der Datenbank Manager bleiben unverändert erhalten.
- Anleitung in der App, README und PDF-Anleitung aktualisiert.

## v0.4.29 – Datenbank Manager und Kalender

- Neuer Button **„Datenbank Manager“** im freien Feld unter „Lottozahlen ziehen“.
- Der Datenbank Manager zeigt zu einem ausgewählten Ziehungsdatum Lottozahlen, Superzahl und die gespeicherten Gewinnquoten.
- Das Datum kann direkt eingegeben oder über ein kleines integriertes Kalenderfenster ausgewählt werden.
- Das Kalenderfenster benötigt kein zusätzliches Python-Paket und funktioniert damit auch auf dem Raspberry Pi ohne Nachinstallation.
- Das Kalenderfenster steht jetzt auch bei der Eingabe und Bearbeitung eigener Tipps zur Verfügung.
- Der Datenbank Manager liest nur die lokale Datenbank und verändert vorhandene Daten nicht.
- Anleitung in der App, README und PDF-Anleitung aktualisiert.

## v0.4.28 – Aktuelle Mittwoch-/Samstag-Ziehung stabilisiert

- Die Startseite wählt die aktuelle Mittwoch- und Samstag-Ziehung jetzt anhand des tatsächlichen Ziehungsdatums und nicht mehr anhand der internen Datenbank-ID.
- Dadurch kann ein später importierter älterer historischer Datensatz die aktuelle Anzeige nicht mehr verdrängen.
- Zahlen, Superzahl und Gewinnquoten bleiben weiterhin an dieselbe konkrete Ziehung gekoppelt.
- Die vorhandene externe Datenbank, Historie und lokale Daten bleiben unverändert erhalten.
- Anleitung, README und PDF-Anleitung auf v0.4.28 aktualisiert.

## v0.4.27 – Quotenimport repariert und beschleunigt

- Der externe Vollimport bleibt für die komplette Ziehungshistorie aktiv.
- Der bisherige Quoten-Synchronisationsbereich ab 04.05.2013 wurde korrigiert: Die 9 Gewinnklassen werden für den verfügbaren vollständigen Quotenbestand ab **01.01.2020** synchronisiert.
- Der Quotenimport läuft jetzt mit einem kleinen parallelen Worker-Pool, damit die rund 697 Ziehungen nicht stundenlang nacheinander abgefragt werden müssen.
- Der Fortschrittsdialog zeigt weiterhin sichtbar den Quotenfortschritt.
- Bereits vollständige Quoten werden übersprungen; lokale Daten bleiben erhalten.
- Fehler einzelner Archivseiten stoppen nicht mehr den gesamten Import; sie werden gesammelt und beim nächsten Abgleich erneut versucht.
- Anleitung in der App, README und PDF-Anleitung aktualisiert.

## v0.4.26 – Externe Datenbank mit vollständigen Gewinnquoten

- Die externe Historie bleibt die große Ziehungsquelle für Zahlen und Superzahl.
- Nach dem Import werden jetzt automatisch fehlende endgültige Gewinnquoten nachgeladen.
- Für den heutigen 9-Klassen-Gewinnplan werden die Gewinnquoten der Ziehungen ab 04.05.2013 aus dem datierten Lotto-Archiv ergänzt.
- Auch bei HTTP 304 (keine Änderung im großen Ziehungsfeed) werden fehlende Quoten nachgeprüft.
- Der Fortschrittsdialog zeigt zusätzlich den Fortschritt beim Quotenimport.
- Bereits vollständige Quoten werden übersprungen; lokale Daten werden nicht gelöscht.
- Die Datenquelle wird intern als Ziehungsfeed + lottozahlen.de Gewinnquotenarchiv geführt.
- Anleitung in der App und PDF-Anleitung aktualisiert.

## v0.4.25 – Automatische Prüfung beim Start

- Externe vollständige Datenquelle dokumentiert.
- Automatische Prüfung auf neue Ziehungen/Quoten bei jedem Start aktiviert.
- Erstimport nur bei Aktivierung; danach inkrementeller Abgleich.
- Lokale Daten bleiben beim Deaktivieren erhalten.

## v0.4.24 – Externe Datenbank: einmal aktivieren, automatisch aktuell

- Die externe Datenbank wurde auf den automatisch gepflegten JSON-Datenfeed `lotto-aktuell/lotto-daten-feed` umgestellt.
- Der Feed wird laut Projektbeschreibung nach jeder Mittwoch-/Samstag-Ziehung automatisch aktualisiert.
- Beim ersten Aktivieren wird die vollständige verfügbare Historie lokal geladen.
- Danach prüft die Anwendung die externe Datenbank bei jedem Start automatisch auf neue bzw. geänderte Ziehungen.
- Der Abgleich nutzt ETag/Last-Modified, sofern der Server diese Angaben liefert, damit unveränderte Daten nicht unnötig neu verarbeitet werden.
- „Aktualisieren“ führt ebenfalls den Datenbank-Abgleich aus.
- Ein unvollständiger Feed wird verworfen; vorhandene lokale Daten bleiben erhalten.
- Die Gewinnquoten werden weiterhin ergänzend aus den Lotto-Archivseiten geladen, da der externe JSON-Feed die Ziehungen mit Zahlen/Superzahl bereitstellt.
- Anleitung in der App und PDF auf v0.4.24 aktualisiert.

## v0.4.23 – Externe Datenbank immer aktuell prüfen

- Ist die externe Lotto-Datenbank aktiviert, wird sie jetzt bei jedem Programmstart erneut geprüft und aktualisiert.
- Auch der Button **„Aktualisieren“** erneuert bei aktivierter externer Datenbank den lokalen historischen Bestand.
- Danach werden die **aktuellen Mittwoch-/Samstag-Ziehungen und Gewinnquoten separat aus der aktuellen Quelle** abgerufen. Damit kann ein eventuell zeitverzögerter Historien-Feed nicht verhindern, dass die aktuellen Zahlen aktualisiert werden.
- Beim Einschalten bleibt der Fortschrittsdialog für den externen Datenbankabruf erhalten.
- Bereits lokal gespeicherte Daten bleiben beim Ausschalten der externen Datenbank erhalten.
- Anleitung in der App und PDF-Anleitung auf v0.4.23 aktualisiert.

## v0.4.22 – Externe Datenbank mit Fortschritt

- Externe LOTTO-6aus49-Historie kann über „Einstellungen“ aktiviert werden.
- Beim ersten Aktivieren wird die vollständige verfügbare Ziehungshistorie als CSV geladen und lokal in `lotto.db` übernommen.
- Ein Fortschrittsfenster zeigt Download, Prüfung und Anzahl der verarbeiteten Ziehungen.
- Bereits lokal vorhandene Daten bleiben beim Ausschalten der externen Datenbank erhalten.
- Gewinnquoten werden weiterhin für konkrete historische Tipps aus den datierten Archivseiten nachgeladen, weil der verwendete Vollhistorien-Feed Zahlen und Superzahl, aber keine neun Gewinnklassen enthält.
- „Aktualisieren“ bleibt der zentrale Aktualisierungsbutton; der doppelte Button „Aktuelle Zahlen & Quoten“ bleibt entfernt.
- Anleitung in der App und PDF-Anleitung aktualisiert.

## v0.4.21 – Menü und Einstellungen

- Einstellungen in die Menüleiste verschoben.
- Externe Lotto-Datenbank als speicherbare Option ergänzt.
- „Aktuelle Zahlen & Quoten“ entfernt, da „Aktualisieren“ dieselbe Aufgabe übernimmt.
- Lokale Lotto-Daten werden beim Ausschalten der externen Datenbank nicht gelöscht.

## v0.4.20 – Gewinnquoten im Aktualisierungsfenster

- Das Fenster „Lotto-Daten aktualisiert“ zeigt jetzt die Geldbeträge der Gewinnquoten je Gewinnklasse.
- Unbesetzte Gewinnklassen werden weiterhin als „unbesetzt“ angezeigt.

## v0.4.19 – Aktuelle Zahlen & Quoten sofort anzeigen

- Nach „Aktuelle Zahlen & Quoten“ werden Zahlen und Gewinnquoten sofort auf der Startseite aktualisiert.
- Gespeicherte Tipps werden anschließend erneut geprüft.

## v0.4.18 – Historische Ziehungen beim Tipp-Prüfen

- Neue Tipps laden die zugehörige historische Ziehung automatisch.
- „Tipp prüfen“ lädt fehlende historische Ziehungen selbst nach.
- Gewinnquoten der historischen Ziehung werden mitgeladen.
- Mehrere Tipps nacheinander bleiben möglich.

## v0.4.17 – Mehrere Tipps nacheinander eingeben

- Nach dem Speichern eines neuen Tipps bleibt das Eingabefenster offen.
- Die Eingabefelder werden für den nächsten Tipp geleert.
- Das Fenster „Meine Lotto-Tipps“ öffnet sich nicht automatisch.

## v0.4.16 – Tippfenster bleibt geschlossen

- Nach dem Speichern eines Tipps wird „Meine Lotto-Tipps“ nicht mehr automatisch geöffnet.

## v0.4.15 – Tipps bearbeiten

- Gespeicherte Tipps können über „Tipp bearbeiten“ geändert werden.
- Zahlen, Superzahl, Name und Tippdatum können bearbeitet werden.
- Der bestehende Datensatz wird aktualisiert statt dupliziert.

## v0.4.14 – Theme-Einstellung in INI

- `data/settings.ini` hinzugefügt.
- Hell/Dunkel wird gespeichert und beim nächsten Start wieder geladen.

## v0.4.13 – Datumszuordnung Mittwoch/Samstag

- `timedelta`-Fehler bei der Tippdatum-Ermittlung behoben.
- Für eigene Tipps kann weiterhin jedes Kalenderdatum eingegeben werden.
- Das Programm ordnet das Datum automatisch der nächsten offiziellen Mittwoch- oder Samstag-Ziehung zu.
- Mittwoch und Samstag bleiben vollständig unterstützt.
- Historische Ziehungen werden weiterhin anhand des konkreten zugeordneten Ziehungsdatums nachgeladen.

## v0.4.11 – Freies Tippdatum mit automatischer Ziehungszuordnung

- Das Tippdatum darf jetzt **jeden gültigen Kalendertag** enthalten.
- Das Programm ordnet den Tipp automatisch der **nächsten Mittwoch- oder Samstag-Ziehung** zu.
- Beispiele: 01.09.2026 → Mittwoch 02.09.2026; 03.09.2026 → Samstag 05.09.2026.
- Die zugeordnete Ziehung wird im Tippfenster sichtbar angezeigt.
- Beim Speichern wird immer das automatisch ermittelte Ziehungsdatum verwendet.

## v0.4.10 – Historische Tipps, Aktualisierung und Darstellung

- Das Ziehungsdatum eines Tipps bestimmt jetzt automatisch Mittwoch oder Samstag.
- Falsch gespeicherte ältere Tipps werden beim Start anhand ihres konkreten Datums korrigiert.
- Alte Tipps werden beim Start und über „Aktualisieren“ erneut geprüft; fehlende historische Ziehungen und Gewinnquoten werden nachgeladen.
- Ein gespeicherter Tipp wird nur noch mit der Ziehung seines exakten Datums verglichen.
- Neuer Button „Aktualisieren“ für aktuelle und historische Lotto-Daten.
- Neue Darstellungsauswahl „Hell“ / „Dunkel“.
- Die funktionierende Gewinnquoten-Auswertung bleibt erhalten.

## v0.4.9 – Freies Tippdatum

- Das Ziehungsdatum eines eigenen Tipps darf frei gewählt werden.
- Die Prüfung, ob das Datum ein Mittwoch oder Samstag sein muss, wurde entfernt.
- Es wird weiterhin geprüft, ob das Datum gültig ist und dem Format TT.MM.JJJJ entspricht.

# CHANGELOG

## v0.4.9
- Fehler bei der Standardauswahl des Ziehungsdatums behoben: Bei einem neuen Tipp wird automatisch der nächste passende Mittwoch bzw. Samstag vorgeschlagen.
- Beim Wechsel zwischen Mittwoch und Samstag wird das vorgeschlagene Datum passend aktualisiert.
- Die manuelle Eingabe historischer Ziehungstermine und die bestehende Gültigkeitsprüfung bleiben erhalten.

## v0.4.8 – Offizielle Superzahl in der Statistik

- Die Statistik enthält jetzt einen eigenen Tab **„Offiziell Superzahl“**.
- Die Superzahlen **0 bis 9** werden mit Anzahl der offiziellen Ziehungen und prozentualem Anteil angezeigt.
- Die Berechnung verwendet ausschließlich die gespeicherten offiziellen Ziehungen und ist von den Simulationsstatistiken getrennt.

## v0.4.7
- Gewinnquoten-Parser korrigiert: Gewinneranzahl und Euro-Quote werden bei flach dargestellten Tabellen nicht mehr zu einem Betrag zusammengezogen.
- Die Lottozahlen-Verarbeitung und Oberfläche bleiben unverändert.

# CHANGELOG

## v0.4.6 – Gewinnquoten sauber aus der Tabelle lesen

- Die Gewinnquoten werden jetzt ausschließlich aus der eigentlichen LOTTO-6aus49-Quotentabelle gelesen.
- „Ausgespielte Gewinnsumme“ bzw. „Ausgezahlte Gewinnsumme“ kann nicht mehr versehentlich als Gewinnquote übernommen werden.
- Unbesetzte Gewinnklassen werden korrekt als **unbesetzt** angezeigt.
- Beispiel 02.09.2026: Klasse 1 und 2 bleiben unbesetzt; Klasse 3 bis 9 zeigen die jeweiligen Quoten.
- Beispiel 29.08.2026: Klasse 1 bleibt unbesetzt; Klasse 2 bis 9 zeigen die jeweiligen Quoten.
- Bereits gespeicherte Quoten werden nicht doppelt angelegt. Nur tatsächlich abweichende/falsche Datensätze werden in place korrigiert.
- Die bisherige Trennung von Mittwoch und Samstag sowie die Reparatur falscher Ziehungszahlen bleiben erhalten.

## v0.4.5 – Gewinnzahlen und Quoten endgültig getrennt

- Gewinnzahlen werden aus dem expliziten Gewinnzahlen-Bereich der Archivseite gelesen.
- Falsche Zahlen aus Datum, „6 aus 49“ oder anderen Seitenelementen werden verhindert.
- Die Quoten-Auswertung endet vor Spiel 77/SUPER 6.
- Falsche bereits gespeicherte Ziehungsdaten werden beim Aktualisieren korrigiert.
- Doppelte Ziehungen werden weiterhin vermieden.
- Das vorhandene `lotto.db` bleibt beim Testen erhalten; die ZIP enthält bewusst keine Datenbankdatei.


## v0.4.3 – Datenabruf korrigiert

- Mittwoch- und Samstag-Ziehung werden getrennt und zuverlässig ermittelt.
- Die Startseite lädt die jeweils letzte **abgeschlossene** Mittwoch- und Samstag-Ziehung.
- Am Samstag vor der Ziehung wird nicht versehentlich die noch nicht gezogene Samstag-Ziehung verwendet.
- Die einzelnen Archivseiten werden direkt nach Datum abgerufen.
- Gewinnquoten werden robuster aus den Archivtabellen gelesen.
- Gewinnklasse 9 (2 Richtige + Superzahl) wird erkannt, wenn die feste Quote 6,00 € auf der Seite ausgewiesen ist.
- Alte gespeicherte Tipps bleiben ihrer konkreten Ziehung zugeordnet.
- Gespeicherte Tipps werden automatisch gegen genau diese historische Ziehung geprüft.
- Gewinnmeldungen erscheinen auch für alte Tipps, sobald die passende Ziehung und Quote verfügbar sind.
- Bereits gemeldete Gewinne werden nicht erneut gemeldet.
- Keine doppelte Speicherung derselben offiziellen Ziehung.

## v0.4.2

- Historische Ziehungen und Quoten für gespeicherte Tipps nachladen.
- Neue Oberfläche mit getrennten Mittwoch-/Samstag-Karten.
- Analyse und Statistik erweitert.
