#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad
from __future__ import unicode_literals, absolute_import, division, print_function

import logging
import atexit
import sys
import os
from typing import List, Optional

# Ajout du répertoire parent au chemin Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtGui import QIcon, QFont, QFontDatabase
from PyQt5.QtCore import Qt, QThread, QTimer

from Common.ui.common import FMainWindow
from Common.models import Settings
from configuration import Config
from models import database, init_database
from database import Setup

from ui.menutoolbar import MenuToolBar
from ui.menubar import MenuBar
from ui.dashboard import DashboardWidget

# Configuration du logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gestionnaire de la base de données"""
    
    @staticmethod
    def initialize():
        """Initialise la base de données et crée les tables si nécessaire"""
        try:
            logger.debug("Initialisation de la base de données")
            logger.debug(f"Chemin de la base de données: {Config.DB_PATH}")
            
            # Initialisation de la base de données
            db = init_database(Config.DB_PATH)
            if db is None:
                raise Exception("Échec de l'initialisation de la base de données")
            
            # Connexion à la base de données
            if db.is_closed():
                db.connect()
            
            # Création des tables
            setup = Setup()
            db.create_tables(setup.LIST_CREAT, safe=True)
            logger.debug("Base de données initialisée avec succès")
            
            # Créer un Owner par défaut si nécessaire
            setup.create_default_owner()
            logger.debug("Vérification/création de l'Owner par défaut terminée")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {str(e)}")
            raise
        finally:
            if not db.is_closed():
                db.close()

    @staticmethod
    def close():
        """Ferme la connexion à la base de données"""
        try:
            from database import database
            if database is not None and not database.is_closed():
                database.close()
                logger.debug("Base de données fermée")
        except Exception as e:
            logger.warning(f"Erreur lors de la fermeture de la base: {e}")
            # Ne pas lever d'exception ici pour éviter de bloquer la fermeture


class ThreadManager:
    """Gestionnaire des threads"""
    
    def __init__(self):
        self._threads: List[QThread] = []
        self._check_timer: Optional[QTimer] = None
    
    def start_monitoring(self, parent):
        """Démarre la surveillance des threads"""
        self._check_timer = QTimer(parent)
        self._check_timer.timeout.connect(self._check_threads)
        self._check_timer.start(1000)  # Vérification toutes les secondes
    
    def stop_monitoring(self):
        """Arrête la surveillance des threads"""
        if self._check_timer:
            self._check_timer.stop()
            self._check_timer = None
    
    def _check_threads(self):
        """Vérifie l'état des threads et nettoie ceux qui sont terminés"""
        for thread in self._threads[:]:
            if not thread.isRunning():
                logger.debug(f"Thread terminé détecté: {thread}")
                self.remove_thread(thread)
    
    def add_thread(self, thread: QThread):
        """Ajoute un thread à la liste des threads à gérer"""
        if thread not in self._threads:
            self._threads.append(thread)
            logger.debug(f"Thread ajouté: {thread}")
    
    def remove_thread(self, thread: QThread):
        """Retire un thread de la liste"""
        if thread in self._threads:
            self._threads.remove(thread)
            logger.debug(f"Thread retiré: {thread}")
    
    def cleanup(self):
        """Nettoie tous les threads"""
        for thread in self._threads[:]:
            if thread.isRunning():
                logger.debug(f"Arrêt forcé du thread: {thread}")
                thread.quit()
                thread.wait(1000)  # Attente d'une seconde maximum
                if thread.isRunning():
                    thread.terminate()  # Force l'arrêt si nécessaire
            self.remove_thread(thread)


class MainWindow(FMainWindow):
    def __init__(self):
        logger.debug("Initialisation de MainWindow")
        FMainWindow.__init__(self)

        # Initialisation de la base de données
        DatabaseManager.initialize()

        self.setWindowIcon(QIcon("{img_media}icon.png".format(img_media=Config.img_media)))
        
        # Configuration optimisée des polices
        font_db = QFontDatabase()
        system_fonts = font_db.families()
        preferred_fonts = ["Arial", "Helvetica", "Sans Serif", "DejaVu Sans"]
        
        # Sélection de la première police disponible
        selected_font = next((font for font in preferred_fonts if font in system_fonts), "Sans Serif")
        default_font = QFont(selected_font, 10)
        default_font.setStyleHint(QFont.SansSerif)
        self.setFont(default_font)
        logger.debug(f"Police sélectionnée: {selected_font}")
        
        self.setWindowTitle(Config.APP_NAME)
        self.menubar = MenuBar(self)
        self.setMenuBar(self.menubar)
        self.settings = Settings.init_settings()
        logger.debug(f"Paramètres de la barre d'outils: {self.settings.toolbar}")
        
        if self.settings.toolbar:
            self.toolbar = MenuToolBar(self)
            ptn = {
                self.settings.LEFT: Qt.LeftToolBarArea,
                self.settings.RIGHT: Qt.RightToolBarArea,
                self.settings.TOP: Qt.TopToolBarArea,
                self.settings.BOTTOM: Qt.BottomToolBarArea,
            }
            # Utiliser TOP comme position par défaut si toolbar_position est None ou invalide
            toolbar_area = ptn.get(self.settings.toolbar_position, Qt.TopToolBarArea)
            self.addToolBar(toolbar_area, self.toolbar)

        self.page = DashboardWidget
        logger.debug("Changement de contexte vers DashboardWidget")
        self.change_context(self.page)

        # Initialisation du gestionnaire de threads
        self.thread_manager = ThreadManager()
        self.thread_manager.start_monitoring(self)
        
        # Enregistrement de la fonction de nettoyage
        atexit.register(self.cleanup)

    def page_width(self):
        width = self.width() - 100
        logger.debug(f"Largeur de la page calculée: {width}")
        return width

    def cleanup(self):
        """Nettoie les ressources avant la fermeture de l'application"""
        logger.debug("Début du nettoyage des ressources")
        
        # Arrêt de la surveillance des threads
        self.thread_manager.stop_monitoring()
        
        # Nettoyage des threads
        self.thread_manager.cleanup()
        
        # Fermeture de la base de données
        DatabaseManager.close()
        
        logger.debug("Nettoyage des ressources terminé")

    def exit(self):
        """Ferme proprement l'application"""
        logger.debug("Début de la procédure de sortie")
        self.cleanup()
        self.logout()
        logger.debug("Fermeture de la fenêtre principale")
        self.close()
        logger.debug("Application fermée avec succès")

    def add_thread(self, thread: QThread):
        """Ajoute un thread à la liste des threads à gérer"""
        self.thread_manager.add_thread(thread)

    def remove_thread(self, thread: QThread):
        """Retire un thread de la liste"""
        self.thread_manager.remove_thread(thread)

    def closeEvent(self, event):
        """Gère l'événement de fermeture de la fenêtre"""
        logger.debug("Événement de fermeture détecté")
        self.cleanup()
        event.accept()
