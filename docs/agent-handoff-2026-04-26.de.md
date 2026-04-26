# VisoMaster Projektstand und Gesprächszusammenfassung

Stand: 2026-04-26

## Zielbild

VisoMaster soll primär auf einem Windows- oder Linux-GPU-Host laufen. Der Mac soll nur als Browser-Client über eine URL genutzt werden. Für den aktuellen Workflow bedeutet das:

- Windows/Linux startet `Start_Web_Network.bat` oder `Start_Web_Network.sh`.
- Der Mac öffnet die WebUI unter der Host-URL, z. B. `http://192.168.178.128:8000/`.
- Die WebUI soll nicht nur Jobs starten, sondern einen nutzbaren Swap-Workflow wie die native App bieten: Target laden, Source-Face laden, Video-Frame wählen, Gesichter finden, geswappte Vorschau sehen und finalen Swap starten.

## Bisher erledigt

- Die WebUI wurde in Richtung einer swap-orientierten Oberfläche erweitert: Media-Bereich, Target/Source-Uploads, Video-Controls, Detection-Frame, Find Faces, Swap Preview, Run und Output-Anzeige.
- Die Layout-Basis wurde in Richtung dockbarer Fensterbereiche mit Golden Layout/Flex-Layout-Idee weiterentwickelt.
- Der Browser-Workflow wurde um klare Schritte ergänzt: Target laden, Source Faces laden, Preview Frame erzeugen, Target Faces finden, Swap Preview prüfen, Run starten.
- 400er-Fehler bei `find-faces` wurden eingegrenzt und die API-/State-Validierung verbessert.
- Playwright-basierte Autotests wurden aufgebaut:
  - `scripts/playwright_flux_swap_audit.py`
  - Stub-Modus für schnelle lokale GUI-/Flow-Validierung
  - Real-Modus gegen den Windows-Host mit echten Dateien
- Quality-Gate wurde erweitert:
  - `scripts/gui_quality_gate.py`
  - Python-Compile
  - JavaScript-Syntax
  - FLUX/ACE++ Tests
  - Model-Discovery Tests
  - Web-Processing-Lifecycle Tests
  - Web-Console-Smoke Tests
- Der Headless-Runner wurde gehärtet:
  - Bootstrap-Status vor schweren Imports
  - bessere Fehlerzustände
  - Stop-/Kill-Handling
  - stale Runner Detection
  - terminale Zustände blockieren nicht mehr als `active=true`
- ComfyUI-Modellpfade werden entdeckt, inklusive Windows-Pfad `E:/ComfyUI_Models/models`.
- Fehlende FLUX/ACE++ Modelle können automatisch heruntergeladen werden.
- Runtime-Abhängigkeiten wurden gehärtet:
  - `huggingface-hub`
  - `imageio-ffmpeg`
  - Starter installieren neue Pflichtpakete nach
  - gebündeltes FFmpeg aus `imageio-ffmpeg` wird für Runner verfügbar gemacht
- Preview-/Find-Faces-Hilfsprozesse blockieren den Statuskanal nicht mehr.
- `/api/processing/status` kann aktive Preview-Helper inklusive `preview_runner.log` melden.

## Echte Testdateien

Auf dem Mac lagen für die realen Tests:

- `/Users/whykiki/Downloads/target.mp4`
- `/Users/whykiki/Downloads/source.jpg`

Erkannte Medienwerte:

- `target.mp4`: Video, ca. 1108x828, 24 FPS, ca. 10 Sekunden, 241 Frames
- `source.jpg`: JPEG, 1200x896

## Reale Testergebnisse gegen Windows-Host

Die echten Playwright-Tests gegen `http://192.168.178.128:8000` kamen erfolgreich durch:

- Target Upload
- Source Upload
- Preview Frame
- Find Faces
- Erkennung von 1 Zielgesicht
- Registrierung und Anzeige des Workflow-Zustands

Danach wurden mehrere echte Host-Probleme sichtbar und schrittweise behoben:

- `huggingface_hub` fehlte zuerst für FLUX-Autodownloads.
- FFmpeg war nicht im Windows-PATH.
- Nach Fehlern blieb der Processing-Status teilweise als `active=true` hängen.
- Während Flux Preview lief, blockierte der Server zunächst Statusabfragen.
- Danach war der Statuskanal erreichbar, aber zunächst wurde noch der falsche Hauptlog statt `preview_runner.log` angezeigt.
- Nach der Korrektur zeigte der richtige Preview-Status, dass FLUX-Modell und LoRA laden, der Prozess aber nach dem Pipeline-Load vor bzw. innerhalb der FLUX-Inferenz hängen blieb.

## Aktueller Fix im Arbeitsstand

Der aktuelle Stand enthält zusätzliche Diagnose- und Stabilitätsverbesserungen für genau diesen FLUX-Preview-Hänger:

- Schnelle FLUX-Preview im Headless-Preview-Modus:
  - maximal 4 Inferenzschritte
  - reduzierte `FluxMaxSequenceLengthSlider` auf maximal 256
- FLUX-Inferenz schreibt jetzt klare Logpunkte:
  - Start der Inferenz
  - Größe, Steps, Device, CPU-Offload
  - Step-Fortschritt, wenn die Pipeline Callback-Parameter unterstützt
  - Abschluss der Inferenz
- Helper-Prozesse bekommen ein Timeout:
  - `VISOMASTER_WEB_HELPER_TIMEOUT_SECONDS`
  - Standard: 900 Sekunden

## Verifizierte Tests

Vor diesem Handoff wurden lokal erfolgreich ausgeführt:

```bash
python3 scripts/gui_quality_gate.py
python3 scripts/playwright_flux_swap_audit.py --mode stub --timeout-ms 60000
```

Zusätzlich wurden gezielt geprüft:

```bash
python3 -m py_compile app/web/headless_runner.py app/processors/utils/flux_ace_plus.py app/services/web_processing.py
python3 -m unittest tests.test_flux_ace_plus tests.test_web_processing_lifecycle
```

## Aktueller Git-Stand beim Handoff

Letzte bekannte Remote-Commits vor diesem Dokument:

- `e73d815 Report active Flux preview helper status`
- `98393fd Keep status responsive during Flux previews`
- `2ece7c8 Harden Flux web runtime dependencies`
- `0ee989e Fallback to Flux downloads when models are missing`
- `5456856 Discover Flux models from ComfyUI paths`
- `aa4183c Harden web headless runner lifecycle`

Dieses Dokument und der aktuelle Diagnose-/Timeout-Fix sollen zusammen gepusht werden, damit ein Windows-Codex-Agent direkt auf demselben Stand weiterarbeiten kann.

## Nächste empfohlene Schritte

1. Auf dem Windows-GPU-Host `git pull` ausführen.
2. `Start_Web_Network.bat` starten.
3. Realen Test starten:

```bash
python3 scripts/playwright_flux_swap_audit.py --mode real --url http://192.168.178.128:8000 --target /Users/whykiki/Downloads/target.mp4 --source /Users/whykiki/Downloads/source.jpg --timeout-ms 900000
```

4. Während `Swap Preview` läuft, `/api/processing/status` beobachten.
5. Entscheidend ist jetzt, ob im `preview_runner.log` neue Einträge wie `ACE++ (FLUX): starting inference` und einzelne Inferenzschritte erscheinen.
6. Falls es erneut hängt, liegt der Engpass nicht mehr in Upload, Detection, API, Statuskanal oder Modell-Download, sondern sehr wahrscheinlich in der eigentlichen FLUX-Inferenz, GPU/VRAM, CPU-Offload oder Diffusers-Konfiguration.

## Empfehlung für weniger manuelle Tests

Damit der Nutzer nicht ständig selbst Tests anstoßen muss, sollte als nächstes ein Windows-Orchestrator angelegt werden:

- `scripts/windows_selftest.ps1`
- Aufgaben:
  - `git pull`
  - alte Python-/Runner-Prozesse beenden
  - `Start_Web_Network.bat` starten
  - Healthcheck auf `/api/status`
  - Playwright-Realtest ausführen
  - Logs sammeln
  - Exit-Code und Kurzbericht ausgeben

Noch besser wäre Codex direkt auf dem Windows-Rechner im Projektordner `C:\GIT\VisoMaster-Experimental`, weil Codex dort dann den GPU-Host-Prozess, Logs, FFmpeg, Modelle und Playwright ohne Mac-/Remote-Umweg steuern kann.
