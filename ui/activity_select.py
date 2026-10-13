#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
)

from Common.ui.common import Button, FWidget
from models import Activity
from ui.activity_edit_add import EditOrAddActivityDialog

logger = logging.getLogger(__name__)


class SelectActivityDialog(QDialog, FWidget):
    """Choix d'activité après login, ou changement pendant la session."""

    def __init__(self, parent=None, required=True, *args, **kwargs):
        FWidget.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.required = required
        self.selected_activity = None

        self.setWindowTitle("Choisir une activité")
        self.setMinimumSize(440, 360)
        self.setModal(True)
        if required:
            # Empêche la fermeture sans choix (croix / Échap)
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        vbox = QVBoxLayout()
        vbox.setSpacing(14)
        vbox.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Quelle activité souhaitez-vous utiliser ?")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        vbox.addWidget(title)

        hint = QLabel(
            "Chaque activité a ses propres comptes et paiements. "
            "Pour en changer plus tard : menu Activités → Changer d'activité…"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid);")
        vbox.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._accept_selection)
        vbox.addWidget(self.list_widget, 1)

        btn_row = QHBoxLayout()
        self.new_btt = Button("➕ Nouvelle activité")
        self.new_btt.clicked.connect(self._create_activity)
        btn_row.addWidget(self.new_btt)
        btn_row.addStretch()

        if not required:
            cancel_btt = Button("Annuler")
            cancel_btt.clicked.connect(self.reject)
            btn_row.addWidget(cancel_btt)

        self.ok_btt = Button("Continuer")
        self.ok_btt.clicked.connect(self._accept_selection)
        btn_row.addWidget(self.ok_btt)
        vbox.addLayout(btn_row)

        self.setLayout(vbox)
        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        current = None
        try:
            current = Activity.get_current()
        except Exception:
            current = None

        activities = list(Activity.active_query())
        if not activities:
            Activity.ensure_default()
            activities = list(Activity.active_query())

        for act in activities:
            item = QListWidgetItem(act.name)
            item.setData(Qt.ItemDataRole.UserRole, act.id)
            if act.description:
                item.setToolTip(act.description)
            self.list_widget.addItem(item)
            if current and act.id == current.id:
                self.list_widget.setCurrentItem(item)

        if self.list_widget.currentItem() is None and self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _create_activity(self):
        def _after_save(activity):
            self.refresh_list()
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == activity.id:
                    self.list_widget.setCurrentItem(item)
                    break

        dlg = EditOrAddActivityDialog(
            parent=self.parent or self,
            activity=None,
            on_saved=_after_save,
        )
        dlg.setModal(True)
        dlg.exec()

    def _accept_selection(self, *_args):
        item = self.list_widget.currentItem()
        if item is None:
            QMessageBox.warning(
                self,
                "Activité requise",
                "Veuillez sélectionner une activité pour continuer.",
            )
            return
        try:
            activity = Activity.get_by_id(item.data(Qt.ItemDataRole.UserRole))
        except Activity.DoesNotExist:
            QMessageBox.warning(self, "Activité", "Activité introuvable.")
            self.refresh_list()
            return

        Activity.set_current(activity)
        self.selected_activity = activity
        self.accept()

    def reject(self):
        if self.required:
            return
        super().reject()

    def closeEvent(self, event):
        if self.required and self.selected_activity is None:
            event.ignore()
            return
        super().closeEvent(event)
