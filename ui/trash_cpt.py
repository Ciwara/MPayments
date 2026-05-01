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
from Common.ui.util import format_number_table_no_round, is_float
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
        # Affichage du solde masqué par défaut (toggle Afficher/Masquer)
        self._show_balance_amounts = False

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
        self.search_count_label.setStyleSheet("color: palette(window-text); font-size: 11px;")

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
        title_left.setStyleSheet("color: palette(window-text);")
        left_layout.addWidget(title_left)
        type_label = QLabel("Afficher :")
        type_label.setStyleSheet("color: palette(window-text); font-size: 11px;")
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
        # Pied de page solde + toggle
        self.toggle_balance_btt = Button("Afficher")
        self.toggle_balance_btt.clicked.connect(self.toggle_balance_visibility)
        balance_footer = QFrame()
        balance_footer_layout = QHBoxLayout()
        balance_footer_layout.setContentsMargins(0, 0, 0, 0)
        balance_footer_layout.addWidget(self.toggle_balance_btt)
        balance_footer_layout.addWidget(self.label_balance, 1)
        balance_footer.setLayout(balance_footer_layout)
        self.splt_clt.addWidget(balance_footer)
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
        # Afficher d’emblée toutes les opérations en corbeille (sans sélection de compte).
        self.table.refresh_(provid_clt_id=None)
        logger.debug("Mise en page Poubelle configurée")

    def toggle_balance_visibility(self):
        self._show_balance_amounts = not self._show_balance_amounts
        self.toggle_balance_btt.setText("Masquer" if self._show_balance_amounts else "Afficher")
        provid_clt_id = getattr(self.table_provid_clt, "provid_clt_id", None)
        self.table.refresh_(provid_clt_id=provid_clt_id)

    def format_balance_text(self, amount_text: str) -> str:
        return amount_text if self._show_balance_amounts else "••••"

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
        item = self.table_provid_clt.currentItem()
        if not isinstance(item, ProviderOrClientQListWidgetItem):
            return
        if isinstance(item.provid_clt, str):
            return
        provid_clt_id = getattr(self.table_provid_clt, "provid_clt_id", None)
        if not isinstance(provid_clt_id, int):
            return
        try:
            account = ProviderOrClient.get(id=provid_clt_id)
            mode = getattr(item, "list_entry_mode", "account_trash")
            if mode == "ops_trash":
                n = (
                    Payment.select()
                    .where(
                        Payment.provider_clt == account,
                        Payment.deleted == True,
                    )
                    .count()
                )
                msg = (
                    f"Supprimer définitivement les {n} opération(s) en corbeille "
                    f"pour le compte « {account.name} » ?\n\n"
                    "Cette action est irréversible."
                )
            else:
                msg = (
                    f"Supprimer définitivement le compte « {account.name} » ?\n\n"
                    "Cette action est irréversible (compte et paiements associés)."
                )
            reply = QMessageBox.question(
                self,
                "⚠️ Suppression définitive",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.suppression()
        except Exception as e:
            logger.error(f"Erreur: {e}")
            self.parent.Notify(f"❌ Erreur : {str(e)}", "error")

    def suppression(self):
        item = self.table_provid_clt.currentItem()
        if not isinstance(item, ProviderOrClientQListWidgetItem):
            return
        provid_clt_id = getattr(self.table_provid_clt, "provid_clt_id", None)
        if not isinstance(provid_clt_id, int):
            return
        mode = getattr(item, "list_entry_mode", "account_trash")
        logger.debug(
            "Suppression définitive compte ID: %s mode=%s", provid_clt_id, mode
        )
        try:
            account = ProviderOrClient.get(id=provid_clt_id)
            if mode == "ops_trash":
                for p in (
                    Payment.select()
                    .where(
                        Payment.provider_clt == account,
                        Payment.deleted == True,
                    )
                    .order_by(Payment.date.asc(), Payment.id.asc())
                ):
                    p.deletes_data()
                self.parent.Notify(
                    "✅ Opérations en corbeille supprimées définitivement", "success"
                )
            else:
                account.delete_permanate()
                self.parent.Notify("✅ Compte supprimé définitivement", "success")
            self.table_provid_clt.refresh_(
                provid_clt=self.search_field.text().strip() or None
            )
            self.update_accounts_count()
            self.table.refresh_(provid_clt_id=provid_clt_id)
        except Exception as e:
            logger.error(f"Erreur lors de la suppression définitive: {str(e)}")
            self.parent.Notify(f"❌ Erreur : {str(e)}", "error")

    def restoration(self):
        item = self.table_provid_clt.currentItem()
        if not isinstance(item, ProviderOrClientQListWidgetItem):
            return
        provid_clt_id = getattr(self.table_provid_clt, "provid_clt_id", None)
        if not isinstance(provid_clt_id, int):
            return
        mode = getattr(item, "list_entry_mode", "account_trash")
        logger.debug("Restauration compte ID: %s mode=%s", provid_clt_id, mode)
        try:
            account = ProviderOrClient.get(id=provid_clt_id)
            if mode == "ops_trash":
                for p in (
                    Payment.select()
                    .where(
                        Payment.provider_clt == account,
                        Payment.deleted == True,
                    )
                    .order_by(Payment.date.asc(), Payment.id.asc())
                ):
                    p.restore_from_trash()
                self.parent.Notify(
                    f"♻️ Opérations restaurées pour « {account.name} »", "success"
                )
            else:
                account.restore_data()
                self.parent.Notify(f"♻️ Compte « {account.name} » restauré", "success")
            self.table_provid_clt.refresh_(
                provid_clt=self.search_field.text().strip() or None
            )
            self.update_accounts_count()
            self.table.refresh_(provid_clt_id=provid_clt_id)
        except Exception as e:
            logger.error(f"Erreur lors de la restauration: {str(e)}")
            self.parent.Notify(f"❌ Erreur : {str(e)}", "error")

    def display_balance(self, amount_text):
        logger.debug(f"Affichage du solde avec style moderne: {amount_text}")
        amount_text = self.format_balance_text(amount_text)
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

        def _apply_type(q):
            if type_filter == "Clients":
                return q.where(ProviderOrClient.type_ == ProviderOrClient.CLT)
            if type_filter == "Fournisseurs":
                return q.where(ProviderOrClient.type_ == ProviderOrClient.FSEUR)
            return q

        qs_deleted = _apply_type(
            ProviderOrClient.select().where(ProviderOrClient.deleted == True)
        )

        pclt_ids = [
            row.provider_clt_id
            for row in Payment.select(Payment.provider_clt)
            .where(Payment.deleted == True)
            .distinct()
        ]
        if pclt_ids:
            qs_ops = _apply_type(
                ProviderOrClient.select().where(
                    ProviderOrClient.deleted == False,
                    ProviderOrClient.id.in_(pclt_ids),
                )
            )
        else:
            qs_ops = None

        if provid_clt:
            search = str(provid_clt).strip()
            if search:
                qs_deleted = qs_deleted.where(ProviderOrClient.name.contains(search))
                if qs_ops is not None:
                    qs_ops = qs_ops.where(ProviderOrClient.name.contains(search))

        for p in qs_deleted.order_by(ProviderOrClient.name):
            self.addItem(ProviderOrClientQListWidgetItem(p, "account_trash"))
        if qs_ops is not None:
            for p in qs_ops.order_by(ProviderOrClient.name):
                self.addItem(ProviderOrClientQListWidgetItem(p, "ops_trash"))

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
    """list_entry_mode: account_trash = compte en corbeille, ops_trash = compte actif avec opérations supprimées."""

    def __init__(self, provid_clt, list_entry_mode="account_trash"):
        logger.debug("Initialisation d'un élément de la liste avec style moderne")
        super(ProviderOrClientQListWidgetItem, self).__init__()

        self.provid_clt = provid_clt
        self.list_entry_mode = list_entry_mode
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
            if getattr(self, "list_entry_mode", "account_trash") == "ops_trash":
                n = (
                    Payment.select()
                    .where(
                        Payment.provider_clt == self.provid_clt,
                        Payment.deleted == True,
                    )
                    .count()
                )
                self.setText(
                    f"📋 {self.provid_clt.name} — {n} opération(s) en corbeille"
                )
                return
            prefix = "⚠️ " if self.provid_clt.is_indebted() else "👤 "
            self.setText(f"{prefix}{self.provid_clt.name}")
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
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._popup_row)

    def _format_for_table(self, value):
        from decimal import Decimal

        if isinstance(value, float):
            return format_number_table_no_round(value)
        if isinstance(value, Decimal):
            return format_number_table_no_round(value)
        return super()._format_for_table(value)

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
            .order_by(Payment.date.asc(), Payment.id.asc())
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
            solde = self.parent.format_balance_text(solde)
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

    def _main_window(self):
        return getattr(self.parent, "parent", None)

    def _popup_row(self, pos):
        idx = self.indexAt(pos)
        if not idx.isValid():
            return
        row = idx.row()
        if row < 0 or row >= len(self.data):
            return
        menu = QMenu()
        act_restore = menu.addAction("♻️ Restaurer cette opération")
        act_erase = menu.addAction("🗑️ Supprimer définitivement…")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen is None:
            return
        mw = self._main_window()
        try:
            payment = Payment.get(id=self.data[row][-1])
            if chosen == act_restore:
                payment.restore_from_trash()
                if mw:
                    mw.Notify("✅ Opération restaurée", "success")
            elif chosen == act_erase:
                reply = QMessageBox.question(
                    self,
                    "Suppression définitive",
                    "Supprimer définitivement cette opération ? Cette action est irréversible.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    payment.deletes_data()
                    if mw:
                        mw.Notify("✅ Opération supprimée définitivement", "success")
        except Exception as e:
            logger.exception("Poubelle menu opération: %s", e)
            if mw:
                mw.Notify(f"❌ Erreur : {e}", "error")
        if hasattr(self.parent, "table_provid_clt"):
            self.parent.table_provid_clt.refresh_(
                provid_clt=self.parent.search_field.text().strip() or None
            )
        if hasattr(self.parent, "update_accounts_count"):
            self.parent.update_accounts_count()
        pid = self.provid_clt_id if isinstance(self.provid_clt_id, int) else None
        self.refresh_(provid_clt_id=pid)

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
            TotalsWidget(
                device_amount(
                    self.totals_debit, self.provid_clt_id, preserve_decimals=True
                )
            ),
        )
        self.setItem(
            nb_rows,
            3,
            TotalsWidget(
                device_amount(
                    self.totals_credit, self.provid_clt_id, preserve_decimals=True
                )
            ),
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
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._popup_row)

    def _item_for_data(self, row, column, data, context=None):
        from decimal import Decimal

        if isinstance(data, (int, float, Decimal)) and column in (2, 3, 4, 5):
            text = format_number_table_no_round(data)
            if column in self.align_map:
                widget_cls = self.widget_from_align(self.align_map[column])
            else:
                from Common.ui.table import FlexibleReadOnlyWidget

                widget_cls = FlexibleReadOnlyWidget
            return widget_cls(text)
        return super()._item_for_data(row, column, data, context)

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
            .order_by(Payment.date.asc(), Payment.id.asc())
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

    def _main_window(self):
        return getattr(self.parent, "parent", None)

    def _popup_row(self, pos):
        idx = self.indexAt(pos)
        if not idx.isValid():
            return
        row = idx.row()
        if row < 0 or row >= len(self.data):
            return
        menu = QMenu()
        act_restore = menu.addAction("♻️ Restaurer cette opération")
        act_erase = menu.addAction("🗑️ Supprimer définitivement…")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen is None:
            return
        mw = self._main_window()
        try:
            payment = Payment.get(id=self.data[row][-1])
            if chosen == act_restore:
                payment.restore_from_trash()
                if mw:
                    mw.Notify("✅ Opération restaurée", "success")
            elif chosen == act_erase:
                reply = QMessageBox.question(
                    self,
                    "Suppression définitive",
                    "Supprimer définitivement cette opération ? Cette action est irréversible.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    payment.deletes_data()
                    if mw:
                        mw.Notify("✅ Opération supprimée définitivement", "success")
        except Exception as e:
            logger.exception("Poubelle menu opération (CISS): %s", e)
            if mw:
                mw.Notify(f"❌ Erreur : {e}", "error")
        if hasattr(self.parent, "table_provid_clt"):
            self.parent.table_provid_clt.refresh_(
                provid_clt=self.parent.search_field.text().strip() or None
            )
        if hasattr(self.parent, "update_accounts_count"):
            self.parent.update_accounts_count()
        pid = self.provid_clt_id if isinstance(self.provid_clt_id, int) else None
        self.refresh_(provid_clt_id=pid)

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
            TotalsWidget(
                device_amount(self.totals_weight, dvs="Kg", preserve_decimals=True)
            ),
        )
        self.setItem(
            nb_rows,
            3,
            TotalsWidget(device_amount(self.totals_debit, preserve_decimals=True)),
        )
        self.setItem(
            nb_rows,
            4,
            TotalsWidget(device_amount(self.totals_credit, preserve_decimals=True)),
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
                (2, device_amount(self.totals_weight, dvs="Kg", preserve_decimals=True)),
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
