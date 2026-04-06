#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

from Common.models import Settings
from Common.ui.common import FMainWindow
from configuration import Config
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from ui.dashboard import DashboardWidget
from ui.menubar import MenuBar
from ui.menutoolbar import MenuToolBar


class MainWindow(FMainWindow):
    def __init__(self):
        FMainWindow.__init__(self)
        
        # Configuration du titre de la fenêtre principale
        self.title = "Fenêtre principale"
        self.setWindowTitle(f"{Config.APP_NAME} - {self.title}")

        # Configuration de l'icône de la fenêtre
        self.setWindowIcon(QIcon.fromTheme("logo", QIcon("{}".format(Config.APP_LOGO))))
        
        # Initialisation de la barre de menu
        self.menubar = MenuBar(self)
        self.setMenuBar(self.menubar)
        
        # Configuration de la barre d'outils selon les paramètres
        self._setup_toolbar()

        # Appliquer le thème sauvegardé (persistant)
        self.apply_saved_theme()

        # Changement vers le contexte initial
        self.change_context(DashboardWidget)

    def apply_saved_theme(self):
        """Applique le thème (Settings.theme) au démarrage."""
        try:
            from Common.ui.theme import apply_theme, THEME_NAMES

            sttg = Settings.get_by_id(1)
            theme_name = getattr(sttg, "theme", "system") or "system"
            if theme_name not in THEME_NAMES:
                # Compatibilité avec d'anciens thèmes ("default", etc.)
                theme_name = "system" if theme_name in ("default", "") else "light"

            app = QApplication.instance()
            apply_theme(app, theme_name, save_to_settings=False)
        except Exception:
            # Ne pas bloquer le démarrage si la DB n'est pas prête
            return

    def set_theme(self, theme_name):
        """Appelé par le menu Common pour changer le thème + sauvegarder."""
        try:
            from Common.ui.theme import apply_theme

            app = QApplication.instance()
            apply_theme(app, theme_name, save_to_settings=True)
        except Exception:
            return

    def _setup_toolbar(self):
        """Configure la barre d'outils selon les paramètres utilisateur"""
        try:
            sttg = Settings().get(id=1)
            if sttg.toolbar:
                self.toolbar = MenuToolBar(self)
                toolbar_positions = {
                    sttg.LEFT: Qt.ToolBarArea.LeftToolBarArea,
                    sttg.RIGHT: Qt.ToolBarArea.RightToolBarArea,
                    sttg.TOP: Qt.ToolBarArea.TopToolBarArea,
                    sttg.BOTTOM: Qt.ToolBarArea.BottomToolBarArea,
                }
                position = toolbar_positions.get(sttg.toolbar_position, Qt.ToolBarArea.TopToolBarArea)
                self.addToolBar(position, self.toolbar)
        except Exception as e:
            # En cas d'erreur, on continue sans toolbar
            print(f"Erreur lors de la configuration de la toolbar: {e}")

    def page_width(self):
        """Retourne la largeur de la page avec une marge"""
        return self.width() - 100

    def exit(self):
        """Méthode de sortie propre de l'application"""
        self.logout()
        self.close()

    def on_login_success(self):
        """Appelé après une connexion réussie"""
        print('Login successful')
        # Initialisation de la barre de menu
        self.menubar = MenuBar(self)
        self.setMenuBar(self.menubar)
        
        # Configuration de la barre d'outils selon les paramètres
        self._setup_toolbar()
        self.apply_saved_theme()
