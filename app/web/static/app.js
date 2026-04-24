const state = {
  selection: null,
  processing: null,
  browserWorkflow: null,
  collections: {
    jobs: [],
    "job-exports": [],
    presets: [],
    embeddings: [],
  },
  utilityTab: "status",
  leftDockTab: "media",
  centerPaneTab: "output",
  workbenchTabs: [],
  workbenchDefaults: { control: {}, parameters: {} },
  workbench: { control: {}, parameters: {} },
  activeWorkbenchTab: null,
  workbenchSaveHandle: null,
  processingPollHandle: null,
  previewUrls: {
    target: null,
    sources: {},
  },
  embeddingDraft: {
    fileName: "",
    name: "",
    embedding_store: {},
  },
  transport: {
    frameIndex: 0,
    frameMax: 0,
    fps: 0,
    mediaType: null,
    playing: false,
    syncingVideo: false,
  },
  ui: {
    busyAction: null,
  },
};

const jobsList = document.getElementById("jobsList");
const jobExportsList = document.getElementById("jobExportsList");
const presetsList = document.getElementById("presetsList");
const embeddingsList = document.getElementById("embeddingsList");
const workspaceSummary = document.getElementById("workspaceSummary");
const globalFlash = document.getElementById("globalFlash");
const leftDockNav = document.getElementById("leftDockNav");
const centerPaneNav = document.getElementById("centerPaneNav");
const resetLayoutButton = document.getElementById("resetLayoutButton");

const processingBadge = document.getElementById("processingBadge");
const processingSelection = document.getElementById("processingSelection");
const processingMessage = document.getElementById("processingMessage");
const processingMeta = document.getElementById("processingMeta");
const processingOutput = document.getElementById("processingOutput");
const processingLog = document.getElementById("processingLog");
const processingProgress = document.getElementById("processingProgress");
const processingProgressValue = document.getElementById("processingProgressValue");
const processingStartButton = document.getElementById("processingStartButton");
const processingStopButton = document.getElementById("processingStopButton");
const processingRefreshButton = document.getElementById("processingRefreshButton");

const targetUploadInput = document.getElementById("targetUploadInput");
const sourceUploadInput = document.getElementById("sourceUploadInput");
const uploadTargetButton = document.getElementById("uploadTargetButton");
const uploadSourcesButton = document.getElementById("uploadSourcesButton");
const findTargetFacesButton = document.getElementById("findTargetFacesButton");
const clearTargetFacesButton = document.getElementById("clearTargetFacesButton");
const quickFindTargetFacesButton = document.getElementById("quickFindTargetFacesButton");
const quickSwapPreviewButton = document.getElementById("quickSwapPreviewButton");
const quickRunWorkflowButton = document.getElementById("quickRunWorkflowButton");
const workflowResetButton = document.getElementById("workflowResetButton");
const workflowRunButton = document.getElementById("workflowRunButton");
const workflowSummary = document.getElementById("workflowSummary");
const workflowGuideTitle = document.getElementById("workflowGuideTitle");
const workflowGuideBadge = document.getElementById("workflowGuideBadge");
const workflowChecklist = document.getElementById("workflowChecklist");
const workflowNextAction = document.getElementById("workflowNextAction");
const detectionFrameInput = document.getElementById("detectionFrameInput");
const targetMediaPreview = document.getElementById("targetMediaPreview");
const sourceFacePreviewList = document.getElementById("sourceFacePreviewList");
const targetFacesPreviewList = document.getElementById("targetFacesPreviewList");
const stageTargetPreview = document.getElementById("stageTargetPreview");
const stageComparePreview = document.getElementById("stageComparePreview");
const targetStageMeta = document.getElementById("targetStageMeta");
const sourceStageMeta = document.getElementById("sourceStageMeta");
const transportPrevFrameButton = document.getElementById("transportPrevFrameButton");
const transportPlayButton = document.getElementById("transportPlayButton");
const transportNextFrameButton = document.getElementById("transportNextFrameButton");
const transportPreviewButton = document.getElementById("transportPreviewButton");
const transportSwapPreviewButton = document.getElementById("transportSwapPreviewButton");
const transportFrameSlider = document.getElementById("transportFrameSlider");
const transportFrameInput = document.getElementById("transportFrameInput");
const transportMeta = document.getElementById("transportMeta");
const quickActionTitle = document.getElementById("quickActionTitle");
const quickActionHint = document.getElementById("quickActionHint");
const runtimeBarFill = document.getElementById("runtimeBarFill");
const runtimeBarLabel = document.getElementById("runtimeBarLabel");
const runtimeBarCaption = document.getElementById("runtimeBarCaption");

const statusBadge = document.getElementById("statusBadge");
const statusSummaryEyebrow = document.getElementById("statusSummaryEyebrow");
const statusSummaryTitle = document.getElementById("statusSummaryTitle");
const statusSummaryText = document.getElementById("statusSummaryText");
const statusSummaryNote = document.getElementById("statusSummaryNote");
const statusOverallPercent = document.getElementById("statusOverallPercent");
const statusOverallLabel = document.getElementById("statusOverallLabel");
const statusAreas = document.getElementById("statusAreas");
const statusCards = document.getElementById("statusCards");

const nameInput = document.getElementById("nameInput");
const jsonEditor = document.getElementById("jsonEditor");
const editorTitle = document.getElementById("editorTitle");
const editorSubtitle = document.getElementById("editorSubtitle");
const saveButton = document.getElementById("saveButton");
const deleteButton = document.getElementById("deleteButton");

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

const workbenchDescription = document.getElementById("workbenchDescription");
const workbenchTabs = document.getElementById("workbenchTabs");
const workbenchSections = document.getElementById("workbenchSections");
const workbenchSummary = document.getElementById("workbenchSummary");
const saveWorkbenchButton = document.getElementById("saveWorkbenchButton");
const resetWorkbenchButton = document.getElementById("resetWorkbenchButton");

const WORKBENCH_TAB_UI = {
  swap: {
    label: "Face Swap",
    description:
      "Native swap controls for model choice, similarity, strength and mask behaviour.",
  },
  restoration: {
    label: "Face Editor",
    description:
      "Finishing and restoration tools for the swapped face, similar to the desktop side tabs.",
  },
  detect: {
    label: "Common",
    description:
      "Shared detector, recognition and matching behaviour for the remote workflow.",
  },
  output: {
    label: "Settings",
    description:
      "Runtime, output and encoding settings for the browser-driven host pipeline.",
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
    const message =
      (payload && typeof payload === "object" && (payload.error || payload.message)) ||
      (typeof payload === "string" &&
        payload.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim()) ||
      response.statusText;
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
    const message =
      (payload && typeof payload === "object" && (payload.error || payload.message)) ||
      (typeof payload === "string" &&
        payload.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim()) ||
      response.statusText;
    throw new Error(message);
  }
  return payload;
}

function showFlash(message, isError = false) {
  globalFlash.hidden = false;
  globalFlash.className = isError ? "global-flash error" : "global-flash";
  globalFlash.textContent = message;
}

function clearFlash() {
  globalFlash.hidden = true;
  globalFlash.textContent = "";
  globalFlash.className = "global-flash";
}

function translateCollectionName(type) {
  const labels = {
    jobs: "Job",
    "job-exports": "Job-Export",
    presets: "Preset",
    embeddings: "Embedding",
    workspace: "Workspace",
  };
  return labels[type] || type;
}

function getListElement(type) {
  return {
    jobs: jobsList,
    "job-exports": jobExportsList,
    presets: presetsList,
    embeddings: embeddingsList,
  }[type];
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
    bits.push(`Dim: ${item.dimensions.join(", ")}`);
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

function renderWorkspaceSummary(summary) {
  if (!summary?.exists) {
    workspaceSummary.textContent =
      "Es wurde noch kein letzter Workspace gespeichert.";
    return;
  }
  workspaceSummary.innerHTML = `
    <strong>${summary.targetFaceCount}</strong> Zielgesichter<br />
    <strong>${summary.inputFaceCount}</strong> Quellgesichter<br />
    <strong>${summary.markerCount}</strong> Marker<br />
    Aktualisiert: ${new Date(summary.modifiedAt).toLocaleString()}
  `;
}

function renderStatus(status) {
  const quality = status.quality;
  const deploymentProfile = status.deploymentProfile || {};
  const runtimeProfile = status.runtimeProfile || {};
  const overallPercent = Number(quality?.overallPercent || 0);

  if (quality) {
    statusBadge.textContent = `${quality.overallPercent}% Remote bereit`;
    statusBadge.dataset.state = overallPercent >= 100 ? "ready" : "loading";
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
        return `
          <article class="status-area-card">
            <div class="status-area-head">
              <div>
                <h4>${area.title}</h4>
                <p class="panel-note">${area.summary}</p>
              </div>
              <span class="status-area-percent">${area.percent}%</span>
            </div>
            <ul class="status-check-list">${checks}</ul>
          </article>
        `;
      })
      .join("");
  }

  runtimeBarFill.style.width = `${Math.max(0, Math.min(100, overallPercent))}%`;
  runtimeBarLabel.textContent = `${overallPercent}% Remote Ready`;
  runtimeBarCaption.textContent = `${
    deploymentProfile.summary || "Remote browser client"
  } • ${runtimeProfile.label || "starter-managed runtime"}`;

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
  return (
    {
      idle: "Leerlauf",
      starting: "Startet",
      loading: "Laedt",
      running: "Laeuft",
      succeeded: "Erfolgreich",
      failed: "Fehlgeschlagen",
      stopping: "Stoppt",
      stopped: "Gestoppt",
    }[status] || status || "Unbekannt"
  );
}

function setStatusTone(element, status) {
  if (!element) {
    return;
  }
  element.dataset.state = status || "idle";
}

function updateProcessingActionState() {
  const selectedJobName =
    state.selection && state.selection.type === "jobs" ? state.selection.name : null;
  const workflow = workflowState();
  const isActive = workflow.processingActive;
  const busy = Boolean(workflow.busyAction);
  const canRunWorkflow = workflow.canRun;
  const canFindFaces = workflow.canFindFaces;
  const canSwapPreview = workflow.canSwapPreview;

  processingStartButton.disabled = !selectedJobName || isActive || busy;
  processingStopButton.disabled = !isActive;
  workflowRunButton.disabled = !canRunWorkflow;
  findTargetFacesButton.disabled = !canFindFaces;
  clearTargetFacesButton.disabled =
    !(state.browserWorkflow?.detectedTargetFaces?.count > 0) || isActive || busy;
  quickFindTargetFacesButton.disabled = !canFindFaces;
  quickSwapPreviewButton.disabled = !canSwapPreview;
  quickRunWorkflowButton.disabled = !canRunWorkflow;
  transportSwapPreviewButton.disabled = !canSwapPreview;
  transportPreviewButton.disabled =
    !state.browserWorkflow?.targetMedia || isActive || busy;
  processingSelection.textContent = selectedJobName
    ? `Ausgewaehlter Job: ${selectedJobName}`
    : "Bitte links einen Job auswaehlen oder direkt mit Uploads arbeiten.";
}

function revokePreviewUrls() {
  if (state.previewUrls.target) {
    URL.revokeObjectURL(state.previewUrls.target);
  }
  Object.values(state.previewUrls.sources).forEach((url) => URL.revokeObjectURL(url));
  state.previewUrls = { target: null, sources: {} };
}

function setTargetPreviewFromInput(files) {
  if (state.previewUrls.target) {
    URL.revokeObjectURL(state.previewUrls.target);
    state.previewUrls.target = null;
  }
  const file = files[0];
  if (!file) {
    return;
  }
  state.previewUrls.target = URL.createObjectURL(file);
}

function setSourcePreviewsFromInput(files) {
  Object.values(state.previewUrls.sources).forEach((url) => URL.revokeObjectURL(url));
  state.previewUrls.sources = {};
  files.forEach((file) => {
    state.previewUrls.sources[file.name] = URL.createObjectURL(file);
  });
}

function createMediaThumb(entry, url, options = {}) {
  const { controls = false, autoplay = false, loop = false } = options;
  if (url && entry.fileType === "image") {
    return `<img src="${url}" alt="${entry.name}" />`;
  }
  if (url && entry.fileType === "video") {
    return `<video src="${url}" muted ${controls ? "controls" : ""} ${
      autoplay ? "autoplay" : ""
    } ${loop ? "loop" : ""} preload="metadata" playsinline></video>`;
  }
  return `<div class="media-placeholder">${entry.fileType === "video" ? "VIDEO" : "IMAGE"}</div>`;
}

function isImageFile(path = "") {
  return /\.(png|jpe?g|webp|bmp)$/i.test(path);
}

function isVideoFile(path = "") {
  return /\.(mp4|mov|mkv|avi|webm|m4v)$/i.test(path);
}

function targetMediaUrl(entry) {
  return state.previewUrls.target || entry?.mediaUrl || "";
}

function sourceMediaUrl(entry) {
  return state.previewUrls.sources[entry.name] || entry.mediaUrl || "";
}

function activeTargetVideo() {
  return stageTargetPreview.querySelector("video");
}

function releaseActiveTargetVideo() {
  const video = activeTargetVideo();
  if (!video) {
    return;
  }
  video.pause();
  video.removeAttribute("src");
  video.load();
}

function setFindFacesBusy(isBusy) {
  const busyLabel = "Finding...";
  const idlePrimaryLabel = "Find Faces";
  const idleQuickLabel = "1. Find Faces";
  findTargetFacesButton.disabled = isBusy;
  quickFindTargetFacesButton.disabled = isBusy;
  findTargetFacesButton.textContent = isBusy ? busyLabel : idlePrimaryLabel;
  quickFindTargetFacesButton.textContent = isBusy ? busyLabel : idleQuickLabel;
}

function workflowState(payload = state.browserWorkflow) {
  const target = payload?.targetMedia;
  const sources = payload?.sourceFaces || [];
  const previewFrame = payload?.previewFrame;
  const detectedFaces = payload?.detectedTargetFaces;
  const swapPreview = payload?.swapPreview;
  const isVideo = target?.fileType === "video";
  const requestedFrame = clampFrame(detectionFrameInput.value || state.transport.frameIndex || 0);
  const previewFrameIndex = Number(previewFrame?.frameIndex ?? 0);
  const detectedFrameIndex = Number(detectedFaces?.frameIndex ?? previewFrameIndex);
  const swapPreviewFrameIndex = Number(swapPreview?.frameIndex ?? previewFrameIndex);
  const previewMatchesFrame = Boolean(target) && (!isVideo || Boolean(previewFrame && previewFrameIndex === requestedFrame));
  const detectionMatchesFrame =
    Boolean(detectedFaces?.count) && (!isVideo || detectedFrameIndex === requestedFrame);
  const swapPreviewMatchesFrame =
    Boolean(swapPreview?.url) && (!isVideo || swapPreviewFrameIndex === requestedFrame);
  const processingActive = Boolean(state.processing?.active);
  const busyAction = state.ui.busyAction;

  const steps = [
    {
      id: "target",
      label: "Target",
      ready: Boolean(target),
      detail: target ? target.name : "Target fehlt",
    },
    {
      id: "sources",
      label: "Sources",
      ready: sources.length > 0,
      detail: sources.length ? `${sources.length} Source Face(s)` : "Source Faces fehlen",
    },
    {
      id: "frame",
      label: "Detection Frame",
      ready: previewMatchesFrame,
      detail: previewMatchesFrame
        ? `Frame ${requestedFrame} bestaetigt`
        : isVideo
          ? "Preview Frame fuer aktuellen Scrub-Frame fehlt"
          : "Bildziel braucht keine Extra-Vorschau",
    },
    {
      id: "detect",
      label: "Find Faces",
      ready: detectionMatchesFrame,
      detail: detectionMatchesFrame
        ? `${detectedFaces.count} Gesicht(er) auf Frame ${requestedFrame}`
        : "Noch keine Zielgesichter fuer diesen Frame",
    },
    {
      id: "preview",
      label: "Swap Preview",
      ready: swapPreviewMatchesFrame,
      detail: swapPreviewMatchesFrame
        ? `Preview fuer Frame ${requestedFrame} bereit`
        : "Noch keine passende Swap Preview",
    },
  ];

  let nextAction = "Lade zuerst das Zielmedium.";
  if (busyAction) {
    nextAction = busyAction;
  } else if (!target) {
    nextAction = "Lade zuerst das Zielmedium.";
  } else if (!sources.length) {
    nextAction = "Lade jetzt mindestens ein Quellgesicht.";
  } else if (!previewMatchesFrame) {
    nextAction = isVideo
      ? "Waehle den Frame und klicke dann Preview Frame."
      : "Das Zielbild ist bereit. Du kannst direkt Gesichter finden.";
  } else if (!detectionMatchesFrame) {
    nextAction = "Klicke jetzt Find Faces fuer den aktuellen Detection-Frame.";
  } else if (!swapPreviewMatchesFrame) {
    nextAction = "Klicke jetzt Swap Preview, bevor du den echten Lauf startest.";
  } else {
    nextAction = "Alles bereit. Du kannst jetzt Swap Faces starten.";
  }

  return {
    requestedFrame,
    isVideo,
    previewMatchesFrame,
    detectionMatchesFrame,
    swapPreviewMatchesFrame,
    canFindFaces: Boolean(target) && previewMatchesFrame && !processingActive && !busyAction,
    canSwapPreview:
      Boolean(target) &&
      sources.length > 0 &&
      previewMatchesFrame &&
      detectionMatchesFrame &&
      !processingActive &&
      !busyAction,
    canRun:
      Boolean(target) &&
      sources.length > 0 &&
      previewMatchesFrame &&
      detectionMatchesFrame &&
      !processingActive &&
      !busyAction,
    busyAction,
    processingActive,
    nextAction,
    steps,
  };
}

function setUiBusy(actionLabel = null) {
  state.ui.busyAction = actionLabel;
  if (state.browserWorkflow) {
    renderWorkflowGuide(state.browserWorkflow);
    renderWorkflowSummary(state.browserWorkflow);
  }
  updateProcessingActionState();
}

function clampFrame(frame) {
  const frameMax = Number(state.transport.frameMax || 0);
  return Math.max(0, Math.min(frameMax, Math.floor(Number(frame) || 0)));
}

function syncTransportControls() {
  const isVideo = state.transport.mediaType === "video";
  const workflow = workflowState();
  const disabled = !isVideo;
  transportPrevFrameButton.disabled = disabled;
  transportPlayButton.disabled = disabled;
  transportNextFrameButton.disabled = disabled;
  transportFrameSlider.disabled = disabled;
  transportFrameInput.disabled = disabled;
  transportPreviewButton.disabled =
    !state.browserWorkflow?.targetMedia || workflow.processingActive || Boolean(workflow.busyAction);
  transportSwapPreviewButton.disabled = !workflow.canSwapPreview;
  transportFrameSlider.max = String(Math.max(0, state.transport.frameMax));
  transportFrameInput.max = String(Math.max(0, state.transport.frameMax));
  transportFrameSlider.value = String(clampFrame(state.transport.frameIndex));
  transportFrameInput.value = String(clampFrame(state.transport.frameIndex));
  transportPlayButton.textContent = state.transport.playing ? "||" : "\u25b6";
  if (!state.browserWorkflow?.targetMedia) {
    transportMeta.textContent = "No video loaded.";
    return;
  }
  if (!isVideo) {
    transportMeta.textContent = "Image loaded. Preview Frame saves the current still image as detection preview.";
    return;
  }
  const fpsLabel =
    state.transport.fps > 0 ? `${state.transport.fps.toFixed(2)} fps` : "fps unknown";
  transportMeta.textContent = `Frame ${clampFrame(state.transport.frameIndex)} / ${Math.max(
    0,
    state.transport.frameMax
  )} • ${fpsLabel}`;
}

function setTransportFrame(frame, options = {}) {
  const { syncVideo = true } = options;
  const nextFrame = clampFrame(frame);
  state.transport.frameIndex = nextFrame;
  detectionFrameInput.value = String(nextFrame);
  syncTransportControls();

  const video = activeTargetVideo();
  if (!syncVideo || !video || state.transport.mediaType !== "video") {
    return;
  }

  const fps = Number(state.transport.fps || 0);
  if (fps <= 0) {
    return;
  }

  state.transport.syncingVideo = true;
  const frameTime = nextFrame / fps;
  video.currentTime = frameTime > 0 ? frameTime : Math.min(0.001, 1 / fps);
  window.setTimeout(() => {
    state.transport.syncingVideo = false;
  }, 50);
}

function syncTransportFromTarget(entry) {
  state.transport.mediaType = entry?.fileType || null;
  state.transport.playing = false;
  state.transport.fps = Number(entry?.fps || 0);
  state.transport.frameMax = Number(entry?.frameMax || 0);
  const requestedFrame = clampFrame(detectionFrameInput.value || 0);
  setTransportFrame(requestedFrame, { syncVideo: false });
}

function attachTargetVideoListeners(entry) {
  const video = activeTargetVideo();
  if (!video) {
    syncTransportControls();
    return;
  }

  video.addEventListener("loadedmetadata", () => {
    const fps = Number(entry?.fps || 0);
    if (fps <= 0 && Number.isFinite(video.duration) && video.duration > 0) {
      state.transport.fps = Math.max(
        0,
        Math.round((state.transport.frameMax / video.duration) * 1000) / 1000
      );
    }
    syncTransportControls();
    setTransportFrame(detectionFrameInput.value || 0, { syncVideo: true });
  });

  video.addEventListener("timeupdate", () => {
    if (state.transport.syncingVideo || state.transport.mediaType !== "video") {
      return;
    }
    const fps = Number(state.transport.fps || 0);
    if (fps <= 0) {
      return;
    }
    setTransportFrame(Math.round(video.currentTime * fps), { syncVideo: false });
  });

  video.addEventListener("play", () => {
    state.transport.playing = true;
    syncTransportControls();
  });

  video.addEventListener("pause", () => {
    state.transport.playing = false;
    syncTransportControls();
  });

  syncTransportControls();
}

function renderComparePreview() {
  const workflow = workflowState();
  const outputPath = state.processing?.outputPath || "";
  const outputUrl = state.processing?.outputDownloadUrl;
  if (outputPath && outputUrl && isImageFile(outputPath)) {
    stageComparePreview.className = "stage-screen";
    stageComparePreview.innerHTML = `
      <img src="${outputUrl}?t=${encodeURIComponent(
        state.processing?.finishedAt || Date.now()
      )}" alt="Swap output preview" />
      <div class="stage-overlay">
        <strong>Processed Output</strong>
        <span>${state.processing?.outputName || "Image output"}</span>
      </div>
    `;
    return;
  }

  if (outputPath && outputUrl && isVideoFile(outputPath)) {
    stageComparePreview.className = "stage-screen";
    stageComparePreview.innerHTML = `
      <video src="${outputUrl}?t=${encodeURIComponent(
        state.processing?.finishedAt || Date.now()
      )}" muted controls playsinline></video>
      <div class="stage-overlay">
        <strong>Processed Output</strong>
        <span>${state.processing?.outputName || "Video output"}</span>
      </div>
    `;
    return;
  }

  if (state.browserWorkflow?.swapPreview?.url && workflow.swapPreviewMatchesFrame) {
    const preview = state.browserWorkflow.swapPreview;
    stageComparePreview.className = "stage-screen";
    stageComparePreview.innerHTML = `
      <img
        src="${preview.url}?t=${encodeURIComponent(preview.updatedAt || Date.now())}"
        alt="Swapped preview frame"
      />
      <div class="stage-overlay">
        <strong>Swapped Preview</strong>
        <span>Frame ${preview.frameIndex ?? 0} • ${preview.sourceCount || 0} source face(s)</span>
      </div>
    `;
    return;
  }

  if (state.browserWorkflow?.previewFrame?.url && workflow.previewMatchesFrame) {
    const preview = state.browserWorkflow.previewFrame;
    stageComparePreview.className = "stage-screen";
    stageComparePreview.innerHTML = `
      <img
        src="${preview.url}?t=${encodeURIComponent(preview.updatedAt || Date.now())}"
        alt="Selected target frame preview"
      />
      <div class="stage-overlay">
        <strong>Detection Frame Preview</strong>
        <span>Frame ${preview.frameIndex ?? 0}</span>
      </div>
    `;
    return;
  }

  if (state.browserWorkflow?.targetMedia) {
    const entry = state.browserWorkflow.targetMedia;
    stageComparePreview.className = "stage-screen";
    stageComparePreview.innerHTML = `
      ${createMediaThumb(entry, targetMediaUrl(entry), { controls: entry.fileType === "video" })}
      <div class="stage-overlay">
        <strong>Preview Pending</strong>
        <span>${
          entry.fileType === "video"
            ? "Use Preview Frame for the selected detection frame, then Find Faces."
            : "Use Find Faces, then create a Swap Preview."
        }</span>
      </div>
    `;
    return;
  }

  stageComparePreview.className = "stage-screen empty";
  stageComparePreview.textContent = "No swap preview available.";
}

function renderTargetPreview(entry) {
  if (!entry) {
    targetMediaPreview.className = "browser-grid empty";
    targetMediaPreview.textContent = "No target media loaded.";
    stageTargetPreview.className = "stage-screen empty";
    stageTargetPreview.textContent = "No target preview available.";
    targetStageMeta.textContent = "No target media selected.";
    state.transport = {
      frameIndex: 0,
      frameMax: 0,
      fps: 0,
      mediaType: null,
      playing: false,
      syncingVideo: false,
    };
    syncTransportControls();
    renderComparePreview();
    return;
  }

  const mediaUrl = targetMediaUrl(entry);
  const previewMarkup = createMediaThumb(entry, mediaUrl);
  const dimensions =
    entry.width && entry.height ? `${entry.width}x${entry.height}` : "size unknown";
  const frameInfo =
    entry.fileType === "video" ? ` • ${entry.frameCount || 0} frames` : "";
  const meta = `${entry.name} • ${entry.fileType} • ${dimensions}${frameInfo} • ${new Date(
    entry.modifiedAt
  ).toLocaleString()}`;
  targetMediaPreview.className = "browser-grid";
  targetMediaPreview.innerHTML = `
    <article class="browser-item is-active">
      ${previewMarkup}
      <div class="browser-item-caption">
        <strong>${entry.name}</strong>
        <span>${entry.fileType}</span>
      </div>
    </article>
  `;

  const stageMarkup =
    entry.fileType === "video" && mediaUrl
      ? `
        <video
          id="stageTargetVideo"
          src="${mediaUrl}"
          muted
          controls
          preload="auto"
          playsinline
        ></video>
        <div class="stage-overlay">
          <strong>${entry.name}</strong>
          <span>Use transport controls to scrub, pause and preview a frame.</span>
        </div>
      `
      : `
        ${previewMarkup}
        <div class="stage-overlay">
          <strong>${entry.name}</strong>
          <span>${entry.fileType}</span>
        </div>
      `;
  stageTargetPreview.className = "stage-screen";
  stageTargetPreview.innerHTML = stageMarkup;
  targetStageMeta.textContent = meta;
  syncTransportFromTarget(entry);
  attachTargetVideoListeners(entry);
  renderComparePreview();
}

function renderSourcePreviews(entries = []) {
  if (!entries.length) {
    sourceFacePreviewList.className = "browser-grid input-grid empty";
    sourceFacePreviewList.textContent = "No source faces loaded.";
    sourceStageMeta.textContent = "No source faces selected.";
    return;
  }

  sourceFacePreviewList.className = "browser-grid input-grid";
  sourceFacePreviewList.innerHTML = entries
    .map((entry) => {
      const url = state.previewUrls.sources[entry.name];
      return `
        <article class="browser-item source-item">
          ${createMediaThumb(entry, url || sourceMediaUrl(entry))}
          <div class="browser-item-caption">
            <strong>${entry.name}</strong>
            <span>${entry.fileType}</span>
          </div>
        </article>
      `;
    })
    .join("");
  sourceStageMeta.textContent = `${entries.length} source face(s) loaded.`;
}

function renderDetectedTargetFaces(payload) {
  const faces = payload?.faces || [];
  const requestedFrame = clampFrame(detectionFrameInput.value || state.transport.frameIndex || 0);
  const isCurrentFrame = faces.length
    ? Number(payload?.frameIndex ?? 0) === requestedFrame
    : false;
  if (!faces.length) {
    targetFacesPreviewList.className = "browser-grid input-grid empty";
    targetFacesPreviewList.textContent = "No target faces detected yet.";
    return;
  }

  targetFacesPreviewList.className = "browser-grid input-grid";
  targetFacesPreviewList.innerHTML = faces
    .map(
      (entry) => `
        <article class="browser-item source-item">
          ${createMediaThumb(entry, entry.mediaUrl)}
          <div class="browser-item-caption">
            <strong>${entry.label || "Target Face"}</strong>
            <span>Frame ${entry.frameIndex ?? 0}</span>
          </div>
        </article>
      `
    )
    .join("");
  if (!isCurrentFrame) {
    targetFacesPreviewList.insertAdjacentHTML(
      "afterbegin",
      `
        <article class="workflow-warning">
          <strong>Outdated Detection</strong>
          <span>The shown faces belong to frame ${payload.frameIndex ?? 0}. Create a new Preview Frame and run Find Faces again for the current frame ${requestedFrame}.</span>
        </article>
      `
    );
  }
}

function assignStrategyLabel(strategy) {
  return (
    {
      first_source_to_all_targets: "First source face replaces all found target faces",
      source_order_to_target_order: "Source faces are assigned to found target faces in order",
    }[strategy] || strategy || "Not set"
  );
}

function renderWorkflowGuide(payload) {
  const workflow = workflowState(payload);
  workflowGuideTitle.textContent = workflow.isVideo
    ? "Video Swap Flow"
    : "Image Swap Flow";
  workflowGuideBadge.textContent = workflow.busyAction
    ? "Working"
    : workflow.canRun
      ? "Ready To Swap"
      : "Setup Needed";
  workflowGuideBadge.dataset.state = workflow.busyAction
    ? "working"
    : workflow.canRun
      ? "ready"
      : "pending";
  quickActionTitle.textContent = workflow.canRun
    ? "Ready To Run"
    : "Recommended Order";
  quickActionHint.textContent = workflow.nextAction;
  workflowNextAction.textContent = workflow.nextAction;
  workflowChecklist.innerHTML = workflow.steps
    .map(
      (step, index) => `
        <article class="workflow-step ${step.ready ? "is-ready" : "is-open"}">
          <span class="workflow-step-index">${index + 1}</span>
          <div>
            <strong>${step.label}</strong>
            <span>${step.detail}</span>
          </div>
        </article>
      `
    )
    .join("");
}

function renderBrowserWorkflow(payload) {
  state.browserWorkflow = payload;
  renderTargetPreview(payload.targetMedia);
  renderSourcePreviews(payload.sourceFaces || []);
  renderDetectedTargetFaces(payload.detectedTargetFaces);
  renderWorkflowGuide(payload);
  if (payload.previewFrame?.frameIndex !== undefined) {
    setTransportFrame(payload.previewFrame.frameIndex, { syncVideo: false });
  }
  renderWorkflowSummary(payload);
  updateProcessingActionState();
}

function renderWorkflowSummary(payload) {
  const workflow = workflowState(payload);
  workflowSummary.innerHTML = `
    <div class="summary-metric-grid">
      <article class="summary-metric">
        <span>Run Ready</span>
        <strong>${workflow.canRun ? "Yes" : "Not Yet"}</strong>
      </article>
      <article class="summary-metric">
        <span>Target Faces</span>
        <strong>${payload.detectedTargetFaces?.count || 0}</strong>
      </article>
      <article class="summary-metric">
        <span>Replace Strategy</span>
        <strong>${assignStrategyLabel(payload.assignStrategy)}</strong>
      </article>
      <article class="summary-metric">
        <span>Output Folder</span>
        <strong>${payload.outputFolder}</strong>
      </article>
    </div>
    <p class="workflow-summary-next">${workflow.nextAction}</p>
  `;
}

function renderProcessingStatus(payload) {
  state.processing = payload;
  processingBadge.textContent = processingStatusLabel(payload.status);
  setStatusTone(processingBadge, payload.status);
  processingMessage.textContent = payload.message || "Noch kein Lauf aktiv.";

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
    ? meta.map((line) => `<span class="processing-pill">${line}</span>`).join("")
    : '<span class="item-meta">Noch keine Laufmetadaten.</span>';

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

  const output = [];
  if (payload.outputPath) {
    output.push(`
      <article class="processing-output-card">
        <span>Ausgabe</span>
        <strong>${payload.outputPath}</strong>
      </article>
    `);
  }
  if (payload.outputDownloadUrl && payload.outputExists) {
    output.push(
      `<article class="processing-output-card processing-output-card-action"><a class="ghost inline-link" href="${payload.outputDownloadUrl}" target="_blank" rel="noreferrer">Ausgabe herunterladen</a></article>`
    );
  }
  if (payload.lastMessage) {
    output.push(`
      <article class="processing-output-card">
        <span>Hinweis</span>
        <strong>${payload.lastMessage}</strong>
      </article>
    `);
  }
  processingOutput.innerHTML = output.length
    ? output.join("")
    : '<div class="item-meta">Nach einem erfolgreichen Lauf erscheint hier der Ausgabepfad.</div>';
  processingLog.value = (payload.logTail || []).join("\n");
  renderComparePreview();

  const shouldPoll = ["starting", "loading", "running", "stopping"].includes(
    payload.status
  );
  if (shouldPoll && !state.processingPollHandle) {
    state.processingPollHandle = window.setInterval(() => {
      refreshProcessingStatus().catch((error) => showFlash(error.message, true));
    }, 2500);
  }
  if (!shouldPoll && state.processingPollHandle) {
    clearInterval(state.processingPollHandle);
    state.processingPollHandle = null;
  }

  updateProcessingActionState();
}

function getWorkbenchValue(key) {
  if (key in state.workbench.parameters) {
    return state.workbench.parameters[key];
  }
  return state.workbench.control[key];
}

function matchesToggleExpression(expression, expected) {
  const required = Boolean(expected);
  return expression
    .split("&")
    .map((part) => part.trim())
    .every((key) => Boolean(getWorkbenchValue(key)) === required);
}

function isControlVisible(control) {
  if (control.parentToggle) {
    const required = "requiredToggleValue" in control ? control.requiredToggleValue : true;
    if (!matchesToggleExpression(control.parentToggle, required)) {
      return false;
    }
  }
  if (control.parentSelection) {
    const value = getWorkbenchValue(control.parentSelection);
    if (value !== control.requiredSelectionValue) {
      return false;
    }
  }
  return true;
}

function formatControlValue(control, value) {
  if (control.type === "toggle") {
    return value ? "An" : "Aus";
  }
  if (control.type === "text") {
    const text = String(value || "").trim();
    if (!text) {
      return "leer";
    }
    return text.length > 22 ? `${text.slice(0, 22)}...` : text;
  }
  if (control.type === "range" && typeof control.decimals === "number") {
    return Number(value).toFixed(control.decimals);
  }
  return String(value);
}

function createWorkbenchInput(control, value) {
  const inputId = `workbench-${control.scope}-${control.key}`;
  if (control.type === "select") {
    return `
      <select id="${inputId}" data-control-key="${control.key}" data-control-scope="${control.scope}">
        ${control.options
          .map(
            (option) =>
              `<option value="${option}" ${option === value ? "selected" : ""}>${option}</option>`
          )
          .join("")}
      </select>
    `;
  }
  if (control.type === "toggle") {
    return `
      <label class="switch">
        <input
          id="${inputId}"
          type="checkbox"
          data-control-key="${control.key}"
          data-control-scope="${control.scope}"
          ${value ? "checked" : ""}
        />
        <span class="switch-ui"></span>
      </label>
    `;
  }
  if (control.type === "text") {
    return `
      <input
        id="${inputId}"
        type="text"
        value="${String(value ?? "").replace(/"/g, "&quot;")}"
        data-control-key="${control.key}"
        data-control-scope="${control.scope}"
      />
    `;
  }
  return `
    <div class="range-wrap">
      <input
        id="${inputId}"
        type="range"
        min="${control.min}"
        max="${control.max}"
        step="${control.step}"
        value="${value}"
        data-control-key="${control.key}"
        data-control-scope="${control.scope}"
      />
      <input
        class="range-number"
        type="number"
        min="${control.min}"
        max="${control.max}"
        step="${control.step}"
        value="${value}"
        data-range-mirror="${control.key}"
        data-control-key="${control.key}"
        data-control-scope="${control.scope}"
      />
    </div>
  `;
}

function displayWorkbenchTab(tab) {
  const ui = WORKBENCH_TAB_UI[tab.id] || {};
  return {
    ...tab,
    label: ui.label || tab.label,
    description: ui.description || tab.description,
  };
}

function findWorkbenchControl(scope, key) {
  for (const tab of state.workbenchTabs) {
    for (const section of tab.sections || []) {
      for (const control of section.controls || []) {
        if (control.scope === scope && control.key === key) {
          return control;
        }
      }
    }
  }
  return null;
}

function renderWorkbench() {
  const tabs = state.workbenchTabs.map(displayWorkbenchTab);
  const activeTab =
    tabs.find((tab) => tab.id === state.activeWorkbenchTab) || tabs[0];
  if (!activeTab) {
    workbenchTabs.innerHTML = "";
    workbenchSections.innerHTML = '<p class="panel-note">Keine Workbench-Daten geladen.</p>';
    return;
  }

  state.activeWorkbenchTab = activeTab.id;
  workbenchDescription.textContent = activeTab.description;
  workbenchTabs.innerHTML = tabs
    .map(
      (tab) => `
        <button
          class="control-tab ${tab.id === activeTab.id ? "is-active" : ""}"
          type="button"
          data-workbench-tab="${tab.id}"
        >
          ${tab.label}
        </button>
      `
    )
    .join("");

  workbenchSections.innerHTML = activeTab.sections
    .map((section) => {
      const controls = section.controls
        .filter((control) => isControlVisible(control))
        .map((control) => {
          const value = getWorkbenchValue(control.key);
          return `
            <article class="control-card">
              <div class="control-row-head">
                <label class="control-label" for="workbench-${control.scope}-${control.key}">
                  ${control.label}
                </label>
                <div class="control-row-actions">
                  <span class="control-value">${formatControlValue(control, value)}</span>
                  <button
                    class="control-reset"
                    type="button"
                    data-control-reset="${control.key}"
                    data-control-scope="${control.scope}"
                    aria-label="Reset ${control.label}"
                  >
                    ↺
                  </button>
                </div>
              </div>
              <p class="control-help">${control.help || ""}</p>
              <div class="control-input">
                ${createWorkbenchInput(control, value)}
              </div>
            </article>
          `;
        })
        .join("");

      return `
        <section class="control-section">
          <div class="control-section-header">
            <h3>${section.title}</h3>
          </div>
          <div class="control-grid">
            ${controls || '<p class="panel-note">Fuer die aktuelle Auswahl sind hier keine Controls sichtbar.</p>'}
          </div>
        </section>
      `;
    })
    .join("");

  const enabledParameters = Object.entries(state.workbench.parameters).filter(
    ([, value]) => value === true
  ).length;
  workbenchSummary.innerHTML = `
    <span><strong>${activeTab.label}</strong> aktiv</span>
    <span>${Object.keys(state.workbench.parameters).length} Parameterwerte</span>
    <span>${Object.keys(state.workbench.control).length} Control-Werte</span>
    <span>${enabledParameters} Toggle(s) aktiviert</span>
  `;
}

function scheduleWorkbenchSave() {
  if (state.workbenchSaveHandle) {
    clearTimeout(state.workbenchSaveHandle);
  }
  state.workbenchSaveHandle = window.setTimeout(() => {
    saveWorkbench(true).catch((error) => showFlash(error.message, true));
  }, 500);
}

function normalizeControlInputValue(control, input) {
  if (control.type === "toggle") {
    return Boolean(input.checked);
  }
  if (control.type === "range") {
    return control.step && String(control.step).includes(".")
      ? Number(input.value)
      : Math.round(Number(input.value));
  }
  return input.value;
}

function controlDefinitionForElement(element) {
  const tab = state.workbenchTabs.find((entry) => entry.id === state.activeWorkbenchTab);
  if (!tab) {
    return null;
  }
  for (const section of tab.sections) {
    for (const control of section.controls) {
      if (
        control.key === element.dataset.controlKey &&
        control.scope === element.dataset.controlScope
      ) {
        return control;
      }
    }
  }
  return null;
}

function setWorkbenchValue(scope, key, value) {
  state.workbench[scope][key] = value;
}

function setUtilityTab(tab) {
  state.utilityTab = tab;
  document.querySelectorAll("[data-utility-tab]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.utilityTab === tab);
  });
  document.querySelectorAll("[data-utility-view]").forEach((view) => {
    view.classList.toggle("is-active", view.dataset.utilityView === tab);
  });
}

function setLeftDockTab(tab) {
  state.leftDockTab = tab;
  document.querySelectorAll("[data-left-dock-tab]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.leftDockTab === tab);
  });
  document.querySelectorAll("[data-left-dock-view]").forEach((view) => {
    view.classList.toggle("is-active", view.dataset.leftDockView === tab);
  });
}

function setCenterPaneTab(tab) {
  state.centerPaneTab = tab;
  document.querySelectorAll("[data-center-pane-tab]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.centerPaneTab === tab);
  });
  document.querySelectorAll("[data-center-pane-view]").forEach((view) => {
    view.classList.toggle("is-active", view.dataset.centerPaneView === tab);
  });
}

function selectEditor(type, name, data, subtitle) {
  state.selection = { type, name };
  editorTitle.textContent = `${translateCollectionName(type)}: ${name}`;
  editorSubtitle.textContent = subtitle;
  nameInput.value = name;
  jsonEditor.value = JSON.stringify(data, null, 2);
  saveButton.disabled = false;
  deleteButton.disabled = type === "workspace";
  setLeftDockTab("tools");
  setUtilityTab("editor");
  renderAllLists();
  updateProcessingActionState();
}

function setDefaultEditorState() {
  editorTitle.textContent = "JSON-Editor";
  editorSubtitle.textContent =
    "Oeffne links einen Job, ein Preset, ein Embedding, einen Export oder den Workspace.";
  nameInput.value = "";
  jsonEditor.value = "";
  saveButton.disabled = true;
  deleteButton.disabled = true;
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
  state.embeddingDraft = { fileName: "", name: "", embedding_store: {} };
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
    !payload[0].embedding_store
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
  setLeftDockTab("tools");
  setUtilityTab("builder");
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

function ensureDraftReady() {
  const fileName = builderFileName.value.trim() || builderEmbeddingName.value.trim();
  const embeddingName = builderEmbeddingName.value.trim() || builderFileName.value.trim();
  if (!fileName) {
    throw new Error("Bitte einen Dateinamen oder Embedding-Namen angeben.");
  }
  if (!embeddingName) {
    throw new Error("Bitte einen Embedding-Namen angeben.");
  }
  if (!Object.keys(state.embeddingDraft.embedding_store).length) {
    throw new Error("Bitte mindestens ein Modell hinzufuegen.");
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
    state.embeddingDraft.embedding_store[modelName] = parseVectorValues(
      builderVectorInput.value
    );
    state.embeddingDraft.fileName =
      builderFileName.value.trim() || state.embeddingDraft.fileName;
    state.embeddingDraft.name =
      builderEmbeddingName.value.trim() ||
      builderFileName.value.trim() ||
      state.embeddingDraft.name;
    builderModelName.value = "";
    builderVectorInput.value = "";
    renderEmbeddingDraft();
    showFlash(`Modell "${modelName}" hinzugefuegt.`);
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function saveDraftEmbedding() {
  clearFlash();
  try {
    ensureDraftReady();
    await request(`/api/embeddings/${encodeURIComponent(state.embeddingDraft.fileName)}`, {
      method: "POST",
      body: JSON.stringify(draftPayload()),
    });
    showFlash(`Embedding "${state.embeddingDraft.fileName}" gespeichert.`);
    await refreshCollection("embeddings");
    await refreshStatus();
  } catch (error) {
    showFlash(error.message, true);
  }
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
  renderStatus(await request("/api/status"));
}

async function refreshProcessingStatus() {
  renderProcessingStatus(await request("/api/processing/status"));
}

async function refreshBrowserWorkflow() {
  renderBrowserWorkflow(await request("/api/browser-workflow"));
}

async function refreshWorkbench() {
  const payload = await request("/api/workbench");
  state.workbenchTabs = payload.tabs || [];
  state.workbenchDefaults = payload.defaults || { control: {}, parameters: {} };
  state.workbench = payload.state || { control: {}, parameters: {} };
  state.activeWorkbenchTab =
    state.activeWorkbenchTab || state.workbenchTabs[0]?.id || null;
  renderWorkbench();
}

async function refreshAll() {
  clearFlash();
  await Promise.all([
    refreshStatus(),
    refreshProcessingStatus(),
    refreshBrowserWorkflow(),
    refreshWorkbench(),
    refreshCollection("jobs"),
    refreshCollection("job-exports"),
    refreshCollection("presets"),
    refreshCollection("embeddings"),
    refreshWorkspaceSummary(),
  ]);
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
        "Dieser Inhalt wird als last_workspace.json im Projekt gespeichert."
      );
      return;
    }
    const payload = await request(`/api/${type}/${encodeURIComponent(name)}`);
    const subtitleMap = {
      jobs: "Job-Definition fuer die Desktop-Queue und den Browser-Start.",
      "job-exports": "Eigenstaendiger Job-Export im aktuellen Workspace-Format.",
      presets: "Preset-Paar aus Parameter- und Control-JSON.",
      embeddings: "Embedding-Datei fuer die Source-Face-Zuordnung.",
    };
    selectEditor(type, name, payload, subtitleMap[type]);
    if (type === "embeddings") {
      hydrateBuilderFromPayload(name, payload);
    }
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
      showFlash("Workspace gespeichert.");
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
    await request(`/api/${currentType}/${encodeURIComponent(currentName)}`, {
      method: "DELETE",
    });
    showFlash(`${translateCollectionName(currentType)} geloescht.`);
    state.selection = null;
    setDefaultEditorState();
    await refreshCollection(currentType);
    await refreshStatus();
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function saveWorkbench(silent = false) {
  state.workbenchSaveHandle = null;
  const payload = await request("/api/workbench", {
    method: "POST",
    body: JSON.stringify(state.workbench),
  });
  state.workbench = payload.state;
  renderWorkbench();
  if (!silent) {
    showFlash("Workbench-Draft gespeichert.");
  }
}

function resetWorkbench() {
  state.workbench = JSON.parse(JSON.stringify(state.workbenchDefaults));
  renderWorkbench();
  scheduleWorkbenchSave();
  showFlash("Workbench auf Default-Werte zurueckgesetzt.");
}

async function uploadTargetMedia() {
  clearFlash();
  setUiBusy("Zielmedium wird hochgeladen...");
  try {
    const files = Array.from(targetUploadInput.files || []);
    if (!files.length) {
      throw new Error("Bitte zuerst ein Zielmedium auswaehlen.");
    }
    setTargetPreviewFromInput(files);
    const payload = await uploadRequest("/api/browser-workflow/target", files);
    setLeftDockTab("media");
    renderBrowserWorkflow(payload.state);
    showFlash(`Zielmedium "${payload.saved.name}" hochgeladen.`);
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setUiBusy(null);
  }
}

async function uploadSourceFaces() {
  clearFlash();
  setUiBusy("Quellgesichter werden hochgeladen...");
  try {
    const files = Array.from(sourceUploadInput.files || []);
    if (!files.length) {
      throw new Error("Bitte zuerst mindestens ein Quellgesicht auswaehlen.");
    }
    setSourcePreviewsFromInput(files);
    const payload = await uploadRequest("/api/browser-workflow/sources", files);
    setLeftDockTab("media");
    renderBrowserWorkflow(payload.state);
    showFlash(`${payload.saved.length} Quellgesicht(er) hochgeladen.`);
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setUiBusy(null);
  }
}

async function resetWorkflow() {
  clearFlash();
  setUiBusy("Session wird geleert...");
  try {
    releaseActiveTargetVideo();
    revokePreviewUrls();
    targetUploadInput.value = "";
    sourceUploadInput.value = "";
    detectionFrameInput.value = "0";
    setLeftDockTab("media");
    renderBrowserWorkflow(
      await request("/api/browser-workflow/reset", {
        method: "POST",
        body: JSON.stringify({}),
      })
    );
    showFlash("Direktlauf-Zustand geleert.");
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setUiBusy(null);
  }
}

async function runUploadedWorkflow() {
  clearFlash();
  const workflow = workflowState();
  if (!workflow.canRun) {
    showFlash(workflow.nextAction, true);
    return;
  }
  setUiBusy("Swap Faces wird gestartet...");
  try {
    const parsedFrame = Number(detectionFrameInput.value || 0);
    const detectionFrame = Number.isFinite(parsedFrame)
      ? Math.max(0, Math.floor(parsedFrame))
      : 0;
    renderProcessingStatus(
      await request("/api/browser-workflow/run", {
        method: "POST",
        body: JSON.stringify({
          detectionFrame,
          workbench: state.workbench,
        }),
      })
    );
    setCenterPaneTab("output");
    showFlash("Browser-Direktlauf gestartet.");
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setUiBusy(null);
  }
}

async function previewTargetFrame() {
  clearFlash();
  if (!state.browserWorkflow?.targetMedia) {
    showFlash("Bitte zuerst ein Zielmedium laden.", true);
    return;
  }
  setUiBusy("Preview Frame wird erzeugt...");
  try {
    const payload = await request("/api/browser-workflow/preview/frame", {
      method: "POST",
      body: JSON.stringify({
        frameIndex: clampFrame(state.transport.frameIndex),
      }),
    });
    setCenterPaneTab("output");
    renderBrowserWorkflow(payload.state);
    showFlash(`Frame ${payload.previewFrame?.frameIndex ?? 0} als Preview geladen.`);
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setUiBusy(null);
  }
}

async function previewSwapFrame() {
  clearFlash();
  const workflow = workflowState();
  if (!workflow.canSwapPreview) {
    showFlash(workflow.nextAction, true);
    return;
  }
  setUiBusy("Swap Preview wird berechnet...");
  const originalLabel = transportSwapPreviewButton.textContent;
  transportSwapPreviewButton.disabled = true;
  transportSwapPreviewButton.textContent = "Rendering...";
  try {
    const payload = await request("/api/browser-workflow/preview/swap", {
      method: "POST",
      body: JSON.stringify({
        frameIndex: clampFrame(state.transport.frameIndex),
        workbench: state.workbench,
      }),
    });
    renderBrowserWorkflow(payload.state);
    showFlash("Geswappte Vorschau wurde aktualisiert.");
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setUiBusy(null);
    transportSwapPreviewButton.textContent = originalLabel;
    syncTransportControls();
  }
}

async function findTargetFaces() {
  clearFlash();
  setLeftDockTab("media");
  const workflow = workflowState();
  if (!workflow.canFindFaces) {
    showFlash(workflow.nextAction, true);
    return;
  }
  setUiBusy("Target Faces werden gesucht...");
  setFindFacesBusy(true);
  try {
    const payload = await request("/api/browser-workflow/find-faces", {
      method: "POST",
      body: JSON.stringify({
        frameIndex: clampFrame(state.transport.frameIndex),
        workbench: state.workbench,
      }),
    });
    renderBrowserWorkflow(payload.state);
    showFlash(payload.message || "Zielgesichter wurden gefunden.");
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setUiBusy(null);
    setFindFacesBusy(false);
    updateProcessingActionState();
  }
}

async function clearTargetFaces() {
  clearFlash();
  setUiBusy("Gefundene Zielgesichter werden geleert...");
  try {
    setLeftDockTab("media");
    const payload = await request("/api/browser-workflow/faces/clear", {
      method: "POST",
      body: JSON.stringify({}),
    });
    renderBrowserWorkflow(payload.state);
    showFlash(payload.message || "Gefundene Zielgesichter wurden geleert.");
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    setUiBusy(null);
  }
}

function stepTargetFrame(delta) {
  const nextFrame = clampFrame(state.transport.frameIndex + delta);
  const video = activeTargetVideo();
  if (video && !video.paused) {
    video.pause();
  }
  setTransportFrame(nextFrame, { syncVideo: true });
}

function toggleTargetPlayback() {
  const video = activeTargetVideo();
  if (!video || state.transport.mediaType !== "video") {
    return;
  }
  if (video.paused) {
    video.play().catch((error) => showFlash(error.message, true));
  } else {
    video.pause();
  }
}

async function startSelectedJob() {
  if (!state.selection || state.selection.type !== "jobs") {
    showFlash("Bitte zuerst einen gespeicherten Job auswaehlen.", true);
    return;
  }
  clearFlash();
  try {
    renderProcessingStatus(
      await request(`/api/processing/jobs/${encodeURIComponent(state.selection.name)}/start`, {
        method: "POST",
      })
    );
    setCenterPaneTab("output");
    showFlash(`Browser-Verarbeitung fuer "${state.selection.name}" gestartet.`);
  } catch (error) {
    showFlash(error.message, true);
  }
}

async function stopProcessing() {
  clearFlash();
  try {
    renderProcessingStatus(
      await request("/api/processing/stop", {
        method: "POST",
      })
    );
    setCenterPaneTab("output");
    showFlash("Browser-Verarbeitung gestoppt.");
  } catch (error) {
    showFlash(error.message, true);
  }
}

document.getElementById("refreshAllButton").addEventListener("click", () => {
  refreshAll().catch((error) => showFlash(error.message, true));
});
resetLayoutButton.addEventListener("click", () => {
  if (window.VisoMasterLayout?.reset) {
    window.VisoMasterLayout.reset();
    showFlash("Layout wurde zurueckgesetzt.");
    return;
  }
  showFlash("Layout ist noch nicht bereit. Bitte Seite neu laden.", true);
});
document.querySelectorAll("[data-refresh]").forEach((button) => {
  button.addEventListener("click", () => {
    refreshCollection(button.dataset.refresh).catch((error) =>
      showFlash(error.message, true)
    );
  });
});
leftDockNav.addEventListener("click", (event) => {
  const button = event.target.closest("[data-left-dock-tab]");
  if (!button) {
    return;
  }
  setLeftDockTab(button.dataset.leftDockTab);
});
centerPaneNav.addEventListener("click", (event) => {
  const button = event.target.closest("[data-center-pane-tab]");
  if (!button) {
    return;
  }
  setCenterPaneTab(button.dataset.centerPaneTab);
});
document.getElementById("loadWorkspaceButton").addEventListener("click", () => {
  loadItem("workspace", "last_workspace");
});

uploadTargetButton.addEventListener("click", uploadTargetMedia);
uploadSourcesButton.addEventListener("click", uploadSourceFaces);
findTargetFacesButton.addEventListener("click", findTargetFaces);
clearTargetFacesButton.addEventListener("click", clearTargetFaces);
quickFindTargetFacesButton.addEventListener("click", findTargetFaces);
quickSwapPreviewButton.addEventListener("click", previewSwapFrame);
quickRunWorkflowButton.addEventListener("click", runUploadedWorkflow);
workflowResetButton.addEventListener("click", resetWorkflow);
workflowRunButton.addEventListener("click", runUploadedWorkflow);
transportPrevFrameButton.addEventListener("click", () => stepTargetFrame(-1));
transportPlayButton.addEventListener("click", toggleTargetPlayback);
transportNextFrameButton.addEventListener("click", () => stepTargetFrame(1));
transportPreviewButton.addEventListener("click", previewTargetFrame);
transportSwapPreviewButton.addEventListener("click", previewSwapFrame);
transportFrameSlider.addEventListener("input", () => {
  setTransportFrame(transportFrameSlider.value, { syncVideo: true });
});
transportFrameInput.addEventListener("change", () => {
  setTransportFrame(transportFrameInput.value, { syncVideo: true });
});
detectionFrameInput.addEventListener("change", () => {
  setTransportFrame(detectionFrameInput.value, { syncVideo: true });
});
processingRefreshButton.addEventListener("click", () => {
  refreshProcessingStatus().catch((error) => showFlash(error.message, true));
});
processingStartButton.addEventListener("click", startSelectedJob);
processingStopButton.addEventListener("click", stopProcessing);

saveButton.addEventListener("click", saveCurrentSelection);
deleteButton.addEventListener("click", deleteCurrentSelection);

builderAddModelButton.addEventListener("click", addModelToDraft);
builderSaveButton.addEventListener("click", saveDraftEmbedding);
builderResetButton.addEventListener("click", () => {
  clearFlash();
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

  document.querySelectorAll("[data-utility-tab]").forEach((button) => {
    button.addEventListener("click", () => setUtilityTab(button.dataset.utilityTab));
  });

workbenchTabs.addEventListener("click", (event) => {
  const button = event.target.closest("[data-workbench-tab]");
  if (!button) {
    return;
  }
  state.activeWorkbenchTab = button.dataset.workbenchTab;
  renderWorkbench();
});

workbenchSections.addEventListener("input", (event) => {
  const input = event.target.closest("[data-control-key]");
  if (!input) {
    return;
  }
  const control = controlDefinitionForElement(input);
  if (!control) {
    return;
  }
  const value = normalizeControlInputValue(control, input);
  setWorkbenchValue(input.dataset.controlScope, input.dataset.controlKey, value);

  const mirrors = workbenchSections.querySelectorAll(
    `[data-range-mirror="${input.dataset.controlKey}"]`
  );
  mirrors.forEach((mirror) => {
    if (mirror !== input) {
      mirror.value = value;
    }
  });

  const ranges = workbenchSections.querySelectorAll(
    `input[type="range"][data-control-key="${input.dataset.controlKey}"]`
  );
  ranges.forEach((range) => {
    if (range !== input) {
      range.value = value;
    }
  });

  const valueLabel = input
    .closest(".control-card")
    ?.querySelector(".control-value");
  if (valueLabel) {
    valueLabel.textContent = formatControlValue(control, value);
  }

  if (control.type === "toggle" || control.type === "select") {
    renderWorkbench();
  }
  scheduleWorkbenchSave();
});

workbenchSections.addEventListener("click", (event) => {
  const button = event.target.closest("[data-control-reset]");
  if (!button) {
    return;
  }
  const control = findWorkbenchControl(
    button.dataset.controlScope,
    button.dataset.controlReset
  );
  if (!control) {
    return;
  }
  setWorkbenchValue(
    button.dataset.controlScope,
    button.dataset.controlReset,
    JSON.parse(JSON.stringify(control.default))
  );
  renderWorkbench();
  scheduleWorkbenchSave();
});

saveWorkbenchButton.addEventListener("click", () => {
  saveWorkbench(false).catch((error) => showFlash(error.message, true));
});
resetWorkbenchButton.addEventListener("click", resetWorkbench);

setDefaultEditorState();
resetEmbeddingBuilder();
setLeftDockTab("media");
setCenterPaneTab("output");
setUtilityTab("status");
refreshAll().catch((error) => showFlash(error.message, true));
