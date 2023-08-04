#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fadiga

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys

from Common.cmain import cmain
from Common.ui.style_qss import theme
from Common.ui.window import FWindow
from migrations import make_migrate
from PyQt4.QtGui import QApplication
from ui.mainwindow import MainWindow

sys.path.append(os.path.abspath("../"))


app = QApplication(sys.argv)


def main():
    window = MainWindow()
    window.setStyleSheet(theme)
    setattr(FWindow, "window", window)
    # window.show()
    window.showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":
    if cmain():
        sys.exit(app.exec_())
