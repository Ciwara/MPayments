#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from PyQt6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PyQt6.QtCore import Qt

from Common.ui.common import Button, FLabel, FPageTitle, FWidget

# Configuration du logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Palette de couleurs moderne (cohérente avec les autres fichiers)
COLORS = {
    'primary': '#1976D2',
    'primary_light': '#42A5F5',
    'primary_dark': '#0D47A1',
    'secondary': '#FF5722',
    'secondary_light': '#FF8A65',
    'success': '#4CAF50',
    'success_light': '#81C784',
    'warning': '#FF9800',
    'warning_light': '#FFB74D',
    'error': '#F44336',
    'error_light': '#E57373',
    'info': '#2196F3',
    'info_light': '#64B5F6',
    'background': '#F8F9FA',
    'surface': '#FFFFFF',
    'surface_variant': '#F5F5F5',
    'text_primary': '#212121',
    'text_secondary': '#757575',
    'border': '#E0E0E0',
    'shadow': 'rgba(0, 0, 0, 0.1)'
}


class DeleteViewWidget(QDialog, FWidget):
    def __init__(self, table_p, obj, parent, *args, **kwargs):
        super(DeleteViewWidget, self).__init__(parent, *args, **kwargs)
        
        logger.debug("Initialisation du dialogue de suppression avec design moderne")

        self.setWindowTitle("⚠️ Confirmation de suppression")
        
        # Style moderne pour la fenêtre de dialogue supprimé
        
        # Dimensions modernes
        self.setMinimumSize(400, 250)
        self.setMaximumSize(500, 300)

        # Set the title using the object's provider name
        try:
            account_name = obj.provider_clt.name
            self.title = "👤 Compte : {}".format(account_name)
        except AttributeError:
            # Fallback si l'objet n'a pas de provider_clt
            account_name = getattr(obj, 'name', 'Élément sélectionné')
            self.title = "🗑️ Élément : {}".format(account_name)
            
        self.obj = obj
        self.table_p = table_p
        # Use getattr to avoid AttributeError if provid_clt_id does not exist
        self.provid_clt_id = getattr(table_p, "provid_clt_id", None)
        self.parent = parent

        # Layout principal moderne
        vbox = QVBoxLayout()
        vbox.setSpacing(24)
        vbox.setContentsMargins(24, 24, 24, 24)
        
        # Titre principal avec icône d'avertissement
        title_container = QLabel()
        title_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_container.setText("⚠️ ATTENTION - Suppression définitive")
        vbox.addWidget(title_container)
        
        # Zone d'information avec le compte
        info_container = QLabel()
        info_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_container.setText(self.title)
        vbox.addWidget(info_container)
        
        # Message d'avertissement
        warning_text = QLabel()
        warning_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_text.setWordWrap(True)
        warning_text.setText(
            "⚠️ Cette action est irréversible.\n"
            "Êtes-vous sûr de vouloir supprimer cet élément ?"
        )
        vbox.addWidget(warning_text)
        
        # Zone des boutons modernes
        button_container = QHBoxLayout()
        button_container.setSpacing(16)
        button_container.setContentsMargins(0, 16, 0, 0)

        # Bouton annuler (style sécurisé)
        cancel_button = Button("❌ Annuler")
        cancel_button.clicked.connect(self.cancel)
        button_container.addWidget(cancel_button)
        
        # Bouton supprimer (style d'avertissement)
        delete_button = Button("🗑️ Supprimer")
        delete_button.clicked.connect(self.delete)
        button_container.addWidget(delete_button)
        
        # Espacement flexible pour centrer les boutons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addLayout(button_container)
        button_layout.addStretch()
        
        vbox.addLayout(button_layout)
        vbox.addStretch()  # Espacement flexible en bas
        
        self.setLayout(vbox)
        
        logger.debug("Dialogue de suppression initialisé avec design moderne")

    def cancel(self):
        """Fermer le dialogue et retourner False."""
        logger.debug("Suppression annulée par l'utilisateur")
        self.close()
        return False

    def delete(self):
        """Supprimer l'objet, rafraîchir le tableau parent et notifier."""
        logger.debug("Confirmation de suppression par l'utilisateur")
        
        try:
            # Récupérer le nom avant suppression pour la notification
            try:
                item_name = self.obj.provider_clt.name
            except AttributeError:
                item_name = getattr(self.obj, 'name', 'l\'élément')
            
            self.obj.deletes_data()
            logger.debug("Objet supprimé avec succès")
            
            self.cancel()
            
            if self.provid_clt_id is not None:
                self.table_p.refresh_(provid_clt_id=self.provid_clt_id)
            else:
                self.table_p.refresh_()
                
            self.parent.Notify(
                "✅ {} a été supprimé avec succès".format(item_name), "success"
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {str(e)}")
            self.parent.Notify(
                "❌ Erreur lors de la suppression : {}".format(str(e)), "error"
            )
