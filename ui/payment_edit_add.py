#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad
from __future__ import unicode_literals, absolute_import, division, print_function

import logging

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import QVBoxLayout, QDialog, QTextEdit, QFormLayout
from PyQt6.QtGui import QFont

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

try:
    unicode
except:
    unicode = str


class EditOrAddPaymentrDialog(QDialog, FWidget):
    def __init__(self, table_p, parent, type_=None, payment=None, *args, **kwargs):
        logger.debug("Initialisation du dialogue de paiement avec design moderne")
        QDialog.__init__(self, parent, *args, **kwargs)
        
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
            
            # Titres avec icônes selon le type
            type_icon = "💰" if self.type_ == Payment.CREDIT else "💸"
            self.title = "🔧 Modification {} {}".format(type_icon, self.payment.libelle)
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
            self.succes_msg = "Paiement enregistré avec succès"
            
            # Titres avec icônes selon le type
            if self.type_ == Payment.CREDIT:
                self.title = "➕ Nouveau Crédit 💰"
            elif self.type_ == Payment.DEBIT:
                self.title = "➖ Nouveau Débit 💸"
            else:
                self.title = "➕ Nouveau Paiement"

        self.setWindowTitle(self.title)
        logger.debug(f"Titre du dialogue: {self.title}")
        
        # Style moderne pour la fenêtre de dialogue
        
        # Dimensions modernes
        self.setMinimumSize(420, 350)
        self.setMaximumSize(500, 450)

        # Champs de saisie modernes
        
        self.payment_weight_field = FloatLineEdit(str(weight).replace(".", ","))
        self.payment_weight_field.setFixedHeight(40)
        
        self.amount_field = FloatLineEdit(str(amount).replace(".", ","))
        self.amount_field.setFixedHeight(45)
        
        self.libelle_field = QTextEdit(self.payment.libelle)
        self.libelle_field.setFixedHeight(80)
        logger.debug("Champs de saisie initialisés avec style moderne")

        vbox = QVBoxLayout()
        vbox.setSpacing(24)
        vbox.setContentsMargins(24, 24, 24, 24)
        
        # Titre principal moderne
        title_label = FormLabel(self.title)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        vbox.addWidget(title_label)

        # Formulaire moderne avec espacement amélioré
        formbox = QFormLayout()
        formbox.setSpacing(16)
        formbox.setContentsMargins(0, 0, 0, 0)
        formbox.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        formbox.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        # Labels avec icônes
        formbox.addRow(FormLabel("📅 Date : *"), self.payment_date_field)
        
        # Label spécial pour le montant selon le type
        if self.type_ == Payment.CREDIT:
            amount_label = "💰 Montant à créditer : *"
        elif self.type_ == Payment.DEBIT:
            amount_label = "💸 Montant à débiter : *"
        else:
            amount_label = "💰 Montant : *"
        formbox.addRow(FormLabel(amount_label), self.amount_field)
        
        if self.type_ == Payment.DEBIT and Config.CISS:
            formbox.addRow(FormLabel("⚖️ Poids (Kg) : *"), self.payment_weight_field)
        formbox.addRow(FormLabel("📝 Libellé :"), self.libelle_field)

        # Bouton d'enregistrement moderne
        butt = ButtonSave("💾 Enregistrer")
        butt.clicked.connect(self.save_edit)
        formbox.addRow("", butt)
        logger.debug("Formulaire configuré avec style moderne")

        vbox.addLayout(formbox)
        vbox.addStretch()  # Espacement flexible en bas
        self.setLayout(vbox)

    def save_edit(self):
        """Sauvegarde avec validation moderne"""
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
            self.parent.Notify("Format de montant invalide", "error")
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
                    self.parent.Notify("Le champ poids est obligatoire", "error")
                    return
                    
                # Optimisation du traitement du poids
                weight_text = self.payment_weight_field.text().replace(",", ".").replace(" ", "").replace("\xa0", "")
                try:
                    payment.weight = float(weight_text) or 0
                except ValueError:
                    logger.error("Format de poids invalide")
                    self.parent.Notify("Format de poids invalide", "error")
                    return
                    
                logger.debug(f"Poids saisi: {payment.weight}")

        try:
            payment.save()
            logger.debug("Paiement sauvegardé avec succès")
            self.close()
            self.parent.Notify(
                "✅ Le {type} {lib} a été enregistré avec succès".format(
                    type=self.type_, lib=libelle
                ),
                "success",
            )
            self.table_p.refresh_(provid_clt_id=self.pro_clt_id)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du paiement: {str(e)}")
            self.parent.Notify("❌ Erreur : {}".format(str(e)), "error")
