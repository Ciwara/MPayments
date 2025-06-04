#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad
from __future__ import unicode_literals, absolute_import, division, print_function

import logging

# import os

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QVBoxLayout, QDialog, QTextEdit, QFormLayout

from configuration import Config

from Common.ui.util import check_is_empty, date_to_datetime
from Common.ui.common import FWidget, ButtonSave, FormLabel, FloatLineEdit, FormatDate

from models import Payment

# Configuration du logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


try:
    unicode
except:
    unicode = str


class EditOrAddPaymentrDialog(QDialog, FWidget):
    def __init__(self, table_p, parent, type_=None, payment=None, *args, **kwargs):
        logger.debug("Initialisation du dialogue de paiement")
        QDialog.__init__(self, parent, *args, **kwargs)

        # Optimisation de la taille de la fenêtre
        self.setFixedWidth(400)
        
        self.type_ = type_
        self.payment = payment
        self.parent = parent
        self.table_p = table_p

        # Mise en cache des valeurs
        self._cached_values = {}
        
        weight = ""
        if self.payment:
            logger.debug("Mode édition d'un paiement existant")
            self.new = False
            self.type_ = payment.type_
            self.payment_date_field = FormatDate(self.payment.date)
            self.payment_date_field.setEnabled(False)
            self.title = "Modification de {} {}".format(
                self.payment.type_, self.payment.libelle
            )
            self.succes_msg = "{} a été bien mise à jour".format(self.payment.type_)

            if self.type_ == Payment.CREDIT:
                amount = payment.credit
            elif self.type_ == Payment.DEBIT:
                amount = payment.debit
                weight = self.payment.weight
        else:
            logger.debug("Mode création d'un nouveau paiement")
            self.new = True
            self.payment = Payment()
            amount = ""
            self.payment_date_field = FormatDate(QDate.currentDate())
            self.succes_msg = "Client a été bien enregistré"
            self.title = "Création d'un nouvel client"

        self.setWindowTitle(self.title)
        logger.debug(f"Titre du dialogue: {self.title}")

        # Optimisation des champs de saisie
        self.payment_weight_field = FloatLineEdit(str(weight).replace(".", ","))
        self.payment_weight_field.setFixedHeight(30)
        
        self.amount_field = FloatLineEdit(str(amount).replace(".", ","))
        self.amount_field.setFixedHeight(30)
        
        self.libelle_field = QTextEdit(self.payment.libelle)
        self.libelle_field.setFixedHeight(60)
        logger.debug("Champs de saisie initialisés")

        vbox = QVBoxLayout()
        vbox.setSpacing(10)  # Réduire l'espacement

        formbox = QFormLayout()
        formbox.setSpacing(10)  # Réduire l'espacement
        formbox.addRow(FormLabel("Date : *"), self.payment_date_field)
        formbox.addRow(FormLabel("Montant : *"), self.amount_field)
        if self.type_ == Payment.DEBIT and Config.CISS:
            formbox.addRow(FormLabel("Poids (Kg) : *"), self.payment_weight_field)
        formbox.addRow(FormLabel("Libelle :"), self.libelle_field)

        butt = ButtonSave("Enregistrer")
        butt.setFixedHeight(30)
        butt.clicked.connect(self.save_edit)
        formbox.addRow("", butt)
        logger.debug("Formulaire configuré")

        vbox.addLayout(formbox)
        self.setLayout(vbox)

    def save_edit(self):
        """add operation avec validation optimisée"""
        logger.debug("Début de la sauvegarde du paiement")
        
        # Validation des champs
        if check_is_empty(self.amount_field):
            logger.warning("Le champ montant est vide")
            return

        # Récupération et nettoyage des données
        self.pro_clt_id = self.table_p.provid_clt_id
        payment_date = str(self.payment_date_field.text())
        libelle = str(self.libelle_field.toPlainText()).strip()
        
        # Optimisation du traitement du montant
        amount_text = self.amount_field.text().replace(",", ".").replace(" ", "").replace("\xa0", "")
        try:
            amount = float(amount_text)
        except ValueError:
            logger.error("Format de montant invalide")
            return
            
        logger.debug(f"Données saisies - Date: {payment_date}, Libellé: {libelle}, Montant: {amount}")

        # Mise à jour du paiement
        payment = self.payment
        payment.type_ = self.type_
        payment.libelle = libelle
        
        if self.new:
            payment.date = date_to_datetime(payment_date)
            payment.provider_clt = self.table_p.provider_clt
            
        if self.type_ == Payment.CREDIT:
            payment.credit = amount
        elif self.type_ == Payment.DEBIT:
            payment.debit = amount

            if Config.CISS:
                if check_is_empty(self.payment_weight_field):
                    logger.warning("Le champ poids est vide")
                    return
                    
                # Optimisation du traitement du poids
                weight_text = self.payment_weight_field.text().replace(",", ".").replace(" ", "").replace("\xa0", "")
                try:
                    payment.weight = float(weight_text) or 0
                except ValueError:
                    logger.error("Format de poids invalide")
                    return
                    
                logger.debug(f"Poids saisi: {payment.weight}")

        try:
            payment.save()
            logger.debug("Paiement sauvegardé avec succès")
            self.close()
            self.parent.Notify(
                "le {type} {lib} à été enregistré avec succès".format(
                    type=self.type_, lib=libelle
                ),
                "success",
            )
            self.table_p.refresh_(provid_clt_id=self.pro_clt_id)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du paiement: {str(e)}")
            self.parent.Notify(e, "error")
