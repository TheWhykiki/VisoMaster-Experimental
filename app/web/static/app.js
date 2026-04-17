const state = {
  selection: null,
  collections: {
    jobs: [],
    "job-exports": [],
    presets: [],
  },
};

const jobsList = document.getElementById("jobsList");
const jobExportsList = document.getElementById("jobExportsList");
const presetsList = document.getElementById("presetsList");
const workspaceSummary = document.getElementById("workspaceSummary");
const statusCards = document.getElementById("statusCards");
const statusBadge = document.getElementById("statusBadge");
const nameInput = document.getElementById("nameInput");
const jsonEditor = document.getElementById("jsonEditor");
const editorTitle = document.getElementById("editorTitle");
const editorSubtitle = document.getElementById("editorSubtitle");
const saveButton = document.getElementById("saveButton");
const deleteButton = document.getElementById("deleteButton");
const flashMessage = document.getElementById("flashMessage");

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

function formatMeta(item) {
  if (item.invalid) {
    return "Ungültiges JSON";
  }
  const bits = [];
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

function renderStatus(status) {
  statusBadge.textContent = status.project.browserUi ? "Web bereit" : "Eingeschränkt";
  const cards = [
    ["Plattform", status.runtime.platform],
    ["Python", status.runtime.pythonVersion],
    ["FFmpeg", status.binaries.ffmpeg || "nicht gefunden"],
    ["FFplay", status.binaries.ffplay || "nicht gefunden"],
    ["Jobs", String(status.data.jobs)],
    ["Presets", String(status.data.presets)],
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
  const target =
    type === "jobs"
      ? jobsList
      : type === "job-exports"
        ? jobExportsList
        : presetsList;
  renderList(target, payload.items, type);
}

async function refreshWorkspaceSummary() {
  const payload = await request("/api/workspaces/last");
  renderWorkspaceSummary(payload.summary);
}

async function refreshStatus() {
  const payload = await request("/api/status");
  renderStatus(payload);
}

async function refreshAll() {
  clearFlash();
  await Promise.all([
    refreshStatus(),
    refreshCollection("jobs"),
    refreshCollection("job-exports"),
    refreshCollection("presets"),
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
  renderList(jobsList, state.collections.jobs, "jobs");
  renderList(jobExportsList, state.collections["job-exports"], "job-exports");
  renderList(presetsList, state.collections.presets, "presets");
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
      return;
    }

    const payload = await request(`/api/${type}/${encodeURIComponent(name)}`);
    const subtitleMap = {
      jobs: "Job-Definition für die Warteschlange der Desktop-Jobverwaltung.",
      "job-exports": "Eigenständiger Job-Export, kompatibel mit dem aktuellen Workspace-Serializer.",
      presets: "Preset-Paar aus Parameter-JSON und Steuerungs-JSON.",
    };
    selectEditor(type, name, payload, subtitleMap[type]);
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
    if (state.selection.type === "presets") {
      await loadItem("presets", name);
    }
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
    await request(
      `/api/${currentType}/${encodeURIComponent(state.selection.name)}`,
      {
        method: "DELETE",
      }
    );
    showFlash(`${translateCollectionName(currentType)} gelöscht.`);
    state.selection = null;
    editorTitle.textContent = "JSON-Editor";
    editorSubtitle.textContent =
      "Wähle einen Job, ein Preset, einen Job-Export oder den letzten Arbeitsbereich aus.";
    nameInput.value = "";
    jsonEditor.value = "";
    saveButton.disabled = true;
    deleteButton.disabled = true;
    await refreshCollection(currentType);
    await refreshAll();
  } catch (error) {
    showFlash(error.message, true);
  }
}

function translateCollectionName(type) {
  const labels = {
    jobs: "Job",
    "job-exports": "Job-Export",
    presets: "Preset",
    workspace: "Arbeitsbereich",
  };
  return labels[type] || type;
}

document.getElementById("refreshAllButton").addEventListener("click", refreshAll);
document.getElementById("loadWorkspaceButton").addEventListener("click", () => {
  loadItem("workspace", "last_workspace");
});
document.querySelectorAll("[data-refresh]").forEach((button) => {
  button.addEventListener("click", () =>
    refreshCollection(button.getAttribute("data-refresh"))
  );
});
saveButton.addEventListener("click", saveCurrentSelection);
deleteButton.addEventListener("click", deleteCurrentSelection);

refreshAll().catch((error) => showFlash(error.message, true));
