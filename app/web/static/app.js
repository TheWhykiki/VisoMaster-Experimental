const state = {
  selection: null,
  helpTopic: "overview",
  helpCollapsed: false,
  processingPollHandle: null,
  browserWorkflow: null,
  collections: {
    jobs: [],
    "job-exports": [],
    presets: [],
    embeddings: [],
  },
  processing: null,
  embeddingDraft: {
    fileName: "",
    name: "",
    embedding_store: {},
  },
};

const jobsList = document.getElementById("jobsList");
const jobExportsList = document.getElementById("jobExportsList");
const presetsList = document.getElementById("presetsList");
const embeddingsList = document.getElementById("embeddingsList");
const workspaceSummary = document.getElementById("workspaceSummary");
const statusCards = document.getElementById("statusCards");
const statusBadge = document.getElementById("statusBadge");
const statusSummaryEyebrow = document.getElementById("statusSummaryEyebrow");
const statusSummaryTitle = document.getElementById("statusSummaryTitle");
const statusSummaryText = document.getElementById("statusSummaryText");
const statusSummaryNote = document.getElementById("statusSummaryNote");
const statusOverallPercent = document.getElementById("statusOverallPercent");
const statusOverallLabel = document.getElementById("statusOverallLabel");
const statusAreas = document.getElementById("statusAreas");
const nameInput = document.getElementById("nameInput");
const jsonEditor = document.getElementById("jsonEditor");
const editorTitle = document.getElementById("editorTitle");
const editorSubtitle = document.getElementById("editorSubtitle");
const saveButton = document.getElementById("saveButton");
const deleteButton = document.getElementById("deleteButton");
const flashMessage = document.getElementById("flashMessage");
const processingBadge = document.getElementById("processingBadge");
const processingMessage = document.getElementById("processingMessage");
const processingMeta = document.getElementById("processingMeta");
const processingSelection = document.getElementById("processingSelection");
const processingOutput = document.getElementById("processingOutput");
const processingLog = document.getElementById("processingLog");
const processingRefreshButton = document.getElementById("processingRefreshButton");
const processingStartButton = document.getElementById("processingStartButton");
const processingStopButton = document.getElementById("processingStopButton");
const processingProgress = document.getElementById("processingProgress");
const processingProgressValue = document.getElementById("processingProgressValue");
const workflowSummary = document.getElementById("workflowSummary");
const workflowResetButton = document.getElementById("workflowResetButton");
const workflowRunButton = document.getElementById("workflowRunButton");
const targetUploadInput = document.getElementById("targetUploadInput");
const sourceUploadInput = document.getElementById("sourceUploadInput");
const uploadTargetButton = document.getElementById("uploadTargetButton");
const uploadSourcesButton = document.getElementById("uploadSourcesButton");
const detectionFrameInput = document.getElementById("detectionFrameInput");

const builderFileName = document.getElementById("builderFileName");
const builderEmbeddingName = document.getElementById("builderEmbeddingName");
const builderModelName = document.getElementById("builderModelName");
const builderVectorInput = document.getElementById("builderVectorInput");
const builderAddModelButton = document.getElementById("builderAddModelButton");
const builderSaveButton = document.getElementById("builderSaveButton");
const builderResetButton = document.getElementById("builderResetButton");
const builderModelList = document.getElementById("builderModelList");
const builderPreview = document.getElementById("builderPreview");
const builderStats = document.getElementById("builderStats");
const helpPanel = document.getElementById("helpPanel");
const helpPanelBody = document.getElementById("helpPanelBody");
const openHelpButton = document.getElementById("openHelpButton");
const helpOverviewButton = document.getElementById("helpOverviewButton");
const helpToggleButton = document.getElementById("helpToggleButton");
const helpTopicEyebrow = document.getElementById("helpTopicEyebrow");
const helpTopicTitle = document.getElementById("helpTopicTitle");
const helpTopicSummary = document.getElementById("helpTopicSummary");
const helpTopicSteps = document.getElementById("helpTopicSteps");
const helpTopicNotes = document.getElementById("helpTopicNotes");
const helpTopicContext = document.getElementById("helpTopicContext");

const HELP_TOPICS = {
  overview: {
    eyebrow: "Schnellstart",
    title: "So findest du dich schnell zurecht",
    summary:
      "Die Web-Konsole ist fuer den Remote-Betrieb gedacht: Browser auf dem Mac oder einem anderen Client, GPU-Host auf Windows oder Linux. Mit wenigen Klicks springst du von der Uebersicht direkt in Jobs, Presets, Embeddings, den letzten Arbeitsbereich oder einen laufenden Browser-Job.",
    steps: [
      "Starte VisoMaster auf dem Windows- oder Linux-Host im Netzwerkmodus und oeffne danach die ausgegebene URL auf dem Mac im Browser.",
      "Pruefe zuerst den Systemstatus, damit du sofort siehst, ob Host-Runtime, Netzwerkmodus und Projektdaten verfuegbar sind.",
      "Oeffne danach in den Projektdaten den Bereich, den du bearbeiten willst, und klicke auf den gewuenschten Eintrag.",
      "Nutze anschliessend den JSON-Editor oder den Embedding-Builder, um Daten sicher zu pruefen und zu speichern oder direkt einen Lauf zu starten.",
    ],
    notes: [
      "Der Mac dient dabei idealerweise nur als Browser-Client und nicht als GPU-Verarbeitungshost.",
      "Die Web-Konsole kann gespeicherte Jobs jetzt direkt ueber die bestehende Desktop-Pipeline auf dem Remote-Host starten.",
      "Die Fragezeichen neben den Bereichen fuehren immer direkt zur passenden Erlaeuterung.",
      "Mit dem Button 'Schnellhilfe' oeffnest du diese Dokumentation jederzeit erneut.",
    ],
    context:
      "Besonders praktisch ist die Konsole fuer einen Mac-Client, der nur ueber URL auf einen staerkeren Windows- oder Linux-Rechner zugreift.",
  },
  status: {
    eyebrow: "Status",
    title: "Systemstatus lesen",
    summary:
      "Hier siehst du auf einen Blick, wie weit der aktuelle Remote-Meilenstein ausgebaut ist, welche Host-Runtime aktiv ist und wie der Browser-Client gedacht ist.",
    steps: [
      "Klicke auf 'Aktualisieren', um Remote-Bewertung, Deployment-Profil, Runtime-Informationen und Dateizaehler neu einzulesen.",
      "Pruefe zuerst die 100%-Karten pro Bereich und danach das Deployment- und Runtime-Profil mit Host- und Client-Rollen.",
      "Nutze die Zaehler fuer Jobs, Presets und Embeddings als schnellen Gesundheitscheck deines Projekts.",
    ],
    notes: [
      "Die Prozentwerte beziehen sich auf den aktuellen Remote-Meilenstein des Projekts und nicht auf spaetere, bewusst getrennte Zukunftsausbaustufen.",
      "Die Runtime-Karten unterscheiden bewusst zwischen Browser-Client-Kontext und der starter-verwalteten Host-Runtime.",
      "Wenn Zaehler auf null stehen, fehlen oft Dateien oder das Projekt wurde noch nicht befuellt.",
      "Ein Mac darf hier bewusst nur Client sein; der GPU-Host soll auf Windows oder Linux laufen.",
    ],
    context:
      "Der Statusbereich eignet sich als erster Stopp vor jeder Bearbeitung oder Fehlersuche.",
  },
  collections: {
    eyebrow: "Projektdaten",
    title: "Dateisammlungen verstehen",
    summary:
      "Die Projektdaten gruppieren die wichtigsten JSON-basierten Arbeitsdateien, damit du sie ohne Dateibrowser oeffnen und bearbeiten kannst.",
    steps: [
      "Waehle die passende Sammlung wie Jobs, Presets oder Embeddings.",
      "Lade die Liste bei Bedarf mit 'Neu laden' fruehzeitig nach.",
      "Klicke auf einen Eintrag, um ihn sofort im Editor oder in der passenden Vorschau zu oeffnen.",
    ],
    notes: [
      "Jede Karte zeigt eine eigene Sammlung aus dem Projektordner an.",
      "Die Metazeile unter jedem Eintrag hilft bei der Einordnung, etwa ueber Zeitstempel oder Dimensionen.",
      "Ungueltiges JSON wird markiert, damit fehlerhafte Dateien schneller auffallen.",
    ],
    context:
      "So gelangst du in ein bis zwei Klicks von der Sammlung direkt zur konkreten Datei.",
  },
  jobs: {
    eyebrow: "Jobs",
    title: "Jobs gezielt pruefen",
    summary:
      "Jobs beschreiben Arbeitsauftraege fuer die Desktop-Verarbeitung, zum Beispiel mit Zielmedien, Gesichtern, Markern und weiteren Einstellungen. Sie sind jetzt auch der Startpunkt fuer die Browser-Verarbeitung.",
    steps: [
      "Waehle einen Job aus der Liste aus, um seine JSON-Struktur zu laden.",
      "Pruefe im Editor Namen, Zielgesichter, Marker und weitere gespeicherte Daten.",
      "Starte denselben Job anschliessend im Bereich 'Browser-Verarbeitung', wenn du ihn ueber das Netzwerk ausfuehren willst.",
    ],
    notes: [
      "Jobs sind fuer die Warteschlange gedacht und bilden haeufig den vollstaendigsten Arbeitsauftrag ab.",
      "Die Metainfos in der Liste zeigen unter anderem Marker- und Zielgesicht-Anzahlen.",
      "Ein geloeschter Job verschwindet sofort aus der Sammlung und muss bei Bedarf neu angelegt werden.",
    ],
    context:
      "Wenn du portable oder getrennt exportierte Varianten brauchst, schau dir zusaetzlich die Job-Exporte an.",
  },
  processing: {
    eyebrow: "Browser-Swap",
    title: "Jobs im Browser starten",
    summary:
      "Die Browser-Verarbeitung nutzt die bestehende Desktop-Pipeline auf dem GPU-Host im Hintergrund. Du startest also keinen zweiten, abgespeckten Algorithmus, sondern denselben gespeicherten Job oder einen Direkt-Upload ueber einen versteckten Runner.",
    steps: [
      "Entweder einen gespeicherten Job aus der Job-Liste oeffnen oder Zielmedium und Quellgesicht direkt im Upload-Bereich hochladen.",
      "Im Bereich 'Browser-Verarbeitung' den passenden Start ausloesen und Status, Fortschritt und Log beobachten.",
      "Nach erfolgreichem Lauf findest du dort den Ausgabepfad und kannst die Datei direkt ueber den Download-Link abrufen.",
    ],
    notes: [
      "Der Direkt-Upload ist bewusst ein Schnellworkflow: Das erste erkannte Quellgesicht wird auf alle erkannten Zielgesichter angewendet.",
      "Desktop-GUI und Browser-Modus nutzen dieselbe Host-Runtime, daher muessen Modelle, FFmpeg und Ausgabepfade weiterhin auf dem Windows- oder Linux-Host verfuegbar sein.",
      "Wenn ein Job keinen Output-Ordner gesetzt hat oder im Upload-Lauf keine Gesichter erkannt werden, bricht der Runner mit einer klaren Fehlermeldung ab.",
    ],
    context:
      "So bekommst du echte Remote-Ausfuehrung vom Mac aus, ohne die bestehende Desktop-Verarbeitung komplett neu bauen zu muessen.",
  },
  "job-exports": {
    eyebrow: "Job-Exporte",
    title: "Exportierte Jobs einordnen",
    summary:
      "Job-Exporte sind eigenstaendige JSON-Dateien fuer Austausch, Sicherung oder getrennte Verarbeitungsschritte. Sie lassen sich genauso direkt oeffnen wie normale Jobs.",
    steps: [
      "Lade die Exportliste neu, wenn neue Dateien ausserhalb der Konsole erzeugt wurden.",
      "Oeffne den gewuenschten Export und kontrolliere den JSON-Inhalt im Editor.",
      "Speichere Anpassungen oder loesche veraltete Exportdateien direkt aus der Ansicht.",
    ],
    notes: [
      "Exportdateien sind oft kompaktere Zwischenstaende fuer Weitergabe oder Ruecksicherung.",
      "Die Bearbeitung funktioniert wie bei Jobs, die Sammlung ist aber getrennt.",
      "Beim Aufraeumen lohnt sich ein Blick auf das Aenderungsdatum in der Liste.",
    ],
    context:
      "Wenn du unsicher bist, starte ueber die Schnellhilfe oder ueber das Fragezeichen neben 'Job-Exporte'.",
  },
  presets: {
    eyebrow: "Presets",
    title: "Presets sicher bearbeiten",
    summary:
      "Ein Preset kombiniert Parameter-JSON und Control-JSON. Die Web-Konsole fuehrt beide Teile in einer gemeinsamen Bearbeitungsansicht zusammen.",
    steps: [
      "Oeffne ein Preset, um die zusammengefuehrte Struktur im Editor zu sehen.",
      "Halte die Bereiche 'parameters' und 'control' sauber getrennt, wenn du Inhalte bearbeitest.",
      "Speichere das Preset, damit beide zugehoerigen Dateien im Projekt aktualisiert werden.",
    ],
    notes: [
      "Presets helfen, wiederkehrende Einstellungen schnell erneut zu nutzen.",
      "Wenn ein Control-Teil fehlt, kann die Konsole ihn beim Speichern neu anlegen.",
      "Ein leerer oder ungueltiger Aufbau fuehrt leicht zu unvollstaendigen Presets.",
    ],
    context:
      "Presets sind ideal, wenn du wiederkehrende Konfigurationen statt kompletter Jobs sichern willst.",
  },
  embeddings: {
    eyebrow: "Embeddings",
    title: "Embedding-Dateien verstehen",
    summary:
      "Embeddings bestehen aus einem Namen und einem embedding_store mit einem oder mehreren Modellvektoren. Die Liste zeigt dir dazu direkt Modelle und Dimensionen an.",
    steps: [
      "Waehle ein Embedding aus der Liste, um die validierte JSON-Struktur zu laden.",
      "Pruefe im Editor Namen und embedding_store oder uebernimm die Daten in den Builder.",
      "Nutze den Builder, wenn du Modellvektoren komfortabler hinzufuegen oder umbauen willst.",
    ],
    notes: [
      "Jeder Modellvektor muss numerisch und nicht leer sein.",
      "Die Konsole validiert Embeddings strenger als einfache Roh-JSON-Dateien.",
      "Mehrere Modelle in einer Datei sind moeglich, sofern sie im embedding_store sauber benannt sind.",
    ],
    context:
      "Die Detailansicht und der Builder greifen ineinander, damit manuelle Eingaben weniger fehleranfaellig werden.",
  },
  workspace: {
    eyebrow: "Arbeitsbereich",
    title: "Letzten Arbeitsbereich nutzen",
    summary:
      "Der letzte Arbeitsbereich spiegelt den zuletzt gespeicherten Projektzustand wider und ist der schnellste Weg, um einen Gesamtstand zu kontrollieren oder zu korrigieren.",
    steps: [
      "Klicke auf 'Oeffnen', um last_workspace.json direkt in den Editor zu laden.",
      "Pruefe Zielmedien, Quellgesichter, Zielgesichter und Marker in einer einzigen Datei.",
      "Speichere deine Aenderungen, wenn der Projektzustand angepasst werden soll.",
    ],
    notes: [
      "Diese Datei ist keine Sammlung mehrerer Eintraege, sondern ein einzelner Projektzustand.",
      "Die Zusammenfassung zeigt zentrale Kennzahlen schon vor dem Oeffnen an.",
      "Aenderungen wirken sich auf den zuletzt gespeicherten Workspace aus.",
    ],
    context:
      "Der Workspace ist besonders hilfreich, wenn du schnell den Gesamtzustand statt nur einzelner Jobs pruefen willst.",
  },
  editor: {
    eyebrow: "Editor",
    title: "JSON-Editor effektiv verwenden",
    summary:
      "Der Editor ist die zentrale Bearbeitungsflaeche fuer Jobs, Exporte, Presets, Embeddings und den letzten Arbeitsbereich.",
    steps: [
      "Oeffne zuerst einen Eintrag aus einer Sammlung oder den letzten Arbeitsbereich.",
      "Passe Name und JSON nur mit gueltiger Struktur an, bevor du speicherst.",
      "Nutze 'Loeschen' nur fuer Sammlungsobjekte, nicht fuer den Workspace.",
    ],
    notes: [
      "Ein leerer Name blockiert das Speichern bei sammlungsbasierten Eintraegen.",
      "Presets werden intern wieder in Parameter- und Control-Datei aufgeteilt.",
      "Fehlerhaftes JSON fuehrt zu einer klaren Rueckmeldung im Flash-Bereich.",
    ],
    context:
      "Wenn du nicht sicher bist, welche Struktur erwartet wird, oeffne erst einen vorhandenen Eintrag als Vorlage.",
  },
  builder: {
    eyebrow: "Builder",
    title: "Embeddings mit dem Builder erstellen",
    summary:
      "Der Embedding-Builder fuehrt dich von Rohzahlen zu einer kompatiblen Embedding-Datei. So musst du die JSON-Struktur nicht komplett von Hand schreiben.",
    steps: [
      "Vergib einen Dateinamen oder Embedding-Namen und setze danach den Modellnamen.",
      "Fuege Vektorwerte als JSON-Array oder als komma-, leerzeichen- oder zeilengetrennte Zahlen ein.",
      "Klicke auf 'Modell hinzufuegen', pruefe die Vorschau und speichere erst danach das Embedding.",
    ],
    notes: [
      "Mehrere Modelle koennen nacheinander in denselben Entwurf aufgenommen werden.",
      "Die Vorschau zeigt genau das JSON, das spaeter gespeichert wird.",
      "Beim Laden eines Embeddings wird der Builder automatisch mit den vorhandenen Daten befuellt.",
    ],
    context:
      "Der Builder ist die sicherste Option, wenn du neue Embeddings erzeugen oder bestehende erweitern willst.",
  },
};

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = payload?.error || payload?.message || response.statusText;
    throw new Error(message);
  }

  return payload;
}

async function uploadRequest(url, files) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = payload?.error || payload?.message || response.statusText;
    throw new Error(message);
  }

  return payload;
}

function showFlash(message, isError = false) {
  flashMessage.hidden = false;
  flashMessage.className = isError ? "flash error" : "flash";
  flashMessage.textContent = message;
}

function clearFlash() {
  flashMessage.hidden = true;
  flashMessage.textContent = "";
  flashMessage.className = "flash";
}

function createHelpListItems(target, items, ordered = false) {
  target.innerHTML = "";
  items.forEach((item) => {
    const entry = document.createElement("li");
    if (!ordered) {
      entry.textContent = item;
    } else {
      const text = document.createElement("span");
      text.textContent = item;
      entry.appendChild(text);
    }
    target.appendChild(entry);
  });
}

function updateHelpButtonState(topic) {
  document.querySelectorAll("[data-help-topic]").forEach((element) => {
    element.classList.toggle("is-active", element.dataset.helpTopic === topic);
  });
}

function renderHelpTopic(topic) {
  const nextTopic = HELP_TOPICS[topic] ? topic : "overview";
  const entry = HELP_TOPICS[nextTopic];
  state.helpTopic = nextTopic;
  helpTopicEyebrow.textContent = entry.eyebrow;
  helpTopicTitle.textContent = entry.title;
  helpTopicSummary.textContent = entry.summary;
  createHelpListItems(helpTopicSteps, entry.steps, true);
  createHelpListItems(helpTopicNotes, entry.notes);
  helpTopicContext.textContent = entry.context;
  updateHelpButtonState(nextTopic);
}

function setHelpCollapsed(collapsed) {
  state.helpCollapsed = collapsed;
  helpPanel.classList.toggle("collapsed", collapsed);
  helpPanelBody.hidden = collapsed;
  helpToggleButton.textContent = collapsed ? "Hilfe anzeigen" : "Hilfe minimieren";
  helpToggleButton.setAttribute("aria-expanded", String(!collapsed));
}

function focusHelpPanel() {
  helpPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showHelpTopic(topic, scrollIntoView = true) {
  renderHelpTopic(topic);
  if (state.helpCollapsed) {
    setHelpCollapsed(false);
  }
  if (scrollIntoView) {
    focusHelpPanel();
  }
}

function translateCollectionName(type) {
  const labels = {
    jobs: "Job",
    "job-exports": "Job-Export",
    presets: "Preset",
    embeddings: "Embedding",
    workspace: "Arbeitsbereich",
  };
  return labels[type] || type;
}

function getListElement(type) {
  const mapping = {
    jobs: jobsList,
    "job-exports": jobExportsList,
    presets: presetsList,
    embeddings: embeddingsList,
  };
  return mapping[type];
}

function formatMeta(item) {
  if (item.invalid) {
    return "Ungueltiges JSON";
  }

  const bits = [];
  if (item.entryCount !== undefined) {
    bits.push(`${item.entryCount} Eintraege`);
  }
  if (item.modelCount !== undefined) {
    bits.push(`${item.modelCount} Modelle`);
  }
  if (item.dimensions?.length) {
    bits.push(`Dimensionen: ${item.dimensions.join(", ")}`);
  }
  if (item.targetFaceCount !== undefined) {
    bits.push(`${item.targetFaceCount} Zielgesichter`);
  }
  if (item.markerCount !== undefined) {
    bits.push(`${item.markerCount} Marker`);
  }
  if (item.modifiedAt) {
    bits.push(new Date(item.modifiedAt).toLocaleString());
  }
  return bits.join(" • ");
}

function renderList(target, items, type) {
  target.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("li");
    empty.className = "item-meta";
    empty.textContent = "Noch nichts gespeichert.";
    target.appendChild(empty);
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.className = "item-button";
    if (
      state.selection &&
      state.selection.type === type &&
      state.selection.name === item.name
    ) {
      button.classList.add("active");
    }
    button.innerHTML = `
      <span class="item-name">${item.name}</span>
      <span class="item-meta">${formatMeta(item)}</span>
    `;
    button.addEventListener("click", () => loadItem(type, item.name));
    li.appendChild(button);
    target.appendChild(li);
  });
}

function renderAllLists() {
  renderList(jobsList, state.collections.jobs, "jobs");
  renderList(jobExportsList, state.collections["job-exports"], "job-exports");
  renderList(presetsList, state.collections.presets, "presets");
  renderList(embeddingsList, state.collections.embeddings, "embeddings");
}

function renderStatus(status) {
  const quality = status.quality;
  const deploymentProfile = status.deploymentProfile || {};
  const runtimeProfile = status.runtimeProfile || {};
  if (quality) {
    statusBadge.textContent = `${quality.overallPercent}% Remote bereit`;
    statusSummaryEyebrow.textContent = "Projektstatus";
    statusSummaryTitle.textContent = quality.scopeTitle;
    statusSummaryText.textContent = quality.scopeSummary;
    statusSummaryNote.textContent = quality.scopeNote;
    statusOverallPercent.textContent = `${quality.overallPercent}%`;
    statusOverallLabel.textContent = quality.overallLabel;
    statusAreas.innerHTML = quality.areas
      .map((area) => {
        const checks = area.checks
          .map(
            (check) =>
              `<li class="${check.ok ? "is-complete" : "is-open"}">${check.ok ? "Erfuellt" : "Offen"}: ${check.label}</li>`
          )
          .join("");
        const footer = area.remaining.length
          ? `<p class="item-meta">Offen: ${area.remaining.join(", ")}</p>`
          : '<p class="item-meta">Alle Kriterien fuer diesen Bereich sind erfuellt.</p>';
        return `
          <article class="status-area-card">
            <div class="status-area-head">
              <div>
                <h3>${area.title}</h3>
                <p class="panel-note">${area.summary}</p>
              </div>
              <span class="status-area-percent">${area.percent}%</span>
            </div>
            <ul class="status-check-list">${checks}</ul>
            ${footer}
          </article>
        `;
      })
      .join("");
  } else {
    statusBadge.textContent = status.capabilities.browserUi ? "Web bereit" : "Eingeschraenkt";
    statusSummaryEyebrow.textContent = "Projektstatus";
    statusSummaryTitle.textContent = "Remote-GPU-Web-Konsole";
    statusSummaryText.textContent = "Es liegen noch keine detaillierten Reifegrade vor.";
    statusSummaryNote.textContent = "";
    statusOverallPercent.textContent = "--";
    statusOverallLabel.textContent = "Noch keine Bewertung";
    statusAreas.innerHTML = "";
  }
  const cards = [
    ["Betriebsmodus", deploymentProfile.summary || "nicht erkannt"],
    ["Browser-Clients", (deploymentProfile.browserClients || []).join(", ") || "nicht erkannt"],
    ["GPU-Hosts", (deploymentProfile.gpuHosts || []).join(", ") || "nicht erkannt"],
    ["Host-Start", deploymentProfile.preferredHostStart || "nicht erkannt"],
    ["URL-Zugriff", deploymentProfile.preferredUrlMode || "nicht erkannt"],
    ["Aktiver Host", `${status.runtime.system} ${status.runtime.release}`],
    ["Aktives Python", status.runtime.pythonVersion],
    ["Projekt-Runtime", runtimeProfile.label || "nicht erkannt"],
    ["Starter-Einstieg", runtimeProfile.entryLabel || "nicht erkannt"],
    ["Kernpakete", runtimeProfile.packageLabel || "nicht erkannt"],
    ["FFmpeg", runtimeProfile.ffmpegLabel || status.binaries.ffmpeg || "nicht gefunden"],
    ["FFplay", runtimeProfile.ffplayLabel || status.binaries.ffplay || "nicht gefunden"],
    ["Git", runtimeProfile.gitLabel || status.binaries.git || "nicht gefunden"],
    ["Jobs", String(status.data.jobs)],
    ["Presets", String(status.data.presets)],
    ["Embeddings", String(status.data.embeddings || 0)],
    ["Browser-Pipeline", status.capabilities.headlessProcessingApi ? "aktiv" : "deaktiviert"],
  ];
  statusCards.innerHTML = cards
    .map(
      ([label, value]) => `
        <dl class="status-card">
          <dt>${label}</dt>
          <dd>${value}</dd>
        </dl>
      `
    )
    .join("");
}

function processingStatusLabel(status) {
  const labels = {
    idle: "Leerlauf",
    starting: "Startet",
    loading: "Laedt",
    running: "Laeuft",
    succeeded: "Erfolgreich",
    failed: "Fehlgeschlagen",
    stopping: "Stoppt",
    stopped: "Gestoppt",
  };
  return labels[status] || status || "Unbekannt";
}

function updateProcessingActionState() {
  const selectedJobName =
    state.selection && state.selection.type === "jobs" ? state.selection.name : null;
  const isActive = Boolean(state.processing?.active);
  const uploadReady = Boolean(state.browserWorkflow?.canRun);
  processingStartButton.disabled = !selectedJobName || isActive;
  processingStopButton.disabled = !isActive;
  workflowRunButton.disabled = !uploadReady || isActive;
  processingSelection.textContent = selectedJobName
    ? `Ausgewaehlter Job: ${selectedJobName}`
    : "Bitte zuerst einen Job aus der Liste oeffnen.";
}

function renderBrowserWorkflow(payload) {
  state.browserWorkflow = payload;
  const parts = [];
  if (payload.targetMedia) {
    parts.push(
      `<div><strong>Zielmedium:</strong> ${payload.targetMedia.name} (${payload.targetMedia.fileType})</div>`
    );
  } else {
    parts.push("<div><strong>Zielmedium:</strong> noch keines hochgeladen</div>");
  }

  if (payload.sourceFaces?.length) {
    parts.push(
      `<div><strong>Quellgesichter:</strong> ${payload.sourceFaces.length} Datei(en)</div>`
    );
    parts.push(
      `<div>${payload.sourceFaces.map((entry) => entry.name).join(", ")}</div>`
    );
  } else {
    parts.push("<div><strong>Quellgesichter:</strong> noch keine hochgeladen</div>");
  }

  parts.push(`<div><strong>Ausgabeordner:</strong> ${payload.outputFolder}</div>`);
  parts.push(
    `<div><strong>Strategie:</strong> Erstes erkanntes Quellgesicht auf alle Zielgesichter anwenden</div>`
  );
  parts.push(`<div>${payload.readyMessage}</div>`);
  workflowSummary.innerHTML = parts.join("");
  updateProcessingActionState();
}

function renderProcessingStatus(payload) {
  state.processing = payload;
  processingBadge.textContent = processingStatusLabel(payload.status);
  processingMessage.textContent =
    payload.message || "Noch kein Job im Browser gestartet.";

  const meta = [];
  if (payload.jobName) {
    meta.push(`Job: ${payload.jobName}`);
  }
  if (payload.startedAt) {
    meta.push(`Gestartet: ${new Date(payload.startedAt).toLocaleString()}`);
  }
  if (payload.finishedAt) {
    meta.push(`Beendet: ${new Date(payload.finishedAt).toLocaleString()}`);
  }
  if (payload.pid) {
    meta.push(`PID: ${payload.pid}`);
  }
  processingMeta.innerHTML = meta.length
    ? meta.map((line) => `<div>${line}</div>`).join("")
    : '<div class="item-meta">Noch keine Laufmetadaten vorhanden.</div>';

  const percent = payload.progress?.percent;
  if (Number.isFinite(percent)) {
    processingProgress.hidden = false;
    processingProgressValue.style.setProperty("--progress-width", `${percent}%`);
    processingProgressValue.textContent = `${percent}%`;
  } else {
    processingProgress.hidden = true;
    processingProgressValue.style.setProperty("--progress-width", "0%");
    processingProgressValue.textContent = "";
  }

  const outputParts = [];
  if (payload.outputPath) {
    outputParts.push(`<div><strong>Ausgabe:</strong> ${payload.outputPath}</div>`);
  }
  if (payload.outputDownloadUrl && payload.outputExists) {
    outputParts.push(
      `<div><a class="ghost" href="${payload.outputDownloadUrl}" target="_blank" rel="noreferrer">Ausgabe herunterladen</a></div>`
    );
  }
  if (payload.lastMessage) {
    outputParts.push(`<div><strong>Hinweis:</strong> ${payload.lastMessage}</div>`);
  }
  processingOutput.innerHTML = outputParts.length
    ? outputParts.join("")
    : '<div class="item-meta">Nach einem erfolgreichen Lauf erscheint hier der Ausgabepfad.</div>';

  processingLog.value = (payload.logTail || []).join("\n");
  updateProcessingActionState();

  const shouldPoll = ["starting", "loading", "running", "stopping"].includes(
    payload.status
  );
  if (shouldPoll && !state.processingPollHandle) {
    state.processingPollHandle = window.setInterval(() => {
      refreshProcessingStatus().catch((error) => showFlash(error.message, true));
    }, 2500);
  }
  if (!shouldPoll && state.processingPollHandle) {
    window.clearInterval(state.processingPollHandle);
    state.processingPollHandle = null;
  }
}

function renderWorkspaceSummary(summary) {
  if (!summary.exists) {
    workspaceSummary.textContent = "Es wurde noch kein letzter Arbeitsbereich gespeichert.";
    return;
  }
  workspaceSummary.innerHTML = `
    <strong>${summary.targetFaceCount}</strong> Zielgesichter<br />
    <strong>${summary.inputFaceCount}</strong> Quellgesichter<br />
    <strong>${summary.markerCount}</strong> Marker<br />
    Aktualisiert: ${new Date(summary.modifiedAt).toLocaleString()}
  `;
}

async function refreshCollection(type) {
  const payload = await request(`/api/${type}`);
  state.collections[type] = payload.items;
  renderList(getListElement(type), payload.items, type);
}

async function refreshWorkspaceSummary() {
  const payload = await request("/api/workspaces/last");
  renderWorkspaceSummary(payload.summary);
}

async function refreshStatus() {
  const payload = await request("/api/status");
  renderStatus(payload);
}

async function refreshProcessingStatus() {
  const payload = await request("/api/processing/status");
  renderProcessingStatus(payload);
}

async function refreshBrowserWorkflow() {
  const payload = await request("/api/browser-workflow");
  renderBrowserWorkflow(payload);
}

async function refreshAll() {
  clearFlash();
  await Promise.all([
    refreshStatus(),
    refreshProcessingStatus(),
    refreshBrowserWorkflow(),
    refreshCollection("jobs"),
    refreshCollection("job-exports"),
    refreshCollection("presets"),
    refreshCollection("embeddings"),
    refreshWorkspaceSummary(),
  ]);
}

function selectEditor(type, name, data, subtitle) {
  state.selection = { type, name };
  editorTitle.textContent = `${translateCollectionName(type)}: ${name}`;
  editorSubtitle.textContent = subtitle;
  nameInput.value = name;
  jsonEditor.value = JSON.stringify(data, null, 2);
  saveButton.disabled = false;
  deleteButton.disabled = type === "workspace";
  renderAllLists();
  updateProcessingActionState();
}

function setDefaultEditorState() {
  editorTitle.textContent = "JSON-Editor";
  editorSubtitle.textContent =
    "Waehle einen Job, ein Preset, ein Embedding, einen Job-Export oder den letzten Arbeitsbereich aus.";
  nameInput.value = "";
  jsonEditor.value = "";
  saveButton.disabled = true;
  deleteButton.disabled = true;
  updateProcessingActionState();
}

function draftPayload() {
  return [
    {
      name: state.embeddingDraft.name.trim(),
      embedding_store: state.embeddingDraft.embedding_store,
    },
  ];
}

function renderEmbeddingDraft() {
  const models = Object.entries(state.embeddingDraft.embedding_store);
  builderModelList.innerHTML = "";

  if (!models.length) {
    const empty = document.createElement("li");
    empty.className = "item-meta";
    empty.textContent = "Noch kein Modell hinzugefuegt.";
    builderModelList.appendChild(empty);
    builderStats.textContent = "Noch kein Modell hinzugefuegt.";
    builderPreview.value = "";
    return;
  }

  const dimensions = [];
  models.forEach(([modelName, values]) => {
    dimensions.push(values.length);
    const li = document.createElement("li");
    li.className = "draft-item";
    li.innerHTML = `
      <div>
        <strong>${modelName}</strong>
        <span class="item-meta">${values.length} Werte</span>
      </div>
      <button class="mini danger-ghost" type="button" data-remove-model="${modelName}">
        Entfernen
      </button>
    `;
    builderModelList.appendChild(li);
  });

  builderStats.textContent = `${models.length} Modell(e) • Dimensionen: ${dimensions.join(", ")}`;
  builderPreview.value = JSON.stringify(draftPayload(), null, 2);
}

function resetEmbeddingBuilder() {
  state.embeddingDraft = {
    fileName: "",
    name: "",
    embedding_store: {},
  };
  builderFileName.value = "";
  builderEmbeddingName.value = "";
  builderModelName.value = "";
  builderVectorInput.value = "";
  renderEmbeddingDraft();
}

function hydrateBuilderFromPayload(fileName, payload) {
  if (
    !Array.isArray(payload) ||
    payload.length !== 1 ||
    !payload[0] ||
    typeof payload[0] !== "object" ||
    !payload[0].embedding_store ||
    typeof payload[0].embedding_store !== "object"
  ) {
    return;
  }

  state.embeddingDraft = {
    fileName,
    name: String(payload[0].name || fileName),
    embedding_store: Object.fromEntries(
      Object.entries(payload[0].embedding_store).map(([modelName, values]) => [
        modelName,
        Array.isArray(values) ? values : [],
      ])
    ),
  };

  builderFileName.value = state.embeddingDraft.fileName;
  builderEmbeddingName.value = state.embeddingDraft.name;
  builderModelName.value = "";
  builderVectorInput.value = "";
  renderEmbeddingDraft();
}

function parseVectorValues(raw) {
  const source = raw.trim();
  if (!source) {
    throw new Error("Bitte mindestens einen Zahlenwert fuer den Embedding-Vektor eingeben.");
  }

  let values;
  if (source.startsWith("[")) {
    values = JSON.parse(source);
    if (!Array.isArray(values)) {
      throw new Error("Das JSON fuer den Embedding-Vektor muss ein Array sein.");
    }
  } else {
    values = source
      .split(/[\s,;]+/)
      .map((part) => part.trim())
      .filter(Boolean);
  }

  if (!values.length) {
    throw new Error("Der Embedding-Vektor enthaelt keine Werte.");
  }

  return values.map((value) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      throw new Error(`"${value}" ist keine gueltige Zahl.`);
    }
    return numeric;
  });
}

function getBuilderFileName() {
  return builderFileName.value.trim() || builderEmbeddingName.value.trim();
}

function getBuilderEmbeddingName() {
  return builderEmbeddingName.value.trim() || builderFileName.value.trim();
}

function ensureDraftReady() {
  const fileName = getBuilderFileName();
  const embeddingName = getBuilderEmbeddingName();
  if (!fileName) {
    throw new Error("Bitte einen Dateinamen oder Embedding-Namen angeben.");
  }
  if (!embeddingName) {
    throw new Error("Bitte einen Embedding-Namen angeben.");
  }
  if (!Object.keys(state.embeddingDraft.embedding_store).length) {
    throw new Error("Bitte mindestens ein Modell zum Embedding hinzufuegen.");
  }

  state.embeddingDraft.fileName = fileName;
  state.embeddingDraft.name = embeddingName;
}

function addModelToDraft() {
  clearFlash();
  try {
    const modelName = builderModelName.value.trim();
    if (!modelName) {
      throw new Error("Bitte einen Modellnamen eingeben.");
    }

    const values = parseVectorValues(builderVectorInput.value);
    state.embeddingDraft.fileName = getBuilderFileName();
    state.embeddingDraft.name = getBuilderEmbeddingName();
    state.embeddingDraft.embedding_store[modelName] = values;

    if (!builderEmbeddingName.value.trim() && builderFileName.value.trim()) {
      builderEmbeddingName.value = builderFileName.value.trim();
      state.embeddingDraft.name = builderEmbeddingName.value.trim();
    }

    builderVectorInput.value = "";
    builderModelName.value = "";
    renderEmbeddingDraft();
    showFlash(`Modell "${modelName}" zum Entwurf hinzugefuegt.`);
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function saveDraftEmbedding() {
  clearFlash();
  try {
    ensureDraftReady();
    const fileName = state.embeddingDraft.fileName;
    const payload = draftPayload();

    await request(`/api/embeddings/${encodeURIComponent(fileName)}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });

    showFlash(`Embedding "${fileName}" gespeichert.`);
    await refreshCollection("embeddings");
    await refreshStatus();
    await loadItem("embeddings", fileName);
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function loadItem(type, name) {
  clearFlash();
  try {
    if (type === "workspace") {
      const payload = await request("/api/workspaces/last");
      selectEditor(
        "workspace",
        "last_workspace",
        payload.data,
        "Dieser Inhalt wird im Projektwurzelverzeichnis als last_workspace.json gespeichert."
      );
      renderHelpTopic("workspace");
      return;
    }

    const payload = await request(`/api/${type}/${encodeURIComponent(name)}`);
    const subtitleMap = {
      jobs: "Job-Definition fuer die Warteschlange der Desktop-Jobverwaltung.",
      "job-exports":
        "Eigenstaendiger Job-Export, kompatibel mit dem aktuellen Workspace-Serializer.",
      presets: "Preset-Paar aus Parameter-JSON und Steuerungs-JSON.",
      embeddings:
        "Kompatible Embedding-Datei fuer den Desktop-Import mit name und embedding_store.",
    };
    selectEditor(type, name, payload, subtitleMap[type]);
    if (type === "embeddings") {
      hydrateBuilderFromPayload(name, payload);
    }
    renderHelpTopic(type);
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function saveCurrentSelection() {
  if (!state.selection) {
    return;
  }

  clearFlash();
  try {
    const payload = JSON.parse(jsonEditor.value || "{}");
    const name = nameInput.value.trim();

    if (state.selection.type === "workspace") {
      await request("/api/workspaces/last", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      state.selection.name = "last_workspace";
      showFlash("Letzter Arbeitsbereich gespeichert.");
      await refreshWorkspaceSummary();
      return;
    }

    if (!name) {
      throw new Error("Der Name darf nicht leer sein.");
    }

    let body = payload;
    if (state.selection.type === "presets") {
      body = {
        parameters: payload.parameters || {},
        control: payload.control || {},
      };
    }

    await request(`/api/${state.selection.type}/${encodeURIComponent(name)}`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    state.selection.name = name;
    showFlash(`${translateCollectionName(state.selection.type)} gespeichert.`);
    await refreshCollection(state.selection.type);
    await refreshStatus();
    await loadItem(state.selection.type, name);
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function deleteCurrentSelection() {
  if (!state.selection || state.selection.type === "workspace") {
    return;
  }

  clearFlash();
  try {
    const currentType = state.selection.type;
    const currentName = state.selection.name;
    await request(
      `/api/${currentType}/${encodeURIComponent(currentName)}`,
      {
        method: "DELETE",
      }
    );
    showFlash(`${translateCollectionName(currentType)} geloescht.`);
    state.selection = null;
    setDefaultEditorState();
    await refreshCollection(currentType);
    await refreshStatus();
    if (
      currentType === "embeddings" &&
      state.embeddingDraft.fileName === currentName
    ) {
      resetEmbeddingBuilder();
    }
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function startSelectedJob() {
  if (!state.selection || state.selection.type !== "jobs") {
    showFlash("Bitte zuerst einen gespeicherten Job aus der Liste oeffnen.", true);
    return;
  }

  clearFlash();
  try {
    const payload = await request(
      `/api/processing/jobs/${encodeURIComponent(state.selection.name)}/start`,
      {
        method: "POST",
      }
    );
    renderHelpTopic("processing");
    renderProcessingStatus(payload);
    showFlash(`Browser-Verarbeitung fuer "${state.selection.name}" gestartet.`);
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function stopProcessing() {
  clearFlash();
  try {
    const payload = await request("/api/processing/stop", {
      method: "POST",
    });
    renderProcessingStatus(payload);
    showFlash("Browser-Verarbeitung gestoppt.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function uploadTargetMedia() {
  clearFlash();
  try {
    const files = Array.from(targetUploadInput.files || []);
    if (!files.length) {
      throw new Error("Bitte zuerst ein Zielmedium auswaehlen.");
    }
    const payload = await uploadRequest("/api/browser-workflow/target", files);
    renderBrowserWorkflow(payload.state);
    renderHelpTopic("processing");
    showFlash(`Zielmedium "${payload.saved.name}" hochgeladen.`);
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function uploadSourceFaces() {
  clearFlash();
  try {
    const files = Array.from(sourceUploadInput.files || []);
    if (!files.length) {
      throw new Error("Bitte zuerst mindestens ein Quellgesicht auswaehlen.");
    }
    const payload = await uploadRequest("/api/browser-workflow/sources", files);
    renderBrowserWorkflow(payload.state);
    renderHelpTopic("processing");
    showFlash(`${payload.saved.length} Quellgesicht(er) hochgeladen.`);
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function resetWorkflow() {
  clearFlash();
  try {
    const payload = await request("/api/browser-workflow/reset", {
      method: "POST",
      body: JSON.stringify({}),
    });
    targetUploadInput.value = "";
    sourceUploadInput.value = "";
    detectionFrameInput.value = "0";
    renderBrowserWorkflow(payload);
    showFlash("Direkt-Upload-Zustand zurueckgesetzt.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function runUploadedWorkflow() {
  clearFlash();
  try {
    const parsedFrame = Number(detectionFrameInput.value || 0);
    const detectionFrame = Number.isFinite(parsedFrame)
      ? Math.max(0, Math.floor(parsedFrame))
      : 0;
    const payload = await request("/api/browser-workflow/run", {
      method: "POST",
      body: JSON.stringify({ detectionFrame }),
    });
    renderHelpTopic("processing");
    renderProcessingStatus(payload);
    showFlash("Browser-Direktlauf gestartet.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

document.getElementById("refreshAllButton").addEventListener("click", refreshAll);
openHelpButton.addEventListener("click", () => showHelpTopic("overview"));
helpOverviewButton.addEventListener("click", () => showHelpTopic("overview", false));
processingRefreshButton.addEventListener("click", () => {
  renderHelpTopic("processing");
  refreshProcessingStatus().catch((error) => showFlash(error.message, true));
});
workflowResetButton.addEventListener("click", resetWorkflow);
processingStartButton.addEventListener("click", startSelectedJob);
processingStopButton.addEventListener("click", stopProcessing);
uploadTargetButton.addEventListener("click", uploadTargetMedia);
uploadSourcesButton.addEventListener("click", uploadSourceFaces);
workflowRunButton.addEventListener("click", runUploadedWorkflow);
helpToggleButton.addEventListener("click", () => {
  const nextCollapsed = !state.helpCollapsed;
  setHelpCollapsed(nextCollapsed);
  if (!nextCollapsed) {
    focusHelpPanel();
  }
});
document.getElementById("loadWorkspaceButton").addEventListener("click", () => {
  loadItem("workspace", "last_workspace");
});
document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-help-topic]");
  if (!trigger) {
    return;
  }
  showHelpTopic(trigger.dataset.helpTopic);
});
document.querySelectorAll("[data-refresh]").forEach((button) => {
  button.addEventListener("click", () =>
    refreshCollection(button.getAttribute("data-refresh"))
  );
});
saveButton.addEventListener("click", saveCurrentSelection);
deleteButton.addEventListener("click", deleteCurrentSelection);

builderAddModelButton.addEventListener("click", addModelToDraft);
builderAddModelButton.addEventListener("click", () => {
  renderHelpTopic("builder");
});
builderSaveButton.addEventListener("click", () => {
  renderHelpTopic("builder");
  saveDraftEmbedding();
});
builderResetButton.addEventListener("click", () => {
  clearFlash();
  renderHelpTopic("builder");
  resetEmbeddingBuilder();
});
builderModelList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-remove-model]");
  if (!button) {
    return;
  }
  delete state.embeddingDraft.embedding_store[button.dataset.removeModel];
  renderEmbeddingDraft();
});

builderFileName.addEventListener("input", () => {
  state.embeddingDraft.fileName = builderFileName.value.trim();
  if (!builderEmbeddingName.value.trim()) {
    state.embeddingDraft.name = state.embeddingDraft.fileName;
  }
  renderEmbeddingDraft();
});

builderEmbeddingName.addEventListener("input", () => {
  state.embeddingDraft.name = builderEmbeddingName.value.trim();
  renderEmbeddingDraft();
});

setDefaultEditorState();
resetEmbeddingBuilder();
renderHelpTopic("overview");
setHelpCollapsed(false);
refreshAll().catch((error) => showFlash(error.message, true));
