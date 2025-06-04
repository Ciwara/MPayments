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
from models import CooperativeMember

from configuration import Config

# Configuration du logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Palette de couleurs moderne (cohérente avec dashboard, statistics et debt_manager)
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


class EditOrAddMemberDialog(QDialog, FWidget):
    def __init__(self, table_p, parent, coop_member=None, *args, **kwargs):
        FWidget.__init__(self, parent, *args, **kwargs)
        
        logger.debug("Initialisation de EditOrAddMemberDialog avec design moderne")

        self.table_p = table_p
        self.coop_member = coop_member
        self.parent = parent
        
        if self.coop_member:
            self.new = False
            self.title = "🔧 Modification de {} {}".format(
                self.coop_member.type_, self.coop_member.name
            )
            self.succes_msg = "{} a été bien mise à jour".format(
                self.coop_member.type_
            )
        else:
            self.new = True
            self.succes_msg = "Client a été bien enregistré"
            self.title = "➕ Création d'un nouveau client"
            self.coop_member = CooperativeMember()
            
        self.setWindowTitle(self.title)
        
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
        
        logger.debug("Configuration du titre et des propriétés de base")

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
        
        self.liste_devise = []
        
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
            if self.coop_member.devise == value:
                self.box_devise.setCurrentIndex(index)

        if self.coop_member.phone:
            phone = str(self.coop_member.phone)
        else:
            phone = ""
            
        # Champs de saisie modernes
        self.nameField = LineEdit(self.coop_member.name)
        self.nameField.setStyleSheet(f"""
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
        
        self.legal_infos = LineEdit(self.coop_member.legal_infos)
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
        
        self.address = QTextEdit(self.coop_member.address)
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
        
        self.email = LineEdit(self.coop_member.email)
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

        # Formulaire moderne avec espacement amélioré
        formbox = QFormLayout()
        formbox.setSpacing(16)
        formbox.setContentsMargins(0, 0, 0, 0)
        formbox.setLabelAlignment(Qt.AlignLeft)
        formbox.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        # Labels avec icônes
        formbox.addRow(FormLabel("👤 Nom complet : *"), self.nameField)

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
        
        # Centrer le bouton
        button_layout = QVBoxLayout()
        button_layout.addWidget(butt)
        button_layout.setAlignment(Qt.AlignCenter)
        
        formbox.addRow("", butt)

        vbox.addLayout(formbox)
        vbox.addStretch()  # Espacement flexible en bas
        self.setLayout(vbox)
        
        logger.debug("EditOrAddMemberDialog initialisé avec succès - Design moderne appliqué")

    def save_edit(self):
        """Sauvegarde avec validation moderne"""
        logger.debug("Début de la sauvegarde")
        
        phone = self.phone_field.text()
        
        # Validation des champs obligatoires
        if check_is_empty(self.nameField):
            logger.warning("Champ nom vide")
            return

        coop_member = self.coop_member
        coop_member.name = str(self.nameField.text())

        if Config.DEVISE_PEP_PROV:
            coop_member.devise = str(self.box_devise.currentText().split()[1])

        if not self.new:
            if phone != "":
                coop_member.phone = int(phone)
            coop_member.email = str(self.email.text())
            coop_member.legal_infos = str(self.legal_infos.text())
            coop_member.address = str(self.address.toPlainText())

        try:
            coop_member.save()
            logger.debug("Sauvegarde réussie")
            self.close()
            self.table_p.refresh_()
            self.parent.Notify(
                "Le Compte {} a été mis à jour".format(coop_member.name), "success"
            )
        except peewee.IntegrityError as e:
            logger.error(f"Erreur d'intégrité lors de la sauvegarde: {e}")
            field_error(self.nameField, "Ce nom existe dans la base de données.")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la sauvegarde: {e}")
            self.parent.Notify(
                "Erreur lors de la sauvegarde : {}".format(str(e)), "error"
            )
