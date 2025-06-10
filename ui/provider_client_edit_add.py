#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

import logging

from PyQt5.QtWidgets import QVBoxLayout, QDialog, QTextEdit, QFormLayout, QComboBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from Common.ui.util import check_is_empty, field_error
from Common.ui.common import FWidget, Button, FormLabel, LineEdit, IntLineEdit
import peewee
from models import ProviderOrClient

from configuration import Config

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


class EditOrAddClientOrProviderDialog(QDialog, FWidget):
    def __init__(self, table_p, parent, prov_clt=None, *args, **kwargs):
        logger.debug("Initialisation du dialogue client/fournisseur avec design moderne")
        FWidget.__init__(self, parent, *args, **kwargs)

        self.table_p = table_p
        self.prov_clt = prov_clt
        self.parent = parent
        
        if self.prov_clt:
            logger.debug("Mode édition d'un client/fournisseur existant")
            self.new = False
            # Icône selon le type
            type_icon = "👤" if self.prov_clt.type_ == "Client" else "🏢"
            self.title = "🔧 Modification {} {} {}".format(type_icon, self.prov_clt.type_, self.prov_clt.name)
            self.succes_msg = "{} a été bien mis à jour".format(self.prov_clt.type_)
        else:
            logger.debug("Mode création d'un nouveau client/fournisseur")
            self.new = True
            self.succes_msg = "Compte créé avec succès"
            self.title = "➕ Création d'un nouveau compte"
            self.prov_clt = ProviderOrClient()
            
        self.setWindowTitle(self.title)
        logger.debug(f"Titre du dialogue: {self.title}")
        
        # Style moderne pour la fenêtre de dialogue
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
                font-family: "Segoe UI", "Arial", sans-serif;
                font-size: 12px;
            }}
            QLabel {{
                color: {COLORS['text_primary']};
                font-weight: 600;
                font-size: 12px;
                padding: 4px 0;
            }}
        """)
        
        # Dimensions modernes
        self.setMinimumSize(500, 400)
        self.setMaximumSize(600, 600)

        vbox = QVBoxLayout()
        vbox.setSpacing(20)
        vbox.setContentsMargins(24, 24, 24, 24)
        
        # Titre principal moderne
        title_label = FormLabel(self.title)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['primary']};
                font-weight: 700;
                font-size: 16px;
                padding: 16px 0;
                border-bottom: 2px solid {COLORS['primary_light']};
                margin-bottom: 16px;
            }}
        """)
        vbox.addWidget(title_label)
        
        self.liste_devise = ProviderOrClient.DEVISE
        logger.debug(f"Liste des devises: {self.liste_devise}")

        # Combobox moderne pour les devises
        self.box_devise = QComboBox()
        self.box_devise.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                color: {COLORS['text_primary']};
                min-height: 20px;
                font-weight: 500;
            }}
            QComboBox:focus {{
                border-color: {COLORS['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {COLORS['text_secondary']};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 4px;
                font-size: 12px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: 4px;
                margin: 2px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {COLORS['primary_light']};
                color: white;
            }}
        """)
        
        for index, value in enumerate(self.liste_devise):
            self.box_devise.addItem("{} {}".format(self.liste_devise[value], value))
            if self.prov_clt.devise == value:
                self.box_devise.setCurrentIndex(index)
        logger.debug("Combo box des devises configuré")

        if self.prov_clt.phone:
            phone = str(self.prov_clt.phone)
        else:
            phone = ""
            
        # Champs de saisie modernes
        self.nameField = LineEdit(self.prov_clt.name)
        self.nameField.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['primary_light']};
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                color: {COLORS['text_primary']};
                font-weight: 600;
                min-height: 24px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
            }}
            QLineEdit:hover {{
                border-color: {COLORS['primary']};
            }}
        """)
        
        self.phone_field = IntLineEdit(phone)
        self.phone_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 12px;
                color: {COLORS['text_primary']};
                font-weight: 500;
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
            }}
            QLineEdit:hover {{
                border-color: {COLORS['primary_light']};
            }}
        """)
        
        self.legal_infos = LineEdit(self.prov_clt.legal_infos)
        self.legal_infos.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 12px;
                color: {COLORS['text_primary']};
                font-weight: 500;
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
            }}
            QLineEdit:hover {{
                border-color: {COLORS['primary_light']};
            }}
        """)
        
        self.address = QTextEdit(self.prov_clt.address)
        self.address.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 12px;
                color: {COLORS['text_primary']};
                font-weight: 500;
                min-height: 80px;
            }}
            QTextEdit:focus {{
                border-color: {COLORS['primary']};
            }}
            QTextEdit:hover {{
                border-color: {COLORS['primary_light']};
            }}
        """)
        
        self.email = LineEdit(self.prov_clt.email)
        self.email.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 12px;
                color: {COLORS['text_primary']};
                font-weight: 500;
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
            }}
            QLineEdit:hover {{
                border-color: {COLORS['primary_light']};
            }}
        """)
        
        logger.debug("Champs de saisie initialisés avec style moderne")

        # Formulaire moderne avec espacement amélioré
        formbox = QFormLayout()
        formbox.setSpacing(16)
        formbox.setContentsMargins(0, 0, 0, 0)
        formbox.setLabelAlignment(Qt.AlignLeft)
        formbox.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        # Labels avec icônes
        formbox.addRow(FormLabel("👤 Nom complet : *"), self.nameField)

        if Config.DEVISE_PEP_PROV:
            formbox.addRow(FormLabel("💱 Devise :"), self.box_devise)

        if not self.new:
            formbox.addRow(FormLabel("📱 Téléphone : *"), self.phone_field)
            formbox.addRow(FormLabel("📧 E-mail :"), self.email)
            formbox.addRow(FormLabel("🏠 Adresse complète :"), self.address)
            formbox.addRow(FormLabel("📋 Info. légale :"), self.legal_infos)

        # Bouton d'enregistrement moderne
        butt = Button("💾 Enregistrer")
        butt.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px 32px;
                font-weight: 700;
                font-size: 13px;
                min-width: 200px;
                min-height: 50px;
                margin-top: 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_light']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['success']};
            }}
        """)
        butt.clicked.connect(self.save_edit)
        formbox.addRow("", butt)
        logger.debug("Formulaire configuré avec style moderne")

        vbox.addLayout(formbox)
        vbox.addStretch()  # Espacement flexible en bas
        self.setLayout(vbox)

    def save_edit(self):
        """Sauvegarde avec validation moderne"""
        logger.debug("Début de la sauvegarde du client/fournisseur")
        phone = self.phone_field.text()
        
        if check_is_empty(self.nameField):
            logger.warning("Le champ nom est vide")
            self.parent.Notify("Le nom est obligatoire", "error")
            return

        prov_clt = self.prov_clt
        prov_clt.name = str(self.nameField.text())
        logger.debug(f"Nom saisi: {prov_clt.name}")

        if Config.DEVISE_PEP_PROV:
            prov_clt.devise = str(self.box_devise.currentText().split()[1])
            logger.debug(f"Devise sélectionnée: {prov_clt.devise}")

        if not self.new:
            if phone != "":
                try:
                    prov_clt.phone = int(phone)
                    logger.debug(f"Téléphone saisi: {prov_clt.phone}")
                except ValueError:
                    self.parent.Notify("Format de téléphone invalide", "error")
                    return
            prov_clt.email = str(self.email.text())
            prov_clt.legal_infos = str(self.legal_infos.text())
            prov_clt.address = str(self.address.toPlainText())
            logger.debug("Informations complémentaires saisies")

        try:
            prov_clt.save()
            logger.debug("Client/fournisseur sauvegardé avec succès")
            self.close()
            self.table_p.refresh_()
            self.parent.Notify(
                "✅ Le compte {} a été mis à jour avec succès".format(prov_clt.name), "success"
            )
        except peewee.IntegrityError as e:
            logger.error(f"Erreur d'intégrité lors de la sauvegarde: {str(e)}")
            field_error(self.nameField, "Ce nom existe déjà dans la base de données.")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la sauvegarde: {str(e)}")
            self.parent.Notify(
                "❌ Erreur lors de la sauvegarde : {}".format(str(e)), "error"
            )
