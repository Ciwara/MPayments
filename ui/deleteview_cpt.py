#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad
from __future__ import unicode_literals, absolute_import, division, print_function

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QDialog, QLabel

from Common.ui.common import FWidget, Button


class DeleteViewWidget(QDialog, FWidget):
    """Confirmation avant mise en corbeille (soft-delete)."""

    def __init__(self, table_p, obj, parent, *args, **kwargs):
        QDialog.__init__(self, parent, *args, **kwargs)

        self.setWindowTitle("Mettre à la corbeille")
        self.setMinimumWidth(400)
        self.obj = obj
        self.table_p = table_p
        self.parent = parent

        title = QLabel("Mettre cet élément à la corbeille ?")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))

        detail = QLabel(obj.display_name())
        detail.setWordWrap(True)
        detail.setStyleSheet("color: palette(mid); padding: 8px 0;")

        hint = QLabel(
            "Vous pourrez le restaurer depuis le menu Poubelle. "
            "La suppression définitive se fait uniquement depuis la corbeille."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid); font-size: 12px;")

        delete_but = Button("Mettre à la corbeille")
        delete_but.clicked.connect(self.delete)
        cancel_but = Button("Annuler")
        cancel_but.clicked.connect(self.cancel)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel_but)
        buttons.addWidget(delete_but)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(20, 20, 20, 20)
        vbox.setSpacing(12)
        vbox.addWidget(title)
        vbox.addWidget(detail)
        vbox.addWidget(hint)
        vbox.addLayout(buttons)

    def cancel(self):
        self.close()
        return False

    def delete(self):
        self.obj.delete_data()
        self.cancel()
        self.table_p.refresh_()
        if hasattr(self.parent, "Notify"):
            self.parent.Notify("Élément mis à la corbeille", "success")
