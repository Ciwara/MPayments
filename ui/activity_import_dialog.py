#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from Common.ui.common import Button, FormLabel, FWidget, LineEdit
from activity_import import (
    ActivityImportError,
    import_into_activity,
    preview_source,
    resolve_app_database,
    resolve_sqlite_file,
)
from configuration import Config
from models import Activity

logger = logging.getLogger(__name__)


class ImportIntoActivityDialog(QDialog, FWidget):
    """Importe une sauvegarde .db dans une activité (sans remplacer toute la base)."""

    def __init__(self, parent=None, *args, **kwargs):
        FWidget.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self._src_path = None

        self.setWindowTitle("Importer une sauvegarde dans une activité")
        self.setMinimumSize(520, 360)
        self.setModal(True)

        vbox = QVBoxLayout()
        vbox.setSpacing(14)
        vbox.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Importer vers une activité")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        vbox.addWidget(title)

        hint = QLabel(
            "Les comptes et paiements de la sauvegarde sont ajoutés à l'activité "
            "choisie. Les utilisateurs et les autres activités ne sont pas modifiés."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid);")
        vbox.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(12)

        file_row = QHBoxLayout()
        self.file_field = LineEdit()
        self.file_field.setReadOnly(True)
        self.file_field.setPlaceholderText("Sélectionnez un fichier .db de sauvegarde…")
        browse_btt = Button("Parcourir…")
        browse_btt.clicked.connect(self._browse)
        file_row.addWidget(self.file_field, 1)
        file_row.addWidget(browse_btt)
        form.addRow(FormLabel("Sauvegarde :"), file_row)

        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet("color: palette(mid);")
        form.addRow("", self.preview_label)

        self.activity_combo = QComboBox()
        self.activity_combo.setEditable(False)
        self._reload_activities()
        form.addRow(FormLabel("Activité cible :"), self.activity_combo)

        self.new_name_field = LineEdit()
        self.new_name_field.setPlaceholderText("Ex. Depenses, Magasin 2…")
        self.new_name_field.setEnabled(False)
        form.addRow(FormLabel("Nom (si nouvelle) :"), self.new_name_field)

        self.activity_combo.currentIndexChanged.connect(self._on_activity_changed)

        self.replace_check = QCheckBox(
            "Remplacer les données déjà présentes dans cette activité"
        )
        self.replace_check.setChecked(True)
        form.addRow("", self.replace_check)

        vbox.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btt = Button("Annuler")
        cancel_btt.clicked.connect(self.reject)
        self.import_btt = Button("Importer")
        self.import_btt.clicked.connect(self._do_import)
        btn_row.addWidget(cancel_btt)
        btn_row.addWidget(self.import_btt)
        vbox.addLayout(btn_row)

        self.setLayout(vbox)
        self._on_activity_changed()

    def _reload_activities(self):
        self.activity_combo.clear()
        current_id = None
        try:
            current = Activity.get_current()
            current_id = getattr(current, "id", None)
        except Exception:
            pass

        for act in Activity.active_query():
            label = act.name
            if current_id and act.id == current_id:
                label = f"{act.name} (courante)"
            self.activity_combo.addItem(label, act.name)

        self.activity_combo.addItem("➕ Nouvelle activité…", "__new__")

    def _on_activity_changed(self):
        is_new = self.activity_combo.currentData() == "__new__"
        self.new_name_field.setEnabled(is_new)
        if is_new:
            self.new_name_field.setFocus()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir une sauvegarde",
            str(Path.home() / "Downloads"),
            "Bases SQLite (*.db);;Tous les fichiers (*)",
        )
        if not path:
            return
        try:
            src = resolve_sqlite_file(path, role="Sauvegarde")
            info = preview_source(src)
        except ActivityImportError as exc:
            QMessageBox.warning(self, "Fichier invalide", str(exc))
            return
        self._src_path = str(src)
        self.file_field.setText(self._src_path)
        self.preview_label.setText(
            f"{info['accounts']} compte(s), {info['payments']} paiement(s) dans la sauvegarde"
        )

    def _target_activity_name(self) -> str:
        data = self.activity_combo.currentData()
        if data == "__new__":
            return str(self.new_name_field.text()).strip()
        return str(data or "").strip()

    def _do_import(self):
        if not self._src_path:
            QMessageBox.warning(
                self, "Sauvegarde manquante", "Sélectionnez d'abord un fichier .db."
            )
            return

        activity_name = self._target_activity_name()
        if not activity_name:
            QMessageBox.warning(
                self, "Activité manquante", "Indiquez le nom de l'activité cible."
            )
            return

        replace = self.replace_check.isChecked()
        if replace:
            reply = QMessageBox.question(
                self,
                "Confirmer l'import",
                f"Importer la sauvegarde dans « {activity_name} » ?\n\n"
                "Les comptes et paiements déjà présents dans cette activité "
                "seront remplacés.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            dest = resolve_app_database(Config.DB_PATH)
        except ActivityImportError as exc:
            QMessageBox.critical(self, "Échec de l'import", str(exc))
            return
        self.import_btt.setEnabled(False)
        try:
            result = import_into_activity(
                self._src_path,
                dest,
                activity_name=activity_name,
                replace=replace,
            )
        except ActivityImportError as exc:
            logger.error("Import activité échoué: %s", exc)
            QMessageBox.critical(self, "Échec de l'import", str(exc))
            self.import_btt.setEnabled(True)
            return
        except Exception as exc:
            logger.exception("Import activité")
            QMessageBox.critical(self, "Échec de l'import", str(exc))
            self.import_btt.setEnabled(True)
            return

        # Basculer sur l'activité importée et rafraîchir l'UI
        try:
            activity = Activity.get(
                Activity.name == result["activity_name"],
                Activity.deleted == False,
            )
            Activity.set_current(activity)
        except Exception as exc:
            logger.warning("Impossible d'activer l'activité importée: %s", exc)

        if hasattr(self.parent, "reload_current_view"):
            try:
                self.parent.reload_current_view()
            except Exception:
                pass
        if hasattr(self.parent, "sync_activity_ui"):
            try:
                self.parent.sync_activity_ui()
            except Exception:
                pass

        msg = (
            f"Import terminé dans « {result['activity_name']} ».\n\n"
            f"• {result['accounts']} compte(s)\n"
            f"• {result['payments']} paiement(s)"
        )
        if result.get("created"):
            msg += "\n• Activité créée"
        if result.get("cleared"):
            msg += f"\n• {result['cleared']} ancien(s) compte(s) remplacé(s)"

        if hasattr(self.parent, "Notify"):
            self.parent.Notify(msg, "success")
        else:
            QMessageBox.information(self, "Import réussi", msg)

        self.accept()
