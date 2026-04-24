import { GoldenLayout } from "./vendor/golden-layout/esm/index.js";

const LAYOUT_STORAGE_KEY = "visomaster:web-layout:v4";
const LEGACY_LAYOUT_STORAGE_KEYS = [
  "visomaster:web-layout:v1",
  "visomaster:web-layout:v2",
  "visomaster:web-layout:v3",
];

function defaultLayoutConfig() {
  return {
    settings: {
      hasHeaders: true,
      reorderEnabled: true,
      showCloseIcon: false,
      showPopoutIcon: false,
      popInOnClose: false,
    },
    dimensions: {
      borderWidth: 6,
      headerHeight: 34,
      minItemHeight: 240,
      minItemWidth: 280,
    },
    root: {
      type: "row",
      content: [
        {
          type: "component",
          title: "Workflow",
          size: "27%",
          componentType: "workspace-panel",
          componentState: { panelId: "workflow" },
        },
        {
          type: "column",
          size: "48%",
          content: [
            {
              type: "component",
              title: "Viewer",
              size: "64%",
              componentType: "workspace-panel",
              componentState: { panelId: "viewer" },
            },
            {
              type: "component",
              title: "Output",
              size: "36%",
              componentType: "workspace-panel",
              componentState: { panelId: "output" },
            },
          ],
        },
        {
          type: "component",
          title: "Parameters",
          size: "25%",
          componentType: "workspace-panel",
          componentState: { panelId: "parameters" },
        },
      ],
    },
  };
}

function loadSavedLayout() {
  try {
    const raw = window.localStorage.getItem(LAYOUT_STORAGE_KEY);
    if (!raw) {
      return defaultLayoutConfig();
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      return defaultLayoutConfig();
    }
    return parsed;
  } catch {
    return defaultLayoutConfig();
  }
}

function saveLayout(layout) {
  try {
    window.localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(layout.saveLayout()));
  } catch {
    // Ignore storage failures so the workbench itself keeps running.
  }
}

function clearSavedLayouts() {
  try {
    [LAYOUT_STORAGE_KEY, ...LEGACY_LAYOUT_STORAGE_KEYS].forEach((key) =>
      window.localStorage.removeItem(key)
    );
  } catch {
    // Ignore storage cleanup failures; the live layout can still be reset in memory.
  }
}

function setLayoutReady(isReady) {
  document.documentElement.classList.toggle("layout-ready", isReady);
}

function reportLayoutFailure(message) {
  const flash = document.getElementById("globalFlash");
  if (!(flash instanceof HTMLElement)) {
    return;
  }
  flash.hidden = false;
  flash.className = "global-flash error";
  flash.textContent =
    message ||
    "Die andockbare Workbench konnte nicht initialisiert werden. Die einfache Fallback-Ansicht bleibt aktiv.";
}

function createFallbackPanel(panelId) {
  const fallback = document.createElement("section");
  fallback.className = "dock-panel layout-panel-template";
  fallback.innerHTML = `
    <div class="dock-header">
      <div>
        <p class="eyebrow">Layout</p>
        <h2>Panel Missing</h2>
      </div>
    </div>
    <p class="panel-note">The panel "${panelId}" could not be mounted.</p>
  `;
  return fallback;
}

function mountPanels(layoutRoot, panelTemplates) {
  const panelNodes = new Map(
    Array.from(panelTemplates.querySelectorAll("[data-layout-panel]")).map((panel) => [
      panel.dataset.layoutPanel,
      panel,
    ])
  );

  const layout = new GoldenLayout(layoutRoot);

  layout.registerComponentFactoryFunction("workspace-panel", (container, componentState) => {
    const panelId = componentState?.panelId;
    const panel = panelNodes.get(panelId) || createFallbackPanel(String(panelId || "unknown"));

    panel.hidden = false;
    panel.classList.add("layout-panel-mounted");
    container.element.appendChild(panel);
    container.stateRequestEvent = () => ({ panelId });

    container.on("beforeComponentRelease", () => {
      panel.hidden = true;
      panelTemplates.appendChild(panel);
    });

    return { panelId };
  });

  try {
    layout.loadLayout(loadSavedLayout());
  } catch (error) {
    clearSavedLayouts();
    layout.loadLayout(defaultLayoutConfig());
  }
  layout.on("stateChanged", () => saveLayout(layout));

  const syncSize = () => {
    const width = layoutRoot.clientWidth;
    const height = layoutRoot.clientHeight;
    if (width > 0 && height > 0) {
      layout.setSize(width, height);
    }
  };

  const resizeObserver = new ResizeObserver(() => syncSize());
  resizeObserver.observe(layoutRoot);
  window.addEventListener("resize", syncSize);
  window.addEventListener("beforeunload", () => saveLayout(layout));
  syncSize();

  window.VisoMasterLayout = {
    instance: layout,
    storageKey: LAYOUT_STORAGE_KEY,
    clearSavedLayouts,
    reset() {
      clearSavedLayouts();
      layout.loadLayout(defaultLayoutConfig());
      saveLayout(layout);
      syncSize();
    },
  };

  setLayoutReady(true);
}

window.addEventListener(
  "DOMContentLoaded",
  () => {
    const layoutRoot = document.getElementById("layoutRoot");
    const panelTemplates = document.getElementById("panelTemplates");
    if (!(layoutRoot instanceof HTMLElement) || !(panelTemplates instanceof HTMLElement)) {
      return;
    }
    try {
      mountPanels(layoutRoot, panelTemplates);
    } catch (error) {
      setLayoutReady(false);
      reportLayoutFailure(
        error instanceof Error
          ? error.message
          : "Die Workbench konnte nicht initialisiert werden."
      );
      console.error("VisoMaster layout bootstrap failed", error);
    }
  },
  { once: true }
);
