#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

import logging

from PyQt6.QtWidgets import QVBoxLayout, QDialog, QTextEdit, QFormLayout, QComboBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

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
        
        if self.prov_clt and getattr(self.prov_clt, "id", None):
            logger.debug("Mode édition d'un client/fournisseur existant")
            self.new = False
            type_icon = "👤" if self.prov_clt.type_ == ProviderOrClient.CLT else "🏢"
            self.title = "🔧 Modification {} {} — {}".format(
                type_icon, self.prov_clt.type_, self.prov_clt.name
            )
            self.succes_msg = "{} mis à jour avec succès".format(self.prov_clt.type_)
        else:
            logger.debug("Mode création d'un nouveau client/fournisseur")
            self.new = True
            self.succes_msg = "Compte créé avec succès"
            self.title = "➕ Nouveau compte"
            self.prov_clt = ProviderOrClient()
            self.prov_clt.type_ = ProviderOrClient.CLT
            
        self.setWindowTitle(self.title)
        logger.debug(f"Titre du dialogue: {self.title}")
        
        # Style moderne pour la fenêtre de dialogue
        
        # Dimensions modernes
        self.setMinimumSize(500, 400)
        self.setMaximumSize(600, 600)

        vbox = QVBoxLayout()
        vbox.setSpacing(20)
        vbox.setContentsMargins(24, 24, 24, 24)
        
        # Titre principal moderne
        title_label = FormLabel(self.title)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        vbox.addWidget(title_label)
        
        self.liste_devise = ProviderOrClient.DEVISE
        logger.debug(f"Liste des devises: {self.liste_devise}")

        # Type de compte (Client / Fournisseur) — en création uniquement
        self.box_type = QComboBox()
        self.box_type.addItem("👤 Client", ProviderOrClient.CLT)
        self.box_type.addItem("🏢 Fournisseur", ProviderOrClient.FSEUR)
        if self.prov_clt.type_ == ProviderOrClient.FSEUR:
            self.box_type.setCurrentIndex(1)
        logger.debug("Combo type compte configuré")

        # Combobox pour les devises
        self.box_devise = QComboBox()
        for index, value in enumerate(self.liste_devise):
            self.box_devise.addItem("{} {}".format(self.liste_devise[value], value))
            if getattr(self.prov_clt, "devise", None) == value:
                self.box_devise.setCurrentIndex(index)
        logger.debug("Combo box des devises configuré")

        if getattr(self.prov_clt, "phone", None):
            phone = str(self.prov_clt.phone)
        else:
            phone = ""
            
        # Champs de saisie avec placeholders
        name_init = getattr(self.prov_clt, "name", None) or ""
        self.nameField = LineEdit(name_init)
        self.nameField.setPlaceholderText("Nom du compte (obligatoire)")
        self.phone_field = IntLineEdit(phone)
        self.phone_field.setPlaceholderText("Numéro de téléphone")
        self.legal_infos = LineEdit(getattr(self.prov_clt, "legal_infos", None) or "")
        self.legal_infos.setPlaceholderText("Informations légales (SIRET, etc.)")
        self.address = QTextEdit(getattr(self.prov_clt, "address", None) or "")
        self.address.setPlaceholderText("Adresse complète")
        self.email = LineEdit(getattr(self.prov_clt, "email", None) or "")
        self.email.setPlaceholderText("exemple@email.com")
        
        logger.debug("Champs de saisie initialisés avec style moderne")

        # Formulaire moderne avec espacement amélioré
        formbox = QFormLayout()
        formbox.setSpacing(16)
        formbox.setContentsMargins(0, 0, 0, 0)
        formbox.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        formbox.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        formbox.addRow(FormLabel("👤 Nom : *"), self.nameField)

        if self.new:
            formbox.addRow(FormLabel("Type :"), self.box_type)

        if Config.DEVISE_PEP_PROV:
            formbox.addRow(FormLabel("💱 Devise :"), self.box_devise)

        if not self.new:
            formbox.addRow(FormLabel("📱 Téléphone : *"), self.phone_field)
            formbox.addRow(FormLabel("📧 E-mail :"), self.email)
            formbox.addRow(FormLabel("🏠 Adresse complète :"), self.address)
            formbox.addRow(FormLabel("📋 Info. légale :"), self.legal_infos)

        # Bouton d'enregistrement moderne
        butt = Button("💾 Enregistrer")
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
        prov_clt.name = str(self.nameField.text()).strip()
        logger.debug(f"Nom saisi: {prov_clt.name}")

        if self.new:
            prov_clt.type_ = self.box_type.currentData()
            logger.debug(f"Type sélectionné: {prov_clt.type_}")

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
