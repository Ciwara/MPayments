#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

from Common.models import Settings
from Common.ui.common import FMainWindow
from configuration import Config
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QToolBar
from ui.debt_manager import DebtsViewWidget
from ui.menubar import MenuBar
from ui.menutoolbar import MenuToolBar


class MainWindow(FMainWindow):
    def __init__(self):
        FMainWindow.__init__(self)

        self._activity_chosen_this_session = False
        self._prompting_activity = False

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
        self.change_context(DebtsViewWidget)

    def refresh_menu_after_login(self):
        """
        Appelé par `Common.cmain` après une connexion (ou auto-connexion).
        Reconstruit les menus/toolbar puis demande l'activité à utiliser.
        """
        try:
            self.menubar = MenuBar(self)
            self.setMenuBar(self.menubar)
        except Exception:
            pass

        try:
            self._setup_toolbar()
        except Exception:
            pass

        self.apply_saved_theme()
        # Après fermeture du dialogue de login (évite les modales imbriquées)
        QTimer.singleShot(0, self.prompt_activity_after_login)

    def prompt_activity_after_login(self):
        """Affiche la page de choix d'activité juste après le login (une fois par session)."""
        if self._activity_chosen_this_session or self._prompting_activity:
            return
        self._prompting_activity = True
        try:
            self.open_activity_page(required=True, return_to=DebtsViewWidget)
        finally:
            self._prompting_activity = False

    def open_activity_page(self, required=False, return_to=None):
        """Ouvre la page de choix d'activité dans la zone centrale."""
        from ui.activity_select import SelectActivityWidget

        if return_to is None:
            view = getattr(self, "view_widget", None)
            if isinstance(view, SelectActivityWidget):
                return_to = view.return_to or DebtsViewWidget
                required = required or view.required
            else:
                return_to = type(view) if view is not None else DebtsViewWidget
        self.change_context(
            SelectActivityWidget, required=required, return_to=return_to
        )

    def switch_activity(self):
        """Changer d'activité pendant la session (menu / raccourci)."""
        self.open_activity_page(required=False)

    def on_activity_selected(self, activity, return_to=None):
        """Activité choisie depuis la page : retour à l'écran précédent."""
        self._activity_chosen_this_session = True
        self._update_window_title_activity(activity)
        self._show_view(return_to)
        self.sync_activity_ui()
        name = getattr(activity, "name", "") or ""
        if name:
            self.Notify(f"Activité « {name} » sélectionnée", "success")

    def leave_activity_page(self, return_to=None):
        """Quitte la page d'activité sans changer la sélection."""
        self._show_view(return_to)

    def _show_view(self, view_cls):
        target = view_cls or DebtsViewWidget
        try:
            from ui.activity_select import SelectActivityWidget

            if target is SelectActivityWidget:
                target = DebtsViewWidget
        except Exception:
            pass
        try:
            self.change_context(target)
        except Exception:
            self.change_context(DebtsViewWidget)

    def reload_current_view(self):
        """Recharge la vue centrale pour appliquer le filtre d'activité."""
        view = getattr(self, "view_widget", None)
        context_cls = type(view) if view is not None else DebtsViewWidget
        try:
            self.change_context(context_cls)
        except Exception:
            self.change_context(DebtsViewWidget)

    def sync_activity_ui(self):
        """Met à jour le titre et le label activité de la toolbar."""
        try:
            from models import Activity

            activity = Activity.get_current()
            self._update_window_title_activity(activity)
        except Exception:
            activity = None

        toolbar = getattr(self, "toolbar", None)
        if toolbar is not None and hasattr(toolbar, "refresh_activity_label"):
            try:
                toolbar.refresh_activity_label()
            except Exception:
                pass

    def _update_window_title_activity(self, activity):
        name = getattr(activity, "name", "") or ""
        suffix = f" — {name}" if name else ""
        self.setWindowTitle(f"{Config.APP_NAME}{suffix}")

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
            # Éviter les doublons: supprimer toute toolbar existante
            existing_tb = getattr(self, "toolbar", None)
            if existing_tb is not None:
                try:
                    self.removeToolBar(existing_tb)
                except Exception:
                    pass
                try:
                    existing_tb.deleteLater()
                except Exception:
                    pass
                self.toolbar = None

            # Certaines versions peuvent avoir des toolbars ajoutées sans référence
            for tb in self.findChildren(QToolBar):
                try:
                    self.removeToolBar(tb)
                except Exception:
                    pass
                try:
                    tb.deleteLater()
                except Exception:
                    pass

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

    def logout(self):
        """Déconnexion : remet le choix d'activité pour la prochaine session."""
        self._activity_chosen_this_session = False
        try:
            super().logout()
        except Exception:
            from Common.models import Owner

            Owner.update(is_identified=False).where(Owner.is_identified == True).execute()

    def exit(self):
        """Méthode de sortie propre de l'application"""
        try:
            self.logout()
        except Exception:
            pass
        try:
            self.close()
        finally:
            # Quitter proprement la boucle Qt (évite les segfaults à la destruction)
            try:
                app = QApplication.instance()
                if app is not None:
                    app.quit()
            except Exception:
                pass

    def on_login_success(self):
        """Appelé après une connexion réussie (si le hook est utilisé)."""
        self.refresh_menu_after_login()
