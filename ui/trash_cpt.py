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

ALL_CONTACTS = "TOUS"


class DebtsTrashViewWidget(FWidget):

    """Affiche la page de gestion de la corbeille avec design moderne"""

    def __init__(self, parent=0, *args, **kwargs):
        logger.debug("Initialisation de DebtsTrashViewWidget avec design moderne")
        super(DebtsTrashViewWidget, self).__init__(parent=parent, *args, **kwargs)
        self.parent = parent
        self.parentWidget().setWindowTitle(
            Config.APP_NAME + " 🗑️ Gestion des éléments supprimés"
        )
        logger.debug("Titre de la fenêtre défini avec style moderne")

        # Style moderne pour le widget principal
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['background']};
                font-family: "Segoe UI", "Arial", sans-serif;
                font-size: 12px;
                color: {COLORS['text_primary']};
            }}
            QLabel {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                font-weight: 500;
                font-size: 12px;
                padding: 8px 12px;
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
            }}
            QSplitter {{
                background-color: {COLORS['background']};
            }}
            QSplitter::handle {{
                background-color: {COLORS['border']};
                width: 3px;
                height: 3px;
            }}
            QSplitter::handle:hover {{
                background-color: {COLORS['primary_light']};
            }}
        """)

        self.title = "🗑️ Mouvements supprimés"
        self.now = datetime.now().strftime(Config.DATEFORMAT)
        logger.debug(f"Date actuelle: {self.now}")

        # Labels modernes avec style amélioré
        self.label_balance = FormLabel("")
        self.label_balance.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['surface']};
                color: {COLORS['primary']};
                font-weight: 700;
                font-size: 14px;
                padding: 16px 20px;
                border-radius: 12px;
                border: 2px solid {COLORS['primary_light']};
                margin: 8px 0;
            }}
        """)
        
        self.label_owner = FormLabel("")
        self.label_owner.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['info_light']};
                color: white;
                font-weight: 600;
                font-size: 13px;
                padding: 12px 16px;
                border-radius: 8px;
                margin: 4px 0;
            }}
        """)

        if Config.CISS:
            logger.debug("Configuration CISS activée")
            self.table = RapportCISSTableWidget(parent=self)
        else:
            logger.debug("Configuration CISS désactivée")
            self.table = RapportTableWidget(parent=self)

        # Bouton de rafraîchissement moderne
        self.button = Button("🔄 Actualiser")
        self.button.clicked.connect(self.refresh_period)
        self.button.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 12px;
                min-height: 40px;
                margin: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info_light']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['info']};
            }}
        """)
        logger.debug("Bouton de rafraîchissement configuré avec style moderne")

        # Bouton de suppression définitive moderne
        self.add_btt = Button("🗑️ Supprimer définitivement")
        self.add_btt.setEnabled(False)
        self.add_btt.clicked.connect(self.suppression)
        self.add_btt.setMaximumHeight(90)
        self.add_btt.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['error']};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px 24px;
                font-weight: 700;
                font-size: 12px;
                min-width: 180px;
                min-height: 60px;
                margin: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['error_light']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['error']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['surface_variant']};
                color: {COLORS['text_secondary']};
            }}
        """)
        logger.debug("Bouton de suppression configuré avec style moderne")

        # Bouton de restauration moderne
        self.sub_btt = Button("♻️ Restaurer")
        self.sub_btt.setEnabled(False)
        self.sub_btt.clicked.connect(self.restoration)
        self.sub_btt.setMaximumHeight(90)
        self.sub_btt.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px 24px;
                font-weight: 700;
                font-size: 12px;
                min-width: 140px;
                min-height: 60px;
                margin: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_light']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['success']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['surface_variant']};
                color: {COLORS['text_secondary']};
            }}
        """)
        logger.debug("Bouton de restauration configuré avec style moderne")

        editbox = QGridLayout()
        editbox.addWidget(self.label_owner, 0, 0)
        editbox.setColumnStretch(0, 2)
        editbox.addWidget(self.sub_btt, 0, 3)
        editbox.addWidget(self.add_btt, 0, 4)
        editbox.setSpacing(12)
        editbox.setContentsMargins(16, 8, 16, 8)
        logger.debug("Mise en page principale configurée avec espacement moderne")

        self.table_provid_clt = ProviderOrClientTableWidget(parent=self)
        logger.debug("Table des fournisseurs/clients initialisée")

        # Champ de recherche moderne
        self.search_field = LineEdit()
        self.search_field.textChanged.connect(self.search)
        self.search_field.setPlaceholderText("🔍 Rechercher un compte...")
        self.search_field.setMaximumHeight(40)
        self.search_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 20px;
                padding: 12px 20px;
                font-size: 12px;
                color: {COLORS['text_primary']};
                font-weight: 500;
                min-height: 16px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
                background-color: {COLORS['surface']};
            }}
            QLineEdit:hover {{
                border-color: {COLORS['primary_light']};
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_secondary']};
                font-style: italic;
            }}
        """)
        logger.debug("Champ de recherche configuré avec style moderne")

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

        # Proportions par défaut pour une meilleure répartition
        splitter.setSizes([250, 750])

        hbox = QHBoxLayout(self)
        hbox.setContentsMargins(16, 16, 16, 16)
        hbox.addWidget(splitter)
        self.setLayout(hbox)
        logger.debug("Mise en page finale configurée avec design moderne")

    def refresh_period(self):
        logger.debug("Rafraîchissement de la période")
        self.table.refresh_()

    def search(self):
        search_text = self.search_field.text()
        logger.debug(f"Recherche avec le texte: {search_text}")
        self.table_provid_clt.refresh_(search_text)

    def suppression(self):
        provid_clt_id = self.table_provid_clt.provid_clt_id
        logger.debug(f"Suppression définitive du compte ID: {provid_clt_id}")
        try:
            ProviderOrClient.get(id=provid_clt_id).delete_permanate()
            self.table_provid_clt.refresh_()
            self.parent.Notify("✅ Compte supprimé définitivement avec succès", "success")
            logger.debug("Compte supprimé définitivement avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression définitive: {str(e)}")
            self.parent.Notify(f"❌ Erreur lors de la suppression: {str(e)}", "error")

    def restoration(self):
        provid_clt_id = self.table_provid_clt.provid_clt_id
        logger.debug(f"Restauration du compte ID: {provid_clt_id}")
        try:
            ProviderOrClient.get(id=provid_clt_id).restore_data()
            self.table_provid_clt.refresh_()
            self.parent.Notify("♻️ Compte restauré avec succès", "success")
            logger.debug("Compte restauré avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la restauration: {str(e)}")
            self.parent.Notify(f"❌ Erreur lors de la restauration: {str(e)}", "error")

    def display_balance(self, amount_text):
        logger.debug(f"Affichage du solde avec style moderne: {amount_text}")
        return f"""
            <div style="text-align: center; padding: 16px;">
                <h2 style="color: {COLORS['primary']}; margin: 0; font-weight: 700;">
                    💰 Solde du {self.now}
                </h2>
                <h1 style="color: {COLORS['success']}; margin: 8px 0; font-weight: 800; font-size: 24px;">
                    {amount_text}
                </h1>
            </div>
        """


class ProviderOrClientTableWidget(QListWidget):

    """Affiche la liste des fournisseurs/clients supprimés avec style moderne"""

    def __init__(self, parent, *args, **kwargs):
        logger.debug("Initialisation de ProviderOrClientTableWidget avec design moderne")
        super(ProviderOrClientTableWidget, self).__init__(parent)

        self.parent = parent
        self.setAutoScroll(True)
        self.itemSelectionChanged.connect(self.handleClicked)
        
        # Style moderne pour la liste
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                padding: 8px;
                font-size: 12px;
                color: {COLORS['text_primary']};
                selection-background-color: {COLORS['primary_light']};
                alternate-background-color: {COLORS['surface_variant']};
            }}
            QListWidget::item {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
                margin: 2px;
                font-weight: 500;
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['primary_light']};
                color: white;
                border-color: {COLORS['primary']};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['primary']};
                color: white;
                border-color: {COLORS['primary_dark']};
                font-weight: 600;
            }}
            QScrollBar:vertical {{
                background-color: {COLORS['surface_variant']};
                width: 12px;
                border-radius: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['border']};
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['primary_light']};
            }}
        """)
        
        self.refresh_()
        logger.debug("Table des fournisseurs/clients initialisée avec style moderne")

    def refresh_(self, provid_clt=None):
        """Rafraichir la liste des fournisseurs/clients supprimés"""
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
        logger.debug("Initialisation d'un élément de la liste avec style moderne")
        super(ProviderOrClientQListWidgetItem, self).__init__()

        self.provid_clt = provid_clt
        self.setSizeHint(QSize(0, 35))  # Hauteur légèrement augmentée pour le style moderne
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
            # Ajout d'une icône selon l'état
            if self.provid_clt.is_indebted():
                text = f"⚠️ {self.provid_clt.name}"
            else:
                text = f"👤 {self.provid_clt.name}"
            self.setText(text)
            logger.debug(f"Texte défini avec icône: {text}")
        except AttributeError:
            font = QFont()
            font.setBold(True)
            font.setPointSize(13)
            self.setFont(font)
            self.setTextAlignment(Qt.AlignCenter)

            if not Config.DEVISE_PEP_PROV:
                self.setText("📋 Tous les comptes")
                logger.debug("Texte par défaut défini avec style: 'Tous les comptes'")

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
