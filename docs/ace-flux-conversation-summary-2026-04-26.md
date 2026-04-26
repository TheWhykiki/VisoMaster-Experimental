# ACE++ / FLUX Erweiterung: Gesprächszusammenfassung

## Ziel

Das bestehende VisoMaster-Swapping sollte so erweitert werden, dass `FLUX`-Modelle zusammen mit `ACE++`-LoRAs als ganz normaler neuer `Swapper` genutzt werden können.

Wichtige Leitplanken aus dem Gespräch:

- `ACE++ / FLUX` soll kein separates Alternativ-Backend sein.
- Die Logik soll als einzelnes, gekapseltes Python-Modul im bestehenden Swapper-Flow hängen.
- Für das Swapping wird eine Maske benötigt, anfangs reicht eine Vollgesichtsmaske.
- Später soll die Maskenerzeugung optional über `Segment Anything` laufen können.
- Die bestehende `Find Faces`-Funktion soll auch für `ACE++` gelten, damit bei mehreren Personen die richtige Zielperson gewählt wird.

## Vereinbarte Architektur

### 1. ACE++ / FLUX als normaler Swapper

- `ACE++ (FLUX)` wurde als eigener Swapper-Zweig behandelt, nicht als alternatives Gesamtsystem.
- Die FLUX-/ACE++-Logik wurde konzeptionell in ein einzelnes Script ausgelagert:
  - `app/processors/utils/flux_ace_plus.py`
- Der Aufruf erfolgt über die bestehenden Swapper-/ModelsProcessor-/FrameWorker-Pfade.

### 2. Modell- und LoRA-Handling

- FLUX-Basemodelle und ACE++-LoRAs sollen lokal erkannt werden.
- Zusätzlich sollten Auto-Download-Optionen bereitgestellt werden:
  - FLUX Base:
    - `FLUX.1 Fill [dev]`
  - ACE++ LoRAs:
    - Portrait
    - Subject
    - Local Editing
- Downloads sollen im Hintergrund passieren, aber nur innerhalb des ACE++-Swappers.
- Fehler bei fehlender Hugging-Face-Lizenz oder fehlendem Token sollen klar gemeldet werden.

### 3. Maskenstrategie

- Erste Zielversion:
  - eine grobe Vollgesichtsmaske reicht
- Diese Vollgesichtsmaske soll aus den bestehenden Face-Parsing-Komponenten gebaut werden.
- Zusätzlich wurde gefordert:
  - Debug-Ansicht für die Maske direkt im ACE++/FLUX-Modus
  - optionales Einbeziehen von Haaren
  - Steuerung von Masken-Expand und Masken-Blur

### 4. FLUX-spezifische Settings

- FLUX-Parameter sollen nicht permanent sichtbar sein.
- Stattdessen soll es einen zuschaltbaren Bereich geben:
  - Prompt
  - Negative Prompt
  - Steps
  - Guidance
  - True CFG
  - LoRA Strength
  - Seed
  - CPU Offload
  - Source Reference
  - Maskenparameter
  - Crop-Parameter für den FLUX-Target-Crop

### 5. Crop-Logik für ACE++

- Es wurde festgelegt, dass nicht nur das Source-Face, sondern auch das Target vor dem FLUX-Step sinnvoll auf Gesicht/Kopf reduziert werden soll.
- Daraus ergab sich der gewünschte Ablauf:
  1. Zielperson im Bild bestimmen
  2. Source-Face und Target-Face/Head crop erzeugen
  3. FLUX/ACE++ nur auf diesem Crop ausführen
  4. Ergebnis zurück auf die normale Face-Tile mappen
  5. Danach wie gewohnt zurück ins Originalbild pasten
  6. Weiter zum nächsten Frame/Bild

### 6. Mehrpersonen-Szenen und Find Faces

- Die Auswahl der korrekten Zielperson soll weiterhin über die vorhandene `Find Faces`-/Similarity-Logik laufen.
- Die Maskenerzeugung soll davon logisch getrennt sein.
- Für die spätere Zielversion mit `Segment Anything` gilt:
  - `Find Faces` entscheidet, welche Person bearbeitet wird
  - `SAM` baut anschließend die Maske für genau diese gewählte Person

## Umgesetzter Stand im Gespräch

### Bereits umgesetzt bzw. vorbereitet

- `ACE++ (FLUX)` als eigener Swapper-Eintrag
- Kapselung der FLUX-/ACE++-Logik in einem dedizierten Python-Modul
- Auto-Download-Pfade für FLUX Base und ACE++ LoRAs vorbereitet
- Vollgesichtsmaske als vereinfachte Maskenlogik
- zuschaltbare FLUX-Settings in der UI
- Debug-Maskenansicht für ACE++
- separater Target-Crop für FLUX mit eigenen Crop-Parametern
- Remap des FLUX-Ergebnisses zurück in die reguläre Face-Tile vor dem Paste-Back
- klare Trennung:
  - Personenauswahl über `Find Faces`
  - Maskenquelle über einen separaten Mask-Provider

### Explizit noch offen

- echte Integration von `Segment Anything`
- zusätzliche Mask-Provider wie:
  - `SAM 2`
  - `SAM 3`
- möglicher erweiterter Source-Head-Crop statt nur des bisher genutzten Input-Face-Crops
- kompletter End-to-End-Livetest mit funktionierender FLUX-Runtime und installierten Diffusers/PEFT-Komponenten

## Kernaussage des Gesprächs

Die gewünschte Richtung ist klar definiert:

`ACE++ / FLUX` soll sich für den Nutzer wie ein ganz normaler zusätzlicher Swapper in VisoMaster verhalten, intern aber moderne generative Komponenten nutzen. Die Zielperson soll weiter über das bestehende Multi-Person-Matching gewählt werden, während Maske, Crop und FLUX-Verarbeitung als eigene, austauschbare interne Bausteine organisiert werden.
