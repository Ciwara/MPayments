# !/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: fad

from __future__ import unicode_literals, absolute_import, division, print_function

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QLabel, QSizePolicy, QWidget

from Common.ui.common import FWidget
from Common.ui.cmenutoolbar import FMenuToolBar
from configuration import Config
from models import Activity


class MenuToolBar(FMenuToolBar, FWidget):
    def __init__(self, parent=None, *args, **kwargs):
        FMenuToolBar.__init__(self, parent, *args, **kwargs)

        from ui.trash_cpt import DebtsTrashViewWidget
        from ui.debt_manager import DebtsViewWidget
        from ui.dashboard import DashboardWidget

        menu = [
            {
                "name": "Tableau de Bord",
                "icon": "state",
                "admin": False,
                "shortcut": "Ctrl+D",
                "goto": DashboardWidget,
            },
            {
                "name": "G. comptes",
                "icon": "compte",
                "admin": False,
                "shortcut": "Ctrl+V",
                "goto": DebtsViewWidget,
            },
            {
                "name": "Poubelle",
                "icon": "del",
                "del": False,
                "shortcut": "Ctrl+P",
                "goto": DebtsTrashViewWidget,
            },
        ]

        for m in menu:
            self.addSeparator()
            self.addAction(
                QIcon("{}{}.png".format(Config.img_media, m.get("icon"))),
                m.get("name"),
                lambda m=m: self.goto(m.get("goto")),
            )

        # Afficher activité courante + version à droite (lecture seule)
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

        self.activity_label = QLabel("", self)
        self.activity_label.setStyleSheet(
            "color: palette(window-text); font-size: 11px; font-weight: 600; padding: 0 8px;"
        )
        self.activity_label.setToolTip(
            "Activité courante — pour changer : menu Activités → Changer d'activité"
        )
        self.addWidget(self.activity_label)

        self.app_version_label = QLabel(f"v{Config.APP_VERSION}", self)
        self.app_version_label.setStyleSheet(
            "color: palette(mid); font-size: 10px; padding: 0 6px;"
        )
        self.addWidget(self.app_version_label)

        self.refresh_activity_label()

    def refresh_activity_label(self):
        """Met à jour l'affichage de l'activité courante (sans permettre le changement)."""
        try:
            activity = Activity.get_current()
            name = activity.name if activity else "—"
        except Exception:
            name = "—"
        self.activity_label.setText(f"Activité : {name}")
