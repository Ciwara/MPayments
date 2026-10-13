#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

import logging

import peewee
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QFormLayout, QTextEdit, QVBoxLayout

from Common.models import Organization, Owner
from Common.ui.common import Button, FormLabel, FWidget, LineEdit
from Common.ui.util import check_is_empty, field_error
from models import Activity

logger = logging.getLogger(__name__)


class EditOrAddActivityDialog(QDialog, FWidget):
    """Création / modification d'une activité (compartiment comptes + paiements)."""

    def __init__(self, parent, activity=None, on_saved=None, *args, **kwargs):
        FWidget.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.on_saved = on_saved
        self.activity = activity

        if self.activity and getattr(self.activity, "id", None):
            self.new = False
            self.title = f"Modifier l'activité — {self.activity.name}"
        else:
            self.new = True
            self.title = "Nouvelle activité"
            self.activity = Activity()

        self.setWindowTitle(self.title)
        self.setMinimumSize(420, 280)
        self.setMaximumSize(520, 420)

        vbox = QVBoxLayout()
        vbox.setSpacing(16)
        vbox.setContentsMargins(24, 24, 24, 24)

        title_label = FormLabel(self.title)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        vbox.addWidget(title_label)

        self.name_field = LineEdit(getattr(self.activity, "name", None) or "")
        self.name_field.setPlaceholderText("Ex. Magasin centre, Boutique 2…")
        self.description_field = QTextEdit(getattr(self.activity, "description", None) or "")
        self.description_field.setPlaceholderText("Description optionnelle")
        self.description_field.setMaximumHeight(100)

        formbox = QFormLayout()
        formbox.setSpacing(12)
        formbox.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        formbox.addRow(FormLabel("Nom : *"), self.name_field)
        formbox.addRow(FormLabel("Description :"), self.description_field)

        save_btt = Button("Enregistrer")
        save_btt.clicked.connect(self.save_edit)
        formbox.addRow("", save_btt)

        vbox.addLayout(formbox)
        vbox.addStretch()
        self.setLayout(vbox)

    def save_edit(self):
        if check_is_empty(self.name_field):
            if hasattr(self.parent, "Notify"):
                self.parent.Notify("Le nom de l'activité est obligatoire", "error")
            return

        name = str(self.name_field.text()).strip()
        exclude_id = None if self.new else self.activity.id
        if Activity.name_exists(name, exclude_id=exclude_id):
            field_error(self.name_field, "Une activité porte déjà ce nom.")
            return

        self.activity.name = name
        self.activity.description = str(self.description_field.toPlainText()).strip() or None

        if self.new:
            try:
                self.activity.organization = Organization.get_by_id(1)
            except Exception:
                try:
                    self.activity.organization = Organization.select().first()
                except Exception:
                    self.activity.organization = None
            try:
                self.activity.owner = Owner.get(Owner.is_identified == True)
            except Exception:
                try:
                    self.activity.owner = Owner.select().first()
                except Exception:
                    self.activity.owner = None
            self.activity.deleted = False
            # Première activité → courante ; sinon on laisse le choix à l'utilisateur
            if Activity.active_query().count() == 0:
                self.activity.is_current = True

        try:
            self.activity.save()
            if self.new and not Activity.select().where(
                Activity.is_current == True, Activity.deleted == False
            ).exists():
                Activity.set_current(self.activity)

            self.close()
            if callable(self.on_saved):
                self.on_saved(self.activity)
            if hasattr(self.parent, "Notify"):
                self.parent.Notify(
                    f"Activité « {self.activity.name} » enregistrée", "success"
                )
        except peewee.IntegrityError:
            field_error(self.name_field, "Ce nom d'activité existe déjà.")
        except Exception as exc:
            logger.error(f"Erreur sauvegarde activité: {exc}")
            if hasattr(self.parent, "Notify"):
                self.parent.Notify(f"Erreur : {exc}", "error")
