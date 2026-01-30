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
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QSplitter,
    QComboBox,
    QLabel,
    QMessageBox,
    QFrame,
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

        self.title = "🗑️ Mouvements supprimés"
        self.now = datetime.now().strftime(Config.DATEFORMAT)
        logger.debug(f"Date actuelle: {self.now}")

        # Labels modernes avec style amélioré
        self.label_balance = FormLabel("")
        
        self.label_owner = FormLabel("")

        if Config.CISS:
            logger.debug("Configuration CISS activée")
            self.table = RapportCISSTableWidget(parent=self)
        else:
            logger.debug("Configuration CISS désactivée")
            self.table = RapportTableWidget(parent=self)

        # Filtre par type (Clients / Fournisseurs / Tous)
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems(["Clients", "Fournisseurs", "Tous"])
        self.type_filter_combo.currentTextChanged.connect(self._on_type_filter_changed)

        # Champ de recherche
        self.search_field = LineEdit()
        self.search_field.setPlaceholderText("Rechercher par nom...")
        self.search_field.textChanged.connect(self.search)

        self.search_count_label = QLabel("0 compte(s) en corbeille")
        self.search_count_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")

        # Boutons d'action
        self.button = Button("🔄 Actualiser")
        self.button.clicked.connect(self.refresh_period)

        self.add_btt = Button("🗑️ Supprimer définitivement")
        self.add_btt.setEnabled(False)
        self.add_btt.clicked.connect(self._confirm_suppression)
        self.add_btt.setMaximumHeight(90)

        self.sub_btt = Button("♻️ Restaurer")
        self.sub_btt.setEnabled(False)
        self.sub_btt.clicked.connect(self.restoration)
        self.sub_btt.setMaximumHeight(90)

        editbox = QGridLayout()
        editbox.addWidget(self.label_owner, 0, 0)
        editbox.setColumnStretch(0, 2)
        editbox.addWidget(self.sub_btt, 0, 3)
        editbox.addWidget(self.add_btt, 0, 4)
        editbox.setSpacing(12)
        editbox.setContentsMargins(16, 8, 16, 8)

        self.table_provid_clt = ProviderOrClientTableWidget(parent=self)

        # Panneau gauche : filtre, recherche, liste
        left_panel = QFrame()
        left_panel.setObjectName("trash_panel")
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(0, 0, 0, 0)
        title_left = QLabel("🗑️ Comptes en corbeille")
        title_left.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_left.setStyleSheet(f"color: {COLORS['text_primary']};")
        left_layout.addWidget(title_left)
        type_label = QLabel("Afficher :")
        type_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        left_layout.addWidget(type_label)
        left_layout.addWidget(self.type_filter_combo)
        left_layout.addWidget(self.search_field)
        left_layout.addWidget(self.search_count_label)
        left_layout.addWidget(self.table_provid_clt)
        left_panel.setLayout(left_layout)

        self.splt_add = QSplitter(Qt.Orientation.Horizontal)
        self.splt_add.setLayout(editbox)

        self.splitter_left = QSplitter(Qt.Orientation.Vertical)
        self.splitter_left.addWidget(left_panel)

        self.splt_clt = QSplitter(Qt.Orientation.Vertical)
        self.splt_clt.addWidget(self.splt_add)
        self.splt_clt.addWidget(self.table)
        self.splt_clt.addWidget(self.label_balance)
        logger.debug("Splitters configurés")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.splitter_left)
        splitter.addWidget(self.splt_clt)

        # Proportions par défaut pour une meilleure répartition
        splitter.setSizes([250, 750])

        hbox = QHBoxLayout(self)
        hbox.setContentsMargins(16, 16, 16, 16)
        hbox.addWidget(splitter)
        self.setLayout(hbox)

        self.update_accounts_count()
        logger.debug("Mise en page Poubelle configurée")

    def refresh_period(self):
        logger.debug("Rafraîchissement de la période")
        self.table.refresh_()
        self.update_accounts_count()

    def _on_type_filter_changed(self, _text):
        self.table_provid_clt.refresh_(provid_clt=self.search_field.text().strip() or None)
        self.update_accounts_count()

    def update_accounts_count(self):
        table = getattr(self, "table_provid_clt", None)
        label = getattr(self, "search_count_label", None)
        if table is None or label is None:
            return
        n = max(0, table.count() - 1)
        label.setText(f"{n} compte(s) en corbeille")

    def search(self):
        search_text = self.search_field.text()
        self.table_provid_clt.refresh_(provid_clt=search_text.strip() or None)
        self.update_accounts_count()

    def _confirm_suppression(self):
        """Demande confirmation avant suppression définitive."""
        provid_clt_id = getattr(self.table_provid_clt, "provid_clt_id", None)
        if not isinstance(provid_clt_id, int):
            return
        try:
            account = ProviderOrClient.get(id=provid_clt_id)
            reply = QMessageBox.question(
                self,
                "⚠️ Suppression définitive",
                f"Supprimer définitivement le compte « {account.name} » ?\n\n"
                "Cette action est irréversible (compte et paiements associés).",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.suppression()
        except Exception as e:
            logger.error(f"Erreur: {e}")
            self.parent.Notify(f"❌ Erreur : {str(e)}", "error")

    def suppression(self):
        provid_clt_id = getattr(self.table_provid_clt, "provid_clt_id", None)
        if not isinstance(provid_clt_id, int):
            return
        logger.debug(f"Suppression définitive du compte ID: {provid_clt_id}")
        try:
            ProviderOrClient.get(id=provid_clt_id).delete_permanate()
            self.table_provid_clt.refresh_(provid_clt=self.search_field.text().strip() or None)
            self.update_accounts_count()
            self.table.refresh_()
            self.parent.Notify("✅ Compte supprimé définitivement", "success")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression définitive: {str(e)}")
            self.parent.Notify(f"❌ Erreur : {str(e)}", "error")

    def restoration(self):
        provid_clt_id = getattr(self.table_provid_clt, "provid_clt_id", None)
        if not isinstance(provid_clt_id, int):
            return
        logger.debug(f"Restauration du compte ID: {provid_clt_id}")
        try:
            account = ProviderOrClient.get(id=provid_clt_id)
            account.restore_data()
            self.table_provid_clt.refresh_(provid_clt=self.search_field.text().strip() or None)
            self.update_accounts_count()
            self.table.refresh_()
            self.parent.Notify(f"♻️ Compte « {account.name} » restauré", "success")
        except Exception as e:
            logger.error(f"Erreur lors de la restauration: {str(e)}")
            self.parent.Notify(f"❌ Erreur : {str(e)}", "error")

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

    """Affiche la liste des comptes (clients/fournisseurs) en corbeille."""

    def __init__(self, parent, *args, **kwargs):
        super(ProviderOrClientTableWidget, self).__init__(parent)
        self.parent = parent
        self.setAutoScroll(True)
        self.itemSelectionChanged.connect(self.handleClicked)
        self.itemDoubleClicked.connect(self._on_double_click)
        self.refresh_()

    def _on_double_click(self, item):
        """Double-clic : restaurer le compte."""
        if not isinstance(item, ProviderOrClientQListWidgetItem) or isinstance(item.provid_clt, str):
            return
        self.parent.restoration()

    def refresh_(self, provid_clt=None):
        """Rafraîchir la liste des comptes en corbeille (deleted=True)."""
        self.clear()
        self.addItem(ProviderOrClientQListWidgetItem(ALL_CONTACTS))

        type_filter = "Clients"
        if hasattr(self.parent, "type_filter_combo"):
            type_filter = self.parent.type_filter_combo.currentText()

        qs = ProviderOrClient.select().where(ProviderOrClient.deleted == True)
        if type_filter == "Clients":
            qs = qs.where(ProviderOrClient.type_ == ProviderOrClient.CLT)
        elif type_filter == "Fournisseurs":
            qs = qs.where(ProviderOrClient.type_ == ProviderOrClient.FSEUR)

        if provid_clt:
            search = str(provid_clt).strip()
            if search:
                qs = qs.where(ProviderOrClient.name.contains(search))
        for p in qs.order_by(ProviderOrClient.name):
            self.addItem(ProviderOrClientQListWidgetItem(p))

        if hasattr(self.parent, "update_accounts_count"):
            self.parent.update_accounts_count()

    def handleClicked(self):
        item = self.currentItem()
        if item is None:
            return
        self.provid_clt = item
        self.provid_clt_id = item.provid_clt_id

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
            icon.addPixmap(QPixmap(icon_path), QIcon.Mode.Normal, QIcon.State.Off)

        self.setIcon(icon)
        self.init_text()

    def init_text(self):
        try:
            solde = self.provid_clt.last_remaining()
            montant = device_amount(solde, self.provid_clt)
            prefix = "⚠️ " if self.provid_clt.is_indebted() else "👤 "
            self.setText(f"{prefix}{self.provid_clt.name} — {montant}")
        except AttributeError:
            font = QFont()
            font.setBold(True)
            font.setPointSize(13)
            self.setFont(font)
            self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not Config.DEVISE_PEP_PROV:
                self.setText("📋 Tous les comptes")

    @property
    def provid_clt_id(self):
        try:
            return self.provid_clt.id
        except AttributeError:
            return self.provid_clt


class RapportTableWidget(FTableWidget):
    def __init__(self, parent, *args, **kwargs):
        FTableWidget.__init__(self, parent=parent, *args, **kwargs)

        self.hheaders = ["📅 Date", "📝 Libellé", "💸 Débit", "💰 Crédit", "📊 Solde", ""]
        self.parent = parent

        self.sorter = False
        self.stretch_columns = [0, 1, 2, 3, 4]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r"}
        self.ecart = -15
        self.display_vheaders = False
        self.provider_clt = None

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
            Payment.select()
            .where(Payment.deleted == True)
            .order_by(Payment.date.asc())
        )

        self.remaining = 0
        if isinstance(provid_clt_id, int):
            try:
                self.provider_clt = ProviderOrClient.get(id=provid_clt_id)
            except ProviderOrClient.DoesNotExist:
                self.provider_clt = "Tous"
                self.provid_clt_id = None
                self.data = []
                self.parent.label_owner.setText("<h3>Compte introuvable (supprimé définitivement ?)</h3>")
                if hasattr(self.parent, "table_provid_clt"):
                    self.parent.table_provid_clt.refresh_(
                        provid_clt=self.parent.search_field.text().strip() or None
                    )
                return
            qs = qs.where(Payment.provider_clt == self.provider_clt)
            solde = device_amount(self.provider_clt.last_remaining(), self.provider_clt)
            tel = self.provider_clt.phone or "—"
            msg = f"<h3>Compte : {self.provider_clt.name} — Solde : {solde}</h3><h4>Tel : {tel}</h4>"
        else:
            self.provider_clt = "Tous"
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
            "format_money": [
                "C:C",
                "D:D",
                "E:E",
            ],
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
        self.parent = parent

        self.sorter = False
        self.stretch_columns = [0, 1, 2, 3, 4, 5]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r", 5: "r"}
        self.display_vheaders = False
        self.provider_clt = None

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
            Payment.select()
            .where(Payment.deleted == True)
            .order_by(Payment.date.asc())
        )

        self.remaining = 0
        if isinstance(provid_clt_id, int):
            try:
                self.provider_clt = ProviderOrClient.get(id=provid_clt_id)
            except ProviderOrClient.DoesNotExist:
                self.provider_clt = "Tous"
                self.provid_clt_id = None
                self.data = []
                self.parent.label_owner.setText("<h3>Compte introuvable (supprimé définitivement ?)</h3>")
                if hasattr(self.parent, "table_provid_clt"):
                    self.parent.table_provid_clt.refresh_(
                        provid_clt=self.parent.search_field.text().strip() or None
                    )
                return
            qs = qs.where(Payment.provider_clt == self.provider_clt)
            solde = device_amount(self.provider_clt.last_remaining(), self.provider_clt)
            tel = self.provider_clt.phone or "—"
            msg = f"<h3>Compte : {self.provider_clt.name} — Solde : {solde}</h3><h4>Tel : {tel}</h4>"
        else:
            self.provider_clt = "Tous"
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
        client_name = self.provider_clt.name if hasattr(self.provider_clt, 'name') else str(self.provider_clt)
        client_id = getattr(self.provider_clt, 'id', None) if hasattr(self.provider_clt, 'id') else None
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
                ("A5", "C7", "Compte : {}".format(client_name)),
                (
                    "A6",
                    "B6",
                    "Solde au {}: {}".format(
                        self.parent.now,
                        device_amount(self.balance_tt, client_id),
                    ),
                ),
            ],
        }
