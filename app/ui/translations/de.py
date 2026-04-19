from __future__ import annotations

from PySide6 import QtWidgets


def _set_text(widget, text: str) -> None:
    widget.setText(text)


def _set_title(widget, title: str) -> None:
    widget.setTitle(title)


def _set_window_title(widget, title: str) -> None:
    widget.setWindowTitle(title)


def _set_tooltip(widget, tooltip: str) -> None:
    widget.setToolTip(tooltip)


def _set_placeholder(widget, text: str) -> None:
    widget.setPlaceholderText(text)


def apply_german_main_window_translation(window: QtWidgets.QMainWindow) -> None:
    text_updates = (
        (window, _set_window_title, "VisoMaster v0.1.6 - Fusion"),
        (window.actionExit, _set_text, "Beenden"),
        (window.actionLoad_Embeddings, _set_text, "Einbettungen laden"),
        (window.actionSave_Embeddings, _set_text, "Einbettungen speichern"),
        (window.actionSave_Embeddings_As, _set_text, "Einbettungen speichern unter"),
        (
            window.actionOpen_Videos_Folder,
            _set_text,
            "Ordner mit Zielbildern/-videos laden",
        ),
        (
            window.actionOpen_Video_Files,
            _set_text,
            "Zielbild-/Videodateien laden",
        ),
        (
            window.actionLoad_Source_Images_Folder,
            _set_text,
            "Ordner mit Quellbildern laden",
        ),
        (
            window.actionLoad_Source_Image_Files,
            _set_text,
            "Quelldateien laden",
        ),
        (window.actionView_Fullscreen_F11, _set_text, "Vollbild anzeigen (F11)"),
        (window.actionView_Help_Shortcuts, _set_text, "Tastenkürzel anzeigen"),
        (window.actionView_Help_Presets, _set_text, "Voreinstellungen"),
        (window.actionLoad_Saved_Workspace, _set_text, "Gespeicherten Arbeitsbereich laden"),
        (window.actionSave_Current_Workspace, _set_text, "Aktuellen Arbeitsbereich speichern"),
        (window.actionLoad_SavedWorkspace, _set_text, "Gespeicherten Arbeitsbereich laden"),
        (window.actionSave_CurrentWorkspace, _set_text, "Aktuellen Arbeitsbereich speichern"),
        (window.TargetMediaCheckBox, _set_text, "Zielvideos/-bilder"),
        (window.InputFacesCheckBox, _set_text, "Quellgesichter"),
        (window.JobsCheckBox, _set_text, "Jobs"),
        (window.facesPanelCheckBox, _set_text, "Gesichter"),
        (window.parametersPanelCheckBox, _set_text, "Parameter"),
        (window.faceCompareCheckBox, _set_text, "Gesichtsvergleich"),
        (window.faceMaskCheckBox, _set_text, "Gesichtsmaske"),
        (window.videoSeekLineEdit, _set_tooltip, "Bildnummer"),
        (
            window.liveSoundButton,
            _set_tooltip,
            "[Experimentell] Live-Ton während der Videowiedergabe umschalten",
        ),
        (window.addMarkerButton, _set_tooltip, "Marker hinzufügen"),
        (window.removeMarkerButton, _set_tooltip, "Marker entfernen"),
        (window.previousMarkerButton, _set_tooltip, "Zum vorherigen Marker springen"),
        (window.nextMarkerButton, _set_tooltip, "Zum nächsten Marker springen"),
        (window.viewFullScreenButton, _set_tooltip, "Vollbild anzeigen (F11)"),
        (window.findTargetFacesButton, _set_text, "Gesichter finden"),
        (window.clearTargetFacesButton, _set_text, "Gesichter leeren"),
        (window.swapfacesButton, _set_text, "Gesichter tauschen"),
        (window.editFacesButton, _set_text, "Gesichter bearbeiten"),
        (window.inputEmbeddingsList, _set_tooltip, "Gespeicherte Einbettung"),
        (window.saveImageButton, _set_text, "Bild speichern"),
        (window.inputEmbeddingsSearchBox, _set_placeholder, "Einbettungen suchen"),
        (window.openEditorButton, _set_tooltip, "Einbettungs-Editor öffnen"),
        (window.openEditorButton, _set_text, "Einbettungs-Editor"),
        (window.openEmbeddingButton, _set_tooltip, "Einbettungsdatei öffnen"),
        (window.saveEmbeddingButton, _set_tooltip, "Einbettung speichern"),
        (window.saveEmbeddingAsButton, _set_tooltip, "Einbettung speichern unter"),
        (window.input_Target_DockWidget, _set_title, "Zielvideos"),
        (window.groupBox_TargetVideos_Select, _set_title, "Zielvideos/-bilder"),
        (window.labelTargetVideosPath, _set_text, "Pfad für Videos/Bilder auswählen"),
        (window.buttonTargetVideosPath, _set_tooltip, "Ordner mit Zielmedien auswählen"),
        (window.targetVideosSearchBox, _set_placeholder, "Videos/Bilder suchen"),
        (window.filterImagesCheckBox, _set_tooltip, "Bilder einbeziehen"),
        (window.filterVideosCheckBox, _set_tooltip, "Videos einbeziehen"),
        (window.filterWebcamsCheckBox, _set_tooltip, "Webcams einbeziehen"),
        (window.input_Faces_DockWidget, _set_title, "Quellgesichter"),
        (window.groupBox_InputFaces_Select, _set_title, "Quellgesichter"),
        (window.labelInputFacesPath, _set_text, "Pfad für Gesichterbilder auswählen"),
        (window.buttonInputFacesPath, _set_tooltip, "Ordner mit Quellgesichtern auswählen"),
        (window.inputFacesSearchBox, _set_placeholder, "Gesichter suchen"),
        (window.jobManagerDockWidget, _set_title, "Job-Verwaltung"),
        (window.addJobButton, _set_text, "Job speichern"),
        (window.loadJobButton, _set_text, "Job laden"),
        (window.deleteJobButton, _set_text, "Job löschen"),
        (window.refreshJobListButton, _set_text, "Jobliste aktualisieren"),
        (window.buttonProcessAll, _set_text, "Alle verarbeiten"),
        (window.buttonProcessSelected, _set_text, "Auswahl verarbeiten"),
        (window.controlOptionsDockWidget, _set_title, "Steuerungsoptionen"),
        (window.label, _set_text, "Ausgabeordner"),
        (window.outputFolderButton, _set_text, "Ordner wählen"),
        (window.outputOpenButton, _set_text, "Ordner öffnen"),
        (window.labelp, _set_text, "Voreinstellungen"),
        (window.applyPresetButton, _set_text, "Anwenden"),
        (window.savePresetButton, _set_text, "Aktuelle Einstellungen als Preset speichern"),
        (window.controlPresetButton, _set_text, "Einstellungen anwenden"),
        (window.clearMemoryButton, _set_text, "VRAM leeren"),
        (window.menuFile, _set_title, "Datei"),
        (window.menuEdit, _set_title, "Bearbeiten"),
        (window.menuView, _set_title, "Ansicht"),
        (window.menuHelp, _set_title, "Hilfe"),
    )

    for widget, setter, value in text_updates:
        setter(widget, value)

    window.tabWidget.setTabText(
        window.tabWidget.indexOf(window.face_swap_tab), "Gesichtstausch"
    )
    window.tabWidget.setTabText(
        window.tabWidget.indexOf(window.face_editor_tab), "Gesichtseditor"
    )
    window.tabWidget.setTabText(
        window.tabWidget.indexOf(window.common_tab), "Restaurierung"
    )
    window.tabWidget.setTabText(
        window.tabWidget.indexOf(window.denoiser_tab), "Entrauscher"
    )
    window.tabWidget.setTabText(
        window.tabWidget.indexOf(window.settings_tab), "Einstellungen"
    )
    window.tabWidget.setTabText(
        window.tabWidget.indexOf(window.preset_tab), "Voreinstellungen"
    )
