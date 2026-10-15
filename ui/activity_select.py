#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
)

from Common.ui.common import Button, FWidget
from configuration import Config
from models import Activity
from ui.activity_edit_add import EditOrAddActivityDialog

logger = logging.getLogger(__name__)


class SelectActivityWidget(FWidget):
    """Page de choix d'activité (après login, ou changement pendant la session)."""

    def __init__(self, parent=None, required=False, return_to=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.parent = parent
        self.required = required
        self.return_to = return_to

        try:
            self.parentWidget().setWindowTitle(f"{Config.APP_NAME} — Choisir une activité")
        except Exception:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)

        card = QFrame()
        card.setObjectName("activity_select_card")
        card.setMaximumWidth(640)
        card.setStyleSheet(
            """
            QFrame#activity_select_card {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 12px;
            }
            """
        )
        card_box = QVBoxLayout(card)
        card_box.setSpacing(14)
        card_box.setContentsMargins(28, 28, 28, 24)

        title = QLabel("Quelle activité souhaitez-vous utiliser ?")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setWordWrap(True)
        card_box.addWidget(title)

        hint = QLabel(
            "Chaque activité a ses propres comptes et paiements. "
            "Choisissez-en une pour continuer."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid);")
        card_box.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(280)
        self.list_widget.setWordWrap(True)
        self.list_widget.setStyleSheet(
            """
            QListWidget {
                border: 1px solid palette(mid);
                border-radius: 8px;
                padding: 4px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
            """
        )
        self.list_widget.itemDoubleClicked.connect(self._accept_selection)
        card_box.addWidget(self.list_widget, 1)

        btn_row = QHBoxLayout()
        self.new_btt = Button("➕ Nouvelle activité")
        self.new_btt.clicked.connect(self._create_activity)
        btn_row.addWidget(self.new_btt)

        self.edit_btt = Button("Modifier")
        self.edit_btt.clicked.connect(self._edit_activity)
        btn_row.addWidget(self.edit_btt)
        btn_row.addStretch()

        if not required:
            back_btt = Button("Retour")
            back_btt.clicked.connect(self._go_back)
            btn_row.addWidget(back_btt)

        self.ok_btt = Button("Continuer")
        self.ok_btt.clicked.connect(self._accept_selection)
        btn_row.addWidget(self.ok_btt)
        card_box.addLayout(btn_row)

        holder = QHBoxLayout()
        holder.addStretch()
        holder.addWidget(card, 1)
        holder.addStretch()
        root.addStretch()
        root.addLayout(holder)
        root.addStretch()

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
            label = act.name
            if current and act.id == current.id:
                label = f"{act.name}   ·   courante"
            if act.description:
                label = f"{label}\n{act.description}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, act.id)
            if act.description:
                item.setToolTip(act.description)
            self.list_widget.addItem(item)
            if current and act.id == current.id:
                self.list_widget.setCurrentItem(item)

        if self.list_widget.currentItem() is None and self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _select_saved(self, activity):
        self.refresh_list()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == activity.id:
                self.list_widget.setCurrentItem(item)
                break
        host = self.parentWidget()
        if host is not None and hasattr(host, "sync_activity_ui"):
            try:
                current = Activity.get_current()
            except Exception:
                current = None
            if current and current.id == activity.id:
                host.sync_activity_ui()

    def _open_editor(self, activity):
        dlg = EditOrAddActivityDialog(
            parent=self.parent or self,
            activity=activity,
            on_saved=self._select_saved,
        )
        dlg.setModal(True)
        dlg.exec()

    def _create_activity(self):
        self._open_editor(None)

    def _edit_activity(self):
        activity = self._selected_activity(
            "Veuillez sélectionner l'activité à modifier."
        )
        if activity is None:
            return
        self._open_editor(activity)

    def _selected_activity(self, empty_message="Veuillez sélectionner une activité pour continuer."):
        item = self.list_widget.currentItem()
        if item is None:
            QMessageBox.warning(self, "Activité requise", empty_message)
            return None
        try:
            return Activity.get_by_id(item.data(Qt.ItemDataRole.UserRole))
        except Activity.DoesNotExist:
            QMessageBox.warning(self, "Activité", "Activité introuvable.")
            self.refresh_list()
            return None

    def _accept_selection(self, *_args):
        activity = self._selected_activity()
        if activity is None:
            return
        try:
            Activity.set_current(activity)
        except Exception as exc:
            logger.error("Impossible de sélectionner l'activité: %s", exc)
            QMessageBox.warning(self, "Activité", "Impossible de sélectionner cette activité.")
            return

        host = self.parentWidget()
        if host is not None and hasattr(host, "on_activity_selected"):
            host.on_activity_selected(activity, return_to=self.return_to)

    def _go_back(self):
        if self.required:
            return
        host = self.parentWidget()
        if host is not None and hasattr(host, "leave_activity_page"):
            host.leave_activity_page(return_to=self.return_to)
