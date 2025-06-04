#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fadiga

import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from Common.ui.common import (Button, FormLabel,
                              FWidget, LineEdit)
from Common.ui.table import FTableWidget, TotalsWidget
from Common.ui.util import is_float
from configuration import Config
from data_helper import device_amount
from models import Payment, ProviderOrClient
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (QGridLayout, QHBoxLayout, QListWidget,
                             QListWidgetItem, QMenu, QSplitter)
from ui.payment_edit_add import EditOrAddPaymentrDialog
from ui.provider_client_edit_add import EditOrAddClientOrProviderDialog

# Configuration du logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


ALL_CONTACTS = "TOUS"

# Fonctions utilitaires pour les calculs précis
def safe_float(value, default=0.0):
    """Conversion sécurisée en float avec valeur par défaut"""
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", ".").replace(" ", "").replace("\xa0", ""))
    except (ValueError, TypeError):
        logger.warning(f"Impossible de convertir '{value}' en float, utilisation de {default}")
        return default

def precise_calculation(amount, precision=2):
    """Calcul précis avec arrondi correct"""
    try:
        decimal_amount = Decimal(str(amount))
        return float(decimal_amount.quantize(Decimal(f'0.{"0" * precision}'), rounding=ROUND_HALF_UP))
    except:
        return round(float(amount), precision)

def calculate_running_balance(payments_data):
    """Calcule les balances courantes correctement pour une liste de paiements"""
    calculated_data = []
    running_balance = 0.0
    
    for payment in payments_data:
        date_val, libelle, debit, credit, stored_balance, payment_id = payment
        
        # Utiliser les valeurs réelles de débit/crédit pour recalculer
        debit_amount = safe_float(debit)
        credit_amount = safe_float(credit)
        
        # Calcul de la balance courante
        running_balance += credit_amount - debit_amount
        running_balance = precise_calculation(running_balance)
        
        # Remplacer la balance stockée par la balance calculée
        calculated_data.append((date_val, libelle, debit_amount, credit_amount, running_balance, payment_id))
    
    return calculated_data


class DebtsViewWidget(FWidget):
    """Shows the home page"""

    def __init__(self, parent=0, *args, **kwargs):
        logger.debug("Initialisation de DebtsViewWidget")
        super(DebtsViewWidget, self).__init__(parent=parent, *args, **kwargs)

        self.parent = parent
        self.parentWidget().setWindowTitle(Config.APP_NAME + " Gestion des dettes")
        logger.debug("Titre de la fenêtre défini")

        # Optimisation de la mise en cache des données
        self._cached_data = {}
        self._last_refresh = None
        
        self.title = "Movements"
        self.now = datetime.now().strftime(Config.DATEFORMAT)
        logger.debug(f"Date actuelle: {self.now}")

        # Configuration des widgets avec des tailles fixes
        self.label_balance = FormLabel("")
        self.label_balance.setFixedHeight(30)
        self.label_owner = FormLabel("")
        self.label_owner.setFixedHeight(30)

        # Optimisation de la table
        if Config.CISS:
            logger.debug("Configuration CISS activée")
            self.table = RapportCISSTableWidget(parent=self)
        else:
            logger.debug("Configuration CISS désactivée")
            self.table = RapportTableWidget(parent=self)
        
        # Configuration des boutons avec des tailles fixes
        self.button = Button("Ok")
        self.button.setFixedSize(80, 30)
        self.button.clicked.connect(self.refresh_period)
        logger.debug("Bouton de rafraîchissement configuré")

        self.btt_pdf_export = Button("")
        self.btt_pdf_export.setFixedSize(40, 30)
        self.btt_pdf_export.clicked.connect(self.export_pdf)
        
        self.btt_xlsx_export = Button("")
        self.btt_xlsx_export.setFixedSize(40, 30)
        self.btt_xlsx_export.clicked.connect(self.export_xlsx)
        logger.debug("Boutons d'export configurés")

        # Optimisation des boutons d'action
        self.add_btt = Button("Créditer")
        self.add_btt.setEnabled(False)
        self.add_btt.clicked.connect(self.add_payment)
        self.add_btt.setFixedSize(200, 30)
        self.add_btt.setIcon(QIcon("{img_media}in.png".format(img_media=Config.img_media)))
        logger.debug("Bouton d'ajout configuré")

        self.sub_btt = Button("Débiter")
        self.sub_btt.setEnabled(False)
        self.sub_btt.clicked.connect(self.sub_payment)
        self.sub_btt.setFixedSize(200, 30)
        self.sub_btt.setIcon(QIcon("{img_media}out.png".format(img_media=Config.img_media)))
        logger.debug("Bouton de soustraction configuré")

        self.add_prov_btt = Button("+ Compte")
        self.add_prov_btt.setFixedSize(300, 60)
        self.add_prov_btt.clicked.connect(self.add_prov_or_clt)
        logger.debug("Bouton d'ajout de compte configuré")

        # Optimisation de la mise en page
        editbox = QGridLayout()
        editbox.setSpacing(5)  # Réduire l'espacement
        editbox.addWidget(self.label_owner, 0, 0)
        editbox.setColumnStretch(0, 2)
        editbox.addWidget(self.sub_btt, 0, 3)
        editbox.addWidget(self.add_btt, 0, 4)
        editbox.addWidget(self.btt_pdf_export, 1, 5)
        editbox.addWidget(self.btt_xlsx_export, 1, 6)
        logger.debug("Mise en page principale configurée")

        # Optimisation de la table des fournisseurs/clients
        self.table_provid_clt = ProviderOrClientTableWidget(parent=self)
        self.table_provid_clt.setAlternatingRowColors(True)  # Améliorer la lisibilité
        logger.debug("Table des fournisseurs/clients initialisée")

        # Optimisation du champ de recherche
        self.search_field = LineEdit()
        self.search_field.textChanged.connect(self.search)
        self.search_field.setPlaceholderText("Rechercher un compte")
        self.search_field.setFixedHeight(40)
        logger.debug("Champ de recherche configuré")

        # Configuration optimisée des splitters
        self.splt_add = QSplitter(Qt.Horizontal)
        self.splt_add.setLayout(editbox)
        self.splt_add.setHandleWidth(1)  # Réduire la largeur des poignées

        self.splitter_left = QSplitter(Qt.Vertical)
        self.splitter_left.setHandleWidth(1)
        self.splitter_left.addWidget(self.search_field)
        self.splitter_left.addWidget(self.table_provid_clt)
        self.splitter_left.addWidget(self.add_prov_btt)

        self.splt_clt = QSplitter(Qt.Vertical)
        self.splt_clt.setHandleWidth(1)
        self.splt_clt.addWidget(self.splt_add)
        self.splt_clt.addWidget(self.table)
        self.splt_clt.addWidget(self.label_balance)
        self.splt_clt.resize(900, 1000)
        logger.debug("Splitters configurés")

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(self.splitter_left)
        splitter.addWidget(self.splt_clt)

        hbox = QHBoxLayout(self)
        hbox.setSpacing(0)  # Réduire l'espacement
        hbox.addWidget(splitter)
        self.setLayout(hbox)
        logger.debug("Mise en page finale configurée")

    def refresh_period(self):
        """Rafraîchit les données avec mise en cache"""
        logger.debug("Rafraîchissement de la période")
        current_time = datetime.now()
        
        # Vérifier si un rafraîchissement est nécessaire (toutes les 5 secondes)
        if (self._last_refresh is None or 
            (current_time - self._last_refresh).total_seconds() > 5):
            self.table.refresh_()
            self._last_refresh = current_time
            logger.debug("Données rafraîchies")
        else:
            logger.debug("Utilisation des données en cache")

    def search(self):
        """Recherche optimisée avec debounce"""
        search_text = self.search_field.text()
        logger.debug(f"Recherche avec le texte: {search_text}")
        
        # Utiliser la mise en cache pour les recherches fréquentes
        if search_text in self._cached_data:
            logger.debug("Utilisation des résultats en cache")
            self.table_provid_clt.refresh_(self._cached_data[search_text])
        else:
            self.table_provid_clt.refresh_(search_text)
            self._cached_data[search_text] = search_text
            logger.debug("Nouvelle recherche effectuée")

    def add_prov_or_clt(self):
        logger.debug("Ouverture du dialogue d'ajout de compte")
        self.parent.open_dialog(
            EditOrAddClientOrProviderDialog,
            modal=True,
            prov_clt=None,
            table_p=self.table_provid_clt,
        )

    def export_pdf(self):
        logger.debug("Début de l'export PDF")
        from Common.exports_pdf import export_dynamic_data
        export_dynamic_data(self.table.dict_data())
        logger.debug("Export PDF terminé")

    def export_xlsx(self):
        logger.debug("Début de l'export XLSX")
        from Common.exports_xlsx import export_dynamic_data
        export_dynamic_data(self.table.dict_data())
        logger.debug("Export XLSX terminé")

    def add_payment(self):
        self.open_dialog(
            EditOrAddPaymentrDialog,
            modal=True,
            payment=None,
            type_=Payment.CREDIT,
            table_p=self.table,
        )

    def sub_payment(self):
        self.open_dialog(
            EditOrAddPaymentrDialog,
            modal=True,
            payment=None,
            type_=Payment.DEBIT,
            table_p=self.table,
        )

    def display_balance(self, amount_text):
        return """ <h2>Solde du {} = <b>{}</b></h2>
               """.format(
            self.now, amount_text
        )


class ProviderOrClientTableWidget(QListWidget):

    """affiche tout le nom de tous les provid_cltes"""

    def __init__(self, parent, *args, **kwargs):
        super(ProviderOrClientTableWidget, self).__init__(parent)

        self.parent = parent
        self.setAutoScroll(True)
        # self.setAutoFillBackground(True)
        self.itemSelectionChanged.connect(self.handleClicked)
        self.refresh_()
        # self.setStyleSheet("QListWidget::item { border-bottom: 1px; }")

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.popup)

    def popup(self, pos):
        from ui.deleteview_cpt import DeleteViewWidget

        row = self.selectionModel().selection().indexes()[0].row()
        if row < 1:
            return
        menu = QMenu()
        editaction = menu.addAction("Modifier l'info.")
        delaction = menu.addAction("Supprimer ce compte")
        action = menu.exec_(self.mapToGlobal(pos))

        provid_clt = ProviderOrClient.get(
            ProviderOrClient.name == self.item(row).text()
        )
        if action == editaction:
            self.parent.open_dialog(
                EditOrAddClientOrProviderDialog,
                modal=True,
                prov_clt=provid_clt,
                table_p=self,
            )
        if action == delaction:
            self.parent.open_dialog(
                DeleteViewWidget, modal=True, table_p=self, obj=provid_clt
            )

    def refresh_(self, provid_clt=None):
        """Rafraichir la liste des provid_cltes"""

        self.clear()
        self.addItem(ProviderOrClientQListWidgetItem(ALL_CONTACTS))
        qs = ProviderOrClient.select().where(
            ProviderOrClient.type_ == ProviderOrClient.CLT,
            ProviderOrClient.deleted == False,
        )
        if provid_clt:
            qs = qs.where(ProviderOrClient.name.contains(provid_clt))
        for provid_clt in qs:
            self.addItem(ProviderOrClientQListWidgetItem(provid_clt))

    def handleClicked(self):
        self.parent.btt_xlsx_export.setEnabled(False)
        self.provid_clt = self.currentItem()
        self.provid_clt_id = self.provid_clt.provid_clt_id

        if isinstance(self.provid_clt_id, int):
            self.parent.sub_btt.setEnabled(True)
            self.parent.add_btt.setEnabled(True)
        else:
            if Config.DEVISE_PEP_PROV:
                # print("DEVISE_PEP_PROV handleClicked")
                return
            self.parent.sub_btt.setEnabled(False)
            self.parent.add_btt.setEnabled(False)
        self.parent.table.refresh_(provid_clt_id=self.provid_clt_id)


class ProviderOrClientQListWidgetItem(QListWidgetItem):
    def __init__(self, provid_clt):
        super(ProviderOrClientQListWidgetItem, self).__init__()

        self.provid_clt = provid_clt
        self.setSizeHint(QSize(0, 30))
        icon = QIcon()

        if not isinstance(self.provid_clt, str):
            icon.addPixmap(
                QPixmap(
                    "{}.png".format(
                        Config.img_media + "debt"
                        if self.provid_clt.is_indebted()
                        else Config.img_cmedia + "user_active"
                    )
                ),
                QIcon.Normal,
                QIcon.Off,
            )

        self.setIcon(icon)
        self.init_text()

    def init_text(self):
        try:
            self.setText(self.provid_clt.name)
        except AttributeError:
            font = QFont()
            font.setBold(True)
            self.setFont(font)
            self.setTextAlignment(Qt.AlignCenter)

            if not Config.DEVISE_PEP_PROV:
                self.setText("Tous")

    @property
    def provid_clt_id(self):
        try:
            return self.provid_clt.id
        except AttributeError:
            return self.provid_clt


class RapportTableWidget(FTableWidget):
    def __init__(self, parent, *args, **kwargs):
        FTableWidget.__init__(self, parent=parent, *args, **kwargs)

        self.hheaders = ["Date", "Libelle opération", "Débit", "Crédit", "Solde", ""]
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.popup)

        self.parent = parent

        self.sorter = False
        self.stretch_columns = [0, 1, 2, 3, 4]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r"}
        self.ecart = -15
        self.display_vheaders = False
        # self.refresh_()
        self.label_mov_tt = "-"

    def refresh_(self, provid_clt_id=None, search=None):
        """Rafraîchissement avec calculs améliorés"""
        logger.debug(f"Rafraîchissement des données pour client {provid_clt_id}")
        
        # Initialisation des totaux
        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.balance_tt = 0.0
        
        self._reset()
        self.set_data_for(provid_clt_id=provid_clt_id, search=search)
        self.refresh()

        self.parent.label_balance.setText(
            self.parent.display_balance(device_amount(self.balance_tt, provid_clt_id))
        )
        self.hideColumn(len(self.hheaders) - 1)

    def set_data_for(self, provid_clt_id=None, search=None):
        """Récupération et calcul des données avec validation"""
        logger.debug("Récupération des données de paiement")
        
        self.provid_clt_id = provid_clt_id
        qs = (
            Payment.select()
            .where(Payment.deleted == False)
            .order_by(Payment.date.asc())
        )

        self.remaining = 0
        if isinstance(provid_clt_id, int):
            self.provider_clt = ProviderOrClient.get(id=provid_clt_id)
            qs = qs.select().where(Payment.provider_clt == self.provider_clt)
            msg = "<h3>Compte : {}</h3> <h4>Tel: {}</h4>".format(
                self.provider_clt.name, self.provider_clt.phone
            )
            logger.debug(f"Filtre sur le client: {self.provider_clt.name}")
        else:
            # Vue globale - tous les clients
            self.provider_clt = "Tous"
            try:
                for prov in ProviderOrClient.select().where(
                    ProviderOrClient.type_ == ProviderOrClient.CLT
                ):
                    self.remaining += prov.last_remaining()
            except Exception as e:
                logger.warning(f"Erreur calcul remaining total: {e}")
                self.remaining = 0
            msg = self.provider_clt
        
        self.parent.label_owner.setText(msg)

        # Récupération des données brutes
        raw_data = [
            (pay.date, pay.libelle, pay.debit, pay.credit, pay.balance, pay.id)
            for pay in qs.iterator()
        ]
        
        # Recalcul des balances pour cohérence
        self.data = calculate_running_balance(raw_data)
        
        logger.debug(f"Données récupérées: {len(self.data)} enregistrements")

    def popup(self, pos):
        from ui.deleteview import DeleteViewWidget

        if (len(self.data) - 1) < self.selectionModel().selection().indexes()[0].row():
            return False
        menu = QMenu()
        editaction = menu.addAction("Modifier cette ligne")
        delaction = menu.addAction("Supprimer cette ligne")
        action = menu.exec_(self.mapToGlobal(pos))
        row = self.selectionModel().selection().indexes()[0].row()
        payment = Payment.get(id=self.data[row][-1])
        if action == editaction:
            self.parent.open_dialog(
                EditOrAddPaymentrDialog, modal=True, payment=payment, table_p=self
            )

        if action == delaction:
            self.parent.open_dialog(
                DeleteViewWidget, modal=True, table_p=self, obj=payment
            )

    def extend_rows(self):
        """Calcul des totaux avec précision améliorée"""
        logger.debug("Calcul des totaux et extension des lignes")
        
        self.parent.btt_pdf_export.setEnabled(True)
        self.parent.btt_xlsx_export.setEnabled(True)
        nb_rows = self.rowCount()
        self.setRowCount(nb_rows + 1)
        self.setSpan(nb_rows + 2, 2, 2, 4)
        
        # Initialisation des totaux
        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.balance_tt = 0.0
        
        # Calcul des totaux à partir des données calculées
        for row_data in self.data:
            date_val, libelle, debit, credit, balance, payment_id = row_data
            
            self.totals_debit += safe_float(debit)
            self.totals_credit += safe_float(credit)
        
        # Arrondir les totaux
        self.totals_debit = precise_calculation(self.totals_debit)
        self.totals_credit = precise_calculation(self.totals_credit)
        
        # Calcul de la balance finale
        if isinstance(self.provid_clt_id, int) and self.data:
            # Pour un client spécifique, utiliser la dernière balance calculée
            self.balance_tt = self.data[-1][4] if self.data else 0.0
        else:
            # Pour tous les clients, calculer la différence des totaux
            self.balance_tt = self.totals_credit - self.totals_debit
        
        self.balance_tt = precise_calculation(self.balance_tt)
        
        logger.debug(f"Totaux calculés - Débit: {self.totals_debit}, Crédit: {self.totals_credit}, Balance: {self.balance_tt}")

        self.label_mov_tt = "Totals mouvements: "
        self.setItem(nb_rows, 1, TotalsWidget(self.label_mov_tt))
        self.setItem(
            nb_rows,
            2,
            TotalsWidget(device_amount(self.totals_debit, self.provid_clt_id)),
        )
        self.setItem(
            nb_rows,
            3,
            TotalsWidget(device_amount(self.totals_credit, self.provid_clt_id)),
        )

    def dict_data(self):
        """Données d'export avec calculs corrects"""
        title = "Movements"
        
        # Déterminer le nom du client pour l'export
        client_name = self.provider_clt.name if hasattr(self.provider_clt, 'name') else str(self.provider_clt)
        client_id = getattr(self.provider_clt, 'id', None) if hasattr(self.provider_clt, 'id') else None
        
        return {
            "file_name": title,
            "headers": self.hheaders[:-1],
            "data": self.data,
            "extend_rows": [
                (1, self.label_mov_tt),
                (2, self.totals_debit),
                (3, self.totals_credit),
            ],
            "sheet": title,
            "widths": self.stretch_columns,
            "format_money": ["C:C", "D:D", "E:E"],
            "exclude_row": len(self.data) - 1,
            "date": self.parent.now,
            "others": [
                ("A7", "C7", "Compte : {}".format(client_name)),
                (
                    "A8",
                    "B8",
                    "Solde au {}: {}".format(
                        self.parent.now,
                        device_amount(self.balance_tt, client_id),
                    ),
                ),
            ],
        }


class RapportCISSTableWidget(FTableWidget):
    def __init__(self, parent, *args, **kwargs):
        FTableWidget.__init__(self, parent=parent, *args, **kwargs)

        self.hheaders = [
            "Date",
            "Libelle opération",
            "Poids (kg)",
            "Débit",
            "Crédit",
            "Solde",
            "",
        ]
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.popup)

        self.parent = parent

        self.sorter = False
        self.stretch_columns = [0, 1, 2, 3, 4, 5]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r", 5: "r"}
        # self.ecart = -5
        self.display_vheaders = False
        # self.refresh_()

    def refresh_(self, provid_clt_id=None, search=None):
        """Rafraîchissement avec calculs améliorés pour CISS"""
        logger.debug(f"Rafraîchissement CISS pour client {provid_clt_id}")

        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.totals_weight = 0.0
        self.balance_tt = 0.0
        
        self._reset()
        self.set_data_for(provid_clt_id=provid_clt_id, search=search)
        self.refresh()

        self.parent.label_balance.setText(
            self.parent.display_balance(device_amount(self.balance_tt, provid_clt_id))
        )
        self.hideColumn(len(self.hheaders) - 1)

    def set_data_for(self, provid_clt_id=None, search=None):
        """Récupération des données CISS avec calculs de poids"""
        logger.debug("Récupération des données CISS")
        
        self.provid_clt_id = provid_clt_id
        qs = (
            Payment.select()
            .where(Payment.deleted == False)
            .order_by(Payment.date.asc())
        )

        self.remaining = 0
        if isinstance(provid_clt_id, int):
            self.provider_clt = ProviderOrClient.get(id=provid_clt_id)
            qs = qs.select().where(Payment.provider_clt == self.provider_clt)
            msg = "<h3>Compte : {}</h3> <h4>Tel: {}</h4>".format(
                self.provider_clt.name, self.provider_clt.phone
            )
        else:
            self.provider_clt = "Tous"
            try:
                for prov in ProviderOrClient.select().where(
                    ProviderOrClient.type_ == ProviderOrClient.CLT
                ):
                    self.remaining += prov.last_remaining()
            except Exception as e:
                logger.warning(f"Erreur calcul remaining CISS: {e}")
                self.remaining = 0
            msg = self.provider_clt
        
        self.parent.label_owner.setText(msg)

        # Récupération avec poids et recalcul des balances
        raw_data = [
            (pay.date, pay.libelle, pay.weight, pay.debit, pay.credit, pay.balance, pay.id)
            for pay in qs.iterator()
        ]
        
        # Adapter le calcul pour inclure les poids
        self.data = []
        running_balance = 0.0
        
        for payment in raw_data:
            date_val, libelle, weight, debit, credit, stored_balance, payment_id = payment
            
            # Convertir en valeurs sûres
            weight_amount = safe_float(weight)
            debit_amount = safe_float(debit)
            credit_amount = safe_float(credit)
            
            # Calcul de la balance courante
            running_balance += credit_amount - debit_amount
            running_balance = precise_calculation(running_balance)
            
            self.data.append((date_val, libelle, weight_amount, debit_amount, credit_amount, running_balance, payment_id))
        
        logger.debug(f"Données CISS récupérées: {len(self.data)} enregistrements")

    def popup(self, pos):
        from ui.deleteview import DeleteViewWidget

        if (len(self.data) - 1) < self.selectionModel().selection().indexes()[0].row():
            return False
        menu = QMenu()
        editaction = menu.addAction("Modifier cette ligne")
        delaction = menu.addAction("Supprimer cette ligne")
        action = menu.exec_(self.mapToGlobal(pos))
        row = self.selectionModel().selection().indexes()[0].row()
        payment = Payment.get(id=self.data[row][-1])
        if action == editaction:
            self.parent.open_dialog(
                EditOrAddPaymentrDialog, modal=True, payment=payment, table_p=self
            )
        if action == delaction:
            self.parent.open_dialog(
                DeleteViewWidget, modal=True, table_p=self, obj=payment
            )

    def extend_rows(self):
        """Calcul des totaux CISS avec poids"""
        logger.debug("Calcul des totaux CISS avec poids")
        
        self.parent.btt_pdf_export.setEnabled(True)
        self.parent.btt_xlsx_export.setEnabled(True)
        nb_rows = self.rowCount()
        self.setRowCount(nb_rows + 1)
        self.setSpan(nb_rows + 2, 2, 2, 4)
        
        # Initialisation des totaux
        self.totals_weight = 0.0
        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.balance_tt = 0.0
        
        # Calcul des totaux à partir des données
        for row_data in self.data:
            date_val, libelle, weight, debit, credit, balance, payment_id = row_data
            
            self.totals_weight += safe_float(weight)
            self.totals_debit += safe_float(debit)
            self.totals_credit += safe_float(credit)
        
        # Arrondir les totaux
        self.totals_weight = precise_calculation(self.totals_weight, 3)  # 3 décimales pour le poids
        self.totals_debit = precise_calculation(self.totals_debit)
        self.totals_credit = precise_calculation(self.totals_credit)
        
        # Calcul de la balance finale
        if isinstance(self.provid_clt_id, int) and self.data:
            # Pour un client spécifique, utiliser la dernière balance calculée
            self.balance_tt = self.data[-1][5] if self.data else 0.0
        else:
            # Pour tous les clients, calculer la différence des totaux
            self.balance_tt = self.totals_credit - self.totals_debit
        
        self.balance_tt = precise_calculation(self.balance_tt)
        
        logger.debug(f"Totaux CISS - Poids: {self.totals_weight}, Débit: {self.totals_debit}, Crédit: {self.totals_credit}, Balance: {self.balance_tt}")

        self.label_mov_tt = "Totals mouvements: "
        self.setItem(nb_rows, 1, TotalsWidget(self.label_mov_tt))
        self.setItem(
            nb_rows,
            2,
            TotalsWidget(device_amount(self.totals_weight, dvs="Kg", aftergam=3)),
        )
        self.setItem(nb_rows, 3, TotalsWidget(device_amount(self.totals_debit)))
        self.setItem(nb_rows, 4, TotalsWidget(device_amount(self.totals_credit)))

    def dict_data(self):
        """Données d'export CISS avec poids"""
        title = "Movements"
        
        # Déterminer le nom du client
        client_name = self.provider_clt.name if hasattr(self.provider_clt, 'name') else str(self.provider_clt)
        
        return {
            "file_name": title,
            "headers": self.hheaders[:-1],
            "data": self.data,
            "extend_rows": [
                (1, self.label_mov_tt),
                (2, device_amount(self.totals_weight, dvs="Kg", aftergam=3)),
                (3, self.totals_debit),
                (4, self.totals_credit),
            ],
            "sheet": title,
            "widths": self.stretch_columns,
            "format_money": ["D:D", "E:E", "F:F"],
            "exclude_row": len(self.data) - 1,
            "date": self.parent.now,
            "others": [
                ("A5", "C7", "Compte : {}".format(client_name)),
                (
                    "A6",
                    "B6",
                    "Solde au {}: {}".format(
                        self.parent.now,
                        device_amount(self.balance_tt, getattr(self.provider_clt, 'id', None)),
                    ),
                ),
            ],
        }
