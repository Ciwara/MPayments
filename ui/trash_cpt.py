#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fadiga

import logging
from datetime import datetime

from Common.ui.common import (
    BttExportPDF,
    BttExportXLSX,
    Button,
    FormLabel,
    FWidget,
    LineEdit,
)
from Common.ui.table import FTableWidget, TotalsWidget
from Common.ui.util import is_float
from configuration import Config
from data_helper import device_amount
from models import Payment, ProviderOrClient
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QSplitter,
)
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


class DebtsTrashViewWidget(FWidget):

    """Shows the home page"""

    def __init__(self, parent=0, *args, **kwargs):
        logger.debug("Initialisation de DebtsTrashViewWidget")
        super(DebtsTrashViewWidget, self).__init__(parent=parent, *args, **kwargs)
        self.parent = parent
        self.parentWidget().setWindowTitle(
            Config.APP_NAME + " Gestion des element supprimer"
        )
        logger.debug("Titre de la fenêtre défini")

        self.title = "Movements"
        self.now = datetime.now().strftime(Config.DATEFORMAT)
        logger.debug(f"Date actuelle: {self.now}")

        self.label_balance = FormLabel("")
        self.label_owner = FormLabel("")

        if Config.CISS:
            logger.debug("Configuration CISS activée")
            self.table = RapportCISSTableWidget(parent=self)
        else:
            logger.debug("Configuration CISS désactivée")
            self.table = RapportTableWidget(parent=self)

        self.button = Button("Ok")
        self.button.clicked.connect(self.refresh_period)
        logger.debug("Bouton de rafraîchissement configuré")

        self.add_btt = Button("Supprimer")
        self.add_btt.setEnabled(False)
        self.add_btt.clicked.connect(self.suppression)
        self.add_btt.setMaximumHeight(90)
        self.add_btt.setIcon(
            QIcon("{img_media}del.png".format(img_media=Config.img_media))
        )
        logger.debug("Bouton de suppression configuré")

        self.sub_btt = Button("Restorer")
        self.sub_btt.setEnabled(False)
        self.sub_btt.clicked.connect(self.restoration)
        self.sub_btt.setMaximumHeight(90)
        logger.debug("Bouton de restauration configuré")

        editbox = QGridLayout()
        editbox.addWidget(self.label_owner, 0, 0)
        editbox.setColumnStretch(0, 2)
        editbox.addWidget(self.sub_btt, 0, 3)
        editbox.addWidget(self.add_btt, 0, 4)
        logger.debug("Mise en page principale configurée")

        self.table_provid_clt = ProviderOrClientTableWidget(parent=self)
        logger.debug("Table des fournisseurs/clients initialisée")

        self.search_field = LineEdit()
        self.search_field.textChanged.connect(self.search)
        self.search_field.setPlaceholderText("Rechercher un compte")
        self.search_field.setMaximumHeight(40)
        logger.debug("Champ de recherche configuré")

        self.splt_add = QSplitter(Qt.Horizontal)
        self.splt_add.setLayout(editbox)

        self.splitter_left = QSplitter(Qt.Vertical)
        self.splitter_left.addWidget(self.search_field)
        self.splitter_left.addWidget(self.table_provid_clt)

        self.splt_clt = QSplitter(Qt.Vertical)
        self.splt_clt.addWidget(self.splt_add)
        self.splt_clt.addWidget(self.table)
        self.splt_clt.addWidget(self.label_balance)
        logger.debug("Splitters configurés")

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.splitter_left)
        splitter.addWidget(self.splt_clt)

        hbox = QHBoxLayout(self)
        hbox.addWidget(splitter)
        self.setLayout(hbox)
        logger.debug("Mise en page finale configurée")

    def refresh_period(self):
        logger.debug("Rafraîchissement de la période")
        self.table.refresh_()

    def search(self):
        search_text = self.search_field.text()
        logger.debug(f"Recherche avec le texte: {search_text}")
        self.table_provid_clt.refresh_(search_text)

    def suppression(self):
        provid_clt_id = self.table_provid_clt.provid_clt_id
        logger.debug(f"Suppression du compte ID: {provid_clt_id}")
        ProviderOrClient.get(id=provid_clt_id).delete_permanate()
        self.table_provid_clt.refresh_()
        logger.debug("Compte supprimé avec succès")

    def restoration(self):
        provid_clt_id = self.table_provid_clt.provid_clt_id
        logger.debug(f"Restauration du compte ID: {provid_clt_id}")
        ProviderOrClient.get(id=provid_clt_id).restore_data()
        self.table_provid_clt.refresh_()
        logger.debug("Compte restauré avec succès")

    def display_balance(self, amount_text):
        logger.debug(f"Affichage du solde: {amount_text}")
        return """ <h2>Solde du {} = <b>{}</b></h2>
               """.format(
            self.now, amount_text
        )


class ProviderOrClientTableWidget(QListWidget):

    """affiche tout le nom de tous les provid_cltes"""

    def __init__(self, parent, *args, **kwargs):
        logger.debug("Initialisation de ProviderOrClientTableWidget")
        super(ProviderOrClientTableWidget, self).__init__(parent)

        self.parent = parent
        self.setAutoScroll(True)
        self.itemSelectionChanged.connect(self.handleClicked)
        self.refresh_()
        logger.debug("Table des fournisseurs/clients initialisée")

    def refresh_(self, provid_clt=None):
        """Rafraichir la liste des provid_cltes"""
        logger.debug("Rafraîchissement de la liste des fournisseurs/clients")
        self.clear()
        self.addItem(ProviderOrClientQListWidgetItem(ALL_CONTACTS))
        qs = ProviderOrClient.select().where(
            ProviderOrClient.type_ == ProviderOrClient.CLT,
            ProviderOrClient.deleted == True,
        )
        if provid_clt:
            logger.debug(f"Filtrage avec le texte: {provid_clt}")
            qs = qs.where(ProviderOrClient.name.contains(provid_clt))
        for provid_clt in qs:
            self.addItem(ProviderOrClientQListWidgetItem(provid_clt))
        logger.debug(f"Nombre d'éléments chargés: {self.count()}")

    def handleClicked(self):
        self.provid_clt = self.currentItem()
        self.provid_clt_id = self.provid_clt.provid_clt_id
        logger.debug(f"Élément sélectionné - ID: {self.provid_clt_id}")

        if isinstance(self.provid_clt_id, int):
            self.parent.sub_btt.setEnabled(True)
            self.parent.add_btt.setEnabled(True)
            logger.debug("Boutons activés")
        else:
            if Config.DEVISE_PEP_PROV:
                logger.debug("Configuration DEVISE_PEP_PROV active")
                return
            self.parent.sub_btt.setEnabled(False)
            self.parent.add_btt.setEnabled(False)
            logger.debug("Boutons désactivés")
        self.parent.table.refresh_(provid_clt_id=self.provid_clt_id)


class ProviderOrClientQListWidgetItem(QListWidgetItem):
    def __init__(self, provid_clt):
        logger.debug("Initialisation d'un élément de la liste")
        super(ProviderOrClientQListWidgetItem, self).__init__()

        self.provid_clt = provid_clt
        self.setSizeHint(QSize(0, 30))
        icon = QIcon()

        if not isinstance(self.provid_clt, str):
            icon_path = "{}.png".format(
                Config.img_media + "debt"
                if self.provid_clt.is_indebted()
                else Config.img_cmedia + "user_active"
            )
            logger.debug(f"Chargement de l'icône: {icon_path}")
            icon.addPixmap(QPixmap(icon_path), QIcon.Normal, QIcon.Off)

        self.setIcon(icon)
        self.init_text()

    def init_text(self):
        try:
            self.setText(self.provid_clt.name)
            logger.debug(f"Texte défini: {self.provid_clt.name}")
        except AttributeError:
            font = QFont()
            font.setBold(True)
            self.setFont(font)
            self.setTextAlignment(Qt.AlignCenter)

            if not Config.DEVISE_PEP_PROV:
                self.setText("Tous")
                logger.debug("Texte par défaut défini: 'Tous'")

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
        self.parent = parent

        self.sorter = False
        self.stretch_columns = [0, 1, 2, 3, 4]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r"}
        self.ecart = -15
        self.display_vheaders = False

    def refresh_(self, provid_clt_id=None, search=None):
        """ """

        self.totals_debit = 0
        self.totals_credit = 0
        self.balance_tt = 0

        self._reset()
        self.set_data_for(provid_clt_id=provid_clt_id, search=search)
        self.refresh()

        self.parent.label_balance.setText(
            self.parent.display_balance(device_amount(self.balance_tt, provid_clt_id))
        )
        self.hideColumn(len(self.hheaders) - 1)

    def set_data_for(self, provid_clt_id=None, search=None):
        self.provid_clt_id = provid_clt_id
        qs = (
            Payment.select().where(Payment.status == False).order_by(Payment.date.asc())
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
            for prov in ProviderOrClient.select().where(
                ProviderOrClient.type_ == ProviderOrClient.CLT
            ):
                self.remaining += prov.last_remaining()
            msg = self.provider_clt
        self.parent.label_owner.setText(msg)

        self.data = [
            (pay.date, pay.libelle, pay.debit, pay.credit, pay.balance, pay.id)
            for pay in qs.iterator()
        ]

    def extend_rows(self):
        nb_rows = self.rowCount()
        self.setRowCount(nb_rows + 1)
        self.setSpan(nb_rows + 2, 2, 2, 4)
        self.totals_debit = 0
        self.totals_credit = 0
        self.balance_tt = 0
        cp = 0
        for row_num in range(0, self.data.__len__()):
            mtt_debit = is_float(str(self.item(row_num, 2).text()))
            mtt_credit = is_float(str(self.item(row_num, 3).text()))
            self.totals_debit += mtt_debit
            self.totals_credit += mtt_credit
            cp += 1

        self.balance_tt = self.totals_credit - self.totals_debit

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
        title = "Movements"
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
            "format_money": [
                "C:C",
                "D:D",
                "E:E",
            ],
            "exclude_row": len(self.data) - 1,
            "date": self.parent.now,
            "others": [
                ("A7", "C7", "Compte : {}".format(self.provider_clt)),
                (
                    "A8",
                    "B8",
                    "Solde au {}: {}".format(
                        self.parent.now,
                        device_amount(self.balance_tt, self.provider_clt.id),
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
        self.parent = parent

        self.sorter = False
        self.stretch_columns = [0, 1, 2, 3, 4, 5]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r", 5: "r"}
        self.display_vheaders = False

    def refresh_(self, provid_clt_id=None, search=None):
        """ """

        self.totals_debit = 0
        self.totals_credit = 0
        self.balance_tt = 0
        self._reset()
        self.set_data_for(provid_clt_id=provid_clt_id, search=search)
        self.refresh()

        self.parent.label_balance.setText(
            self.parent.display_balance(device_amount(self.balance_tt, provid_clt_id))
        )
        self.hideColumn(len(self.hheaders) - 1)

    def set_data_for(self, provid_clt_id=None, search=None):
        self.provid_clt_id = provid_clt_id
        qs = (
            Payment.select().where(Payment.status == False).order_by(Payment.date.asc())
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
            for prov in ProviderOrClient.select().where(
                ProviderOrClient.type_ == ProviderOrClient.CLT
            ):
                self.remaining += prov.last_remaining()
            msg = self.provider_clt
        self.parent.label_owner.setText(msg)

        self.data = [
            (
                pay.date,
                pay.libelle,
                pay.weight,
                pay.debit,
                pay.credit,
                pay.balance,
                pay.id,
            )
            for pay in qs.iterator()
        ]

    def extend_rows(self):
        nb_rows = self.rowCount()
        self.setRowCount(nb_rows + 1)
        self.setSpan(nb_rows + 2, 2, 2, 4)
        self.totals_weight = 0
        self.totals_debit = 0
        self.totals_credit = 0
        self.balance_tt = 0
        cp = 0
        for row_num in range(0, self.data.__len__()):
            mtt_weight = is_float(str(self.item(row_num, 2).text()))
            mtt_debit = is_float(str(self.item(row_num, 3).text()))
            mtt_credit = is_float(str(self.item(row_num, 4).text()))
            self.totals_weight += mtt_weight
            self.totals_debit += mtt_debit
            self.totals_credit += mtt_credit
            cp += 1

        self.balance_tt = self.totals_credit - self.totals_debit

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
        title = "Movements"
        return {
            "file_name": title,
            "headers": self.hheaders[:-1],
            "data": self.data,
            "extend_rows": [
                (1, self.label_mov_tt),
                (2, device_amount(self.totals_weight, dvs="F", aftergam=3)),
                (3, self.totals_debit),
                (4, self.totals_credit),
            ],
            "sheet": title,
            "widths": self.stretch_columns,
            "format_money": [
                "C:C",
                "D:D",
                "E:E",
            ],
            "exclude_row": len(self.data) - 1,
            "date": self.parent.now,
            "others": [
                ("A5", "C7", "Compte : {}".format(self.provider_clt)),
                (
                    "A6",
                    "B6",
                    "Solde au {}: {}".format(
                        self.parent.now,
                        device_amount(self.balance_tt, self.provider_clt),
                    ),
                ),
            ],
        }
