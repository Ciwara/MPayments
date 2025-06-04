#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

import logging

from PyQt5.QtWidgets import QVBoxLayout, QDialog, QTextEdit, QFormLayout, QComboBox

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


class EditOrAddClientOrProviderDialog(QDialog, FWidget):
    def __init__(self, table_p, parent, prov_clt=None, *args, **kwargs):
        logger.debug("Initialisation du dialogue client/fournisseur")
        FWidget.__init__(self, parent, *args, **kwargs)

        self.table_p = table_p
        self.prov_clt = prov_clt
        self.parent = parent
        if self.prov_clt:
            logger.debug("Mode édition d'un client/fournisseur existant")
            self.new = False
            self.title = u"Modification de {} {}".format(
                self.prov_clt.type_, self.prov_clt.name
            )
            self.succes_msg = u"{} a été bien mise à jour".format(self.prov_clt.type_)
        else:
            logger.debug("Mode création d'un nouveau client/fournisseur")
            self.new = True
            self.succes_msg = u"Client a été bien enregistré"
            self.title = u"Création d'un nouvel client"
            self.prov_clt = ProviderOrClient()
        self.setWindowTitle(self.title)
        logger.debug(f"Titre du dialogue: {self.title}")

        vbox = QVBoxLayout()
        self.liste_devise = ProviderOrClient.DEVISE
        logger.debug(f"Liste des devises: {self.liste_devise}")

        # Combobox widget
        self.box_devise = QComboBox()
        for index, value in enumerate(self.liste_devise):
            self.box_devise.addItem("{} {}".format(self.liste_devise[value], value))
            if self.prov_clt.devise == value:
                self.box_devise.setCurrentIndex(index)
        logger.debug("Combo box des devises configuré")

        if self.prov_clt.phone:
            phone = str(self.prov_clt.phone)
        else:
            phone = ""
        self.nameField = LineEdit(self.prov_clt.name)
        self.phone_field = IntLineEdit(phone)
        self.legal_infos = LineEdit(self.prov_clt.legal_infos)
        self.address = QTextEdit(self.prov_clt.address)
        self.email = LineEdit(self.prov_clt.email)
        logger.debug("Champs de saisie initialisés")

        formbox = QFormLayout()
        formbox.addRow(FormLabel(u"Nom complete : *"), self.nameField)

        if Config.DEVISE_PEP_PROV:
            formbox.addRow(FormLabel(u"Devise :"), self.box_devise)

        if not self.new:
            formbox.addRow(FormLabel(u"Tel: *"), self.phone_field)
            formbox.addRow(FormLabel(u"E-mail :"), self.email)
            formbox.addRow(FormLabel(u"addresse complete :"), self.address)
            formbox.addRow(FormLabel(u"Info. legale :"), self.legal_infos)

        butt = Button(u"Enregistrer")
        butt.clicked.connect(self.save_edit)
        formbox.addRow("", butt)
        logger.debug("Formulaire configuré")

        vbox.addLayout(formbox)
        self.setLayout(vbox)

    def save_edit(self):
        """add operation"""
        logger.debug("Début de la sauvegarde du client/fournisseur")
        phone = self.phone_field.text()
        if check_is_empty(self.nameField):
            logger.warning("Le champ nom est vide")
            return

        prov_clt = self.prov_clt
        prov_clt.name = str(self.nameField.text())
        logger.debug(f"Nom saisi: {prov_clt.name}")

        if Config.DEVISE_PEP_PROV:
            prov_clt.devise = str(self.box_devise.currentText().split()[1])
            logger.debug(f"Devise sélectionnée: {prov_clt.devise}")

        if not self.new:
            if phone != "":
                prov_clt.phone = int(phone)
                logger.debug(f"Téléphone saisi: {prov_clt.phone}")
            prov_clt.email = str(self.email.text())
            prov_clt.legal_infos = str(self.legal_infos.text())
            prov_clt.address = str(self.address.toPlainText())
            logger.debug("Informations complémentaires saisies")

        try:
            prov_clt.save()
            logger.debug("Client/fournisseur sauvegardé avec succès")
            self.close()
            self.table_p.refresh_()
        except peewee.IntegrityError as e:
            logger.error(f"Erreur d'intégrité lors de la sauvegarde: {str(e)}")
            field_error(self.nameField, "Ce nom existe dans la basse de donnée.")
