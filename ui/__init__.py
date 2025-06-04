#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

import logging

from .mainwindow import MainWindow
from .debt_manager import DebtsViewWidget
from .menubar import MenuBar
from .menutoolbar import MenuToolBar

__all__ = ['MainWindow', 'DebtsViewWidget', 'MenuBar', 'MenuToolBar']

# Configuration du logger
logging.basicConfig(
    level=logging.DEBUG,  # Niveau du logger (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Format du message
    datefmt='%Y-%m-%d %H:%M:%S',  # Format de la date
)
logger = logging.getLogger(__name__)
