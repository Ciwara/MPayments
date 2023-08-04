#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad
from __future__ import absolute_import, division, print_function, unicode_literals

from Common.ui.common import FMainWindow
from configuration import Config
from PyQt4.QtGui import QIcon
from ui.debt_manager import DebtsViewWidget

# from ui.menutoolbar import MenuToolBar
from ui.menubar import MenuBar


class MainWindow(FMainWindow):
    def __init__(self):
        FMainWindow.__init__(self)

        self.setWindowIcon(QIcon.fromTheme("logo", QIcon("{}".format(Config.APP_LOGO))))
        self.menubar = MenuBar(self)
        self.setMenuBar(self.menubar)
        # self.toolbar = MenuToolBar(self)
        # self.addToolBar(Qt.LeftToolBarArea, self.toolbar)

        self.page = DebtsViewWidget

        self.change_context(self.page)

    def page_width(self):
        return self.width() - 100

    def exit(self):
        self.logout()
        self.close()
