# Hilfe zur VisoMaster Web-Konsole

Diese Dokumentation beschreibt die aktuelle browserfaehige Verwaltungsoberflaeche von VisoMaster-Fusion. Sie ergaenzt die integrierte Hilfe in der Web-Konsole und richtet sich an Anwender, die Jobs, Presets, Embeddings und den letzten Arbeitsbereich gezielt pruefen oder bearbeiten moechten.

## Einstieg

Die Web-Konsole ist eine Verwaltungsoberflaeche fuer Projektdateien. Die eigentliche Medienverarbeitung laeuft weiterhin primaer ueber die Desktop-Anwendung.

Typischer Ablauf:

1. `Start_Web.bat` oder `Start_Web_Network.bat` starten
2. Web-Konsole im Browser oeffnen
3. Bereich auswaehlen: Status, Jobs, Presets, Embeddings oder Arbeitsbereich
4. Eintrag anklicken, JSON pruefen und bei Bedarf speichern

## Hilfe direkt in der Oberflaeche

Die Web-Konsole enthaelt jetzt zwei schnelle Wege zur Erklaerung:

- `Schnellhilfe` im Kopfbereich oeffnet die zentrale Dokumentationsflaeche
- Fragezeichen-Buttons neben Bereichen springen direkt zur passenden Erklaerung

Damit gelangst du mit einem oder zwei Klicks zur Beschreibung der gerade sichtbaren Funktion.

## Funktionsbereiche

### Systemstatus

Hier siehst du:

- Plattform und Python-Version
- erkannte FFmpeg-Tools
- Anzahl der gefundenen Jobs, Presets und Embeddings

Das hilft beim schnellen Pruefen, ob die Umgebung laeuft und ob Projektdaten verfuegbar sind.

### Jobs

Jobs sind gespeicherte Arbeitsauftraege fuer die Desktop-Verarbeitung. Sie enthalten typischerweise:

- Zielmedien
- Quellgesichter
- Zielgesichter
- Marker
- weitere Verarbeitungseinstellungen

In der Web-Konsole kannst du Jobs laden, im JSON-Editor pruefen und wieder speichern.

### Job-Exporte

Job-Exporte sind eigenstaendige JSON-Dateien fuer den Austausch oder fuer getrennte Verarbeitungsschritte. Sie lassen sich wie Jobs oeffnen und bearbeiten, sind aber als Exportform gedacht.

### Presets

Ein Preset besteht aus zwei Teilen:

- `parameters`
- `control`

Die Web-Konsole fuehrt beide Teile gemeinsam in einer Ansicht zusammen. Beim Speichern werden daraus wieder die zugehoerigen Dateien im Projekt abgelegt.

### Embeddings

Embeddings sind kompatible JSON-Dateien mit:

- einem Namen
- einem `embedding_store`
- einem oder mehreren Modellvektoren

Die Konsole zeigt Zusammenfassungen wie Modellanzahl und Vektordimensionen an.

### Letzter Arbeitsbereich

Der letzte Arbeitsbereich spiegelt den zuletzt gespeicherten Projektzustand wider. Er ist praktisch, wenn du den aktuellen Stand schnell pruefen oder gezielt korrigieren moechtest, ohne erst mehrere Einzeldateien zu laden.

## JSON-Editor

Der JSON-Editor ist die zentrale Bearbeitungsflaeche fuer:

- Jobs
- Job-Exporte
- Presets
- Embeddings
- `last_workspace.json`

Hinweise:

- Der Name eines Eintrags darf nicht leer sein
- Presets sollten die Bereiche `parameters` und `control` enthalten
- Ungueltiges JSON blockiert das Speichern

## Embedding-Builder

Mit dem Embedding-Builder kannst du ein Embedding ohne manuelles Rohformat bauen.

Empfohlener Ablauf:

1. Dateiname oder Embedding-Name eintragen
2. Modellname setzen
3. Vektorwerte als JSON-Array oder komma-/zeilengetrennte Zahlen einfuegen
4. `Modell hinzufuegen` klicken
5. Vorschau pruefen
6. `Embedding speichern` ausfuehren

## Wann die Web-Konsole sinnvoll ist

Die Web-Konsole eignet sich besonders fuer:

- schnelle Kontrolle von Projektdateien
- Korrektur von JSON-Daten
- Verwaltung von Presets und Embeddings
- Einsicht in den zuletzt gespeicherten Arbeitsbereich

Fuer eigentliche Vorschau, Face-Swap-Konfiguration und Verarbeitung bleibt die Desktop-GUI die Hauptoberflaeche.
