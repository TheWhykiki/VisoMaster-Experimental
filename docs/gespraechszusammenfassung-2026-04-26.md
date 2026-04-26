# Gespraechszusammenfassung vom 26.04.2026

## Ausgangslage

Im Verlauf dieses Gespraechs stand VisoMaster-Experimental im Fokus mit drei grossen Zielen:

1. Das Projekt unter Windows wieder sauber nutzbar und installierbar machen.
2. Die originale Desktop-GUI erhalten.
3. Zusaetzlich einen sinnvollen Browser- und Netzwerkzugang aufbauen, damit Verarbeitung auch remote angestossen werden kann.

## Wichtigste Entscheidungen

- Die native Desktop-GUI bleibt erhalten und wird nicht durch die Weboberflaeche ersetzt.
- Die Weboberflaeche wird nicht als zweite, komplett getrennte Verarbeitungslogik gebaut, sondern nutzt schrittweise die bestehende Desktop-Pipeline im Hintergrund weiter.
- Fuer Browser-Betrieb wurde zuerst ein Verwaltungs- und Status-Layer aufgebaut, danach eine echte Headless-Ausfuehrung ueber einen versteckten Runner.
- Der langfristige Zielpfad bleibt: Verarbeitungslogik weiter aus Qt herausloesen und spaeter noch sauberer als echten Service betreiben.

## Umgesetzte Themen im Verlauf

### 1. Windows-Start und Installation

Es wurden mehrere Probleme in den Windows-Startern und der Installation identifiziert und behoben:

- falscher oder unpassender Portable-Startpfad
- Batch-Starter schlossen sich bei Fehlern sofort
- `.venv`, `conda`, System-Python und Runtime-Erkennung waren nicht robust genug
- automatisches Anlegen des `visomaster`-Conda-Environments und Installieren der Requirements fehlte

Ziel war, dass `Start.bat`, `Start_Web.bat`, `Start_Web_Network.bat` und `Start_Portable.bat` unter Windows nachvollziehbar starten, Fehler anzeigen und die benoetigte Python-Umgebung besser vorbereiten koennen.

### 2. GUI plus Web-/Netzwerk-Modus

Es wurde eine klare Trennung der Startmodi eingefuehrt:

- Desktop-GUI weiter ueber `main.py` und die Desktop-Starter
- Web-Konsole lokal
- Web-Konsole im LAN bzw. Netzwerk
- Portable-Varianten fuer diese Modi

Die Grundidee war von Anfang an, dass Desktop und Browser parallel existieren und nicht gegeneinander ausgespielt werden.

### 3. Browser-Konsole

Die Web-Konsole wurde zunaechst als browserfaehige Verwaltungsoberflaeche aufgebaut fuer:

- Status
- Jobs
- Job-Exporte
- Presets
- Embeddings
- letzten Arbeitsbereich

Danach wurde klar, dass das fuer den praktischen Nutzen nicht reicht, weil ein echter Face-Swap-Start im Browser fehlte.

### 4. Echte Browser-Verarbeitung ueber gespeicherte Jobs

Daraufhin wurde die naechste Stufe umgesetzt:

- ein Web-Processing-Service fuer Status, Logs und Prozessverwaltung
- ein versteckter Headless-Runner auf Basis der vorhandenen Qt-/Desktop-Pipeline
- API-Endpunkte zum Starten, Stoppen und Beobachten von Verarbeitungslaeufen
- eine Browser-Oberflaeche mit Status, Fortschritt, Log und Ausgabe-Link

Damit koennen gespeicherte Jobs inzwischen direkt aus der Weboberflaeche gestartet werden, ohne die Desktop-GUI zu entfernen.

### 5. Direkter Browser-Upload ohne vorab gespeicherten Job

Im letzten grossen Schritt wurde ein zusaetzlicher Schnellworkflow aufgebaut:

- Zielmedium im Browser hochladen
- Quellgesicht(er) im Browser hochladen
- optional einen Erkennungsframe bei Videos vorgeben
- Direktlauf aus dem Browser starten

Aktuell wird dabei das erste erkannte Quellgesicht auf alle erkannten Zielgesichter angewendet. Das ist bewusst die erste sinnvolle Remote-Stufe, noch nicht die vollstaendige browserseitige Zielgesicht-zu-Quellgesicht-Zuordnung.

## Branches, Pushes und Repo-Struktur

Im Verlauf wurden die zwischenzeitlichen Arbeiten konsolidiert:

- Arbeitsstaende wurden auf einen eigenen Branch gepusht
- daraus wurde spaeter ein gemeinsamer `main`-Stand gemacht
- alte Zwischen-Branches wurden anschliessend aufgeraeumt

Danach wurde der aktuelle Entwicklungsstand auf `main` weitergefuehrt.

## Uebersetzung und Dokumentation

Es wurde zusaetzlich eine sinnvolle deutsche Ebene eingezogen:

- deutsche Uebersetzung zentraler Oberflaechenteile
- deutsche Web-Hilfen
- deutsche README-Ergaenzungen
- eigene deutschsprachige Dokumentationsdateien

Ziel war nicht nur kosmetische Uebersetzung, sondern ein besserer Einstieg in Desktop- und Web-Nutzung.

## Aktueller technischer Stand zum Ende dieses Gespraechs

### Desktop

- Die originale GUI ist weiterhin der vollwertige Hauptmodus.
- Die lokale Pipeline mit Qt, Torch/ONNX, FFmpeg und den vorhandenen Swappern bleibt intakt.

### Web

- Die Web-Konsole ist vorhanden.
- Gespeicherte Jobs koennen remote gestartet und beobachtet werden.
- Ein Direkt-Upload-Workflow ohne vorher gespeicherten Job ist vorhanden.
- Status, Fortschritt, Runner-Log und Ausgabe-Link sind im Browser sichtbar.

### FLUX / ACE++

Im aktuellen Arbeitsbaum liegen zusaetzlich noch weitere Anpassungen fuer FLUX / ACE++:

- detailliertere Inferenz-Logs in `app/processors/utils/flux_ace_plus.py`
- ein Timeout fuer Browser-Hilfsverarbeitung in `app/services/web_processing.py`
- eine schnellere FLUX-Vorschau fuer Preview-Laeufe in `app/web/headless_runner.py`

Diese Aenderungen sind Teil des aktuellen Arbeitsstands, der zusammen mit dieser Zusammenfassung gepusht wird.

## Noch offene oder bewusst bekannte Grenzen

- Die Web-Verarbeitung basiert noch stark auf der bestehenden Desktop-Architektur und ist noch kein komplett entkoppelter Service.
- Der Direkt-Upload ist noch ein Schnellworkflow und noch keine vollstaendige browserseitige Multi-Face-Zuordnung.
- Echte End-to-End-Tests unter Windows und mit realen Medien muessen weiterhin in der Zielumgebung validiert werden.
- Langfristig bleibt die weitere Entkopplung der Kernpipeline von `MainWindow` der sinnvollste Architekturpfad.

## Kurzfazit

Aus einem urspruenglich schwer nutzbaren Stand wurden schrittweise folgende Ergebnisse erreicht:

- Windows-Starter und Installationspfad wurden robuster gemacht.
- Die originale Desktop-GUI blieb erhalten.
- Eine zusaetzliche Web- und Netzwerkoberflaeche wurde aufgebaut.
- Aus der anfaenglichen Verwaltungsoberflaeche wurde eine erste echte Remote-Verarbeitung.
- Zusaetzlich gibt es jetzt einen direkten Browser-Upload-Workflow als naechste Ausbaustufe.

Damit ist das Projekt heute deutlich naeher an einem parallelen Desktop-und-Web-Betriebsmodell als zu Beginn dieses Gespraechs.
