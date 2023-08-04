# !/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: fad

from __future__ import unicode_literals, absolute_import, division, print_function

from PyQt4.QtGui import QIcon, QToolBar, QCursor
from PyQt4.QtCore import Qt, QSize

from Common.ui.common import FWidget
from Common.ui.cmenutoolbar import FMenuToolBar
from configuration import Config


class MenuToolBar(FMenuToolBar, FWidget):
    def __init__(self, parent=None, *args, **kwargs):
        FMenuToolBar.__init__(self, parent, *args, **kwargs)

        from ui.statistics import StatisticsViewWidget
        from ui.trash_cpt import DebtsTrashViewWidget
        from ui.debt_manager import DebtsViewWidget

        menu = [
            {
                "name": u"Statistiques",
                "icon": 'state',
                "admin": False,
                "shortcut": "Ctrl+S",
                "goto": StatisticsViewWidget,
            },
            {
                "name": u"G. comptes",
                "icon": 'compte',
                "admin": False,
                "shortcut": "Ctrl+V",
                "goto": DebtsViewWidget,
            },
            {
                "name": u"Poubelle",
                "icon": 'del',
                "del": False,
                "shortcut": "Ctrl+P",
                "goto": DebtsTrashViewWidget,
            },
        ]

        for m in menu:
            self.addSeparator()
            self.addAction(
                QIcon("{}{}.png".format(Config.img_media, m.get('icon'))),
                m.get('name'),
                lambda m=m: self.goto(m.get('goto')),
            )
