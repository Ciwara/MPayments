#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: fad

from __future__ import absolute_import, division, print_function, unicode_literals

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from Common.ui.common import FWidget
from configuration import Config


class AboutDialog(QDialog, FWidget):
    def __init__(self, parent=None, *args, **kwargs):
        QDialog.__init__(self, parent, *args, **kwargs)

        self.setWindowTitle(f"À propos — {Config.APP_NAME}")
        try:
            self.setWindowIcon(QIcon(QPixmap("{}".format(Config.APP_LOGO))))
        except Exception:
            pass

        self.setMinimumWidth(420)

        title = QLabel(Config.APP_NAME)
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))

        version = QLabel(f"Version : {Config.APP_VERSION}")
        version.setStyleSheet("color: palette(window-text); font-size: 12px;")

        date = QLabel(f"Date : {Config.APP_DATE}")
        date.setStyleSheet("color: palette(mid); font-size: 11px;")

        desc = QLabel("Application de gestion des paiements et comptes.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: palette(window-text); font-size: 12px;")

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(date)
        layout.addSpacing(6)
        layout.addWidget(desc)
        layout.addStretch(1)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
