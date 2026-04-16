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
    return "Invalid JSON";
  }
  const bits = [];
  if (item.targetFaceCount !== undefined) {
    bits.push(`${item.targetFaceCount} target faces`);
  }
  if (item.markerCount !== undefined) {
    bits.push(`${item.markerCount} markers`);
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
    empty.textContent = "Nothing stored yet.";
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
  statusBadge.textContent = status.project.browserUi ? "Web Ready" : "Limited";
  const cards = [
    ["Platform", status.runtime.platform],
    ["Python", status.runtime.pythonVersion],
    ["FFmpeg", status.binaries.ffmpeg || "not found"],
    ["FFplay", status.binaries.ffplay || "not found"],
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
    workspaceSummary.textContent = "No last workspace has been saved yet.";
    return;
  }
  workspaceSummary.innerHTML = `
    <strong>${summary.targetFaceCount}</strong> target faces<br />
    <strong>${summary.inputFaceCount}</strong> input faces<br />
    <strong>${summary.markerCount}</strong> markers<br />
    Updated ${new Date(summary.modifiedAt).toLocaleString()}
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
  editorTitle.textContent = `${type}: ${name}`;
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
        "This payload is stored at the project root as last_workspace.json."
      );
      return;
    }

    const payload = await request(`/api/${type}/${encodeURIComponent(name)}`);
    const subtitleMap = {
      jobs: "Queue job definition used by the desktop job manager.",
      "job-exports": "Standalone job export compatible with the current workspace serializer.",
      presets: "Preset pair made of parameter JSON plus control JSON.",
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
      showFlash("Last workspace saved.");
      await refreshWorkspaceSummary();
      return;
    }

    if (!name) {
      throw new Error("Name must not be empty.");
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
    showFlash(`${state.selection.type} saved.`);
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
    showFlash(`${currentType} deleted.`);
    state.selection = null;
    editorTitle.textContent = "JSON Editor";
    editorSubtitle.textContent =
      "Select a job, preset, job export or the last workspace.";
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
