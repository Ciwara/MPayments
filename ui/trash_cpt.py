#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fadiga

import logging
from datetime import datetime

from Common.ui.common import Button, FormLabel, FWidget, LineEdit
from Common.ui.table import FTableWidget, TotalsWidget
from Common.ui.util import format_number_table_no_round, is_float
from configuration import Config
from data_helper import device_amount
from models import Activity, Payment, ProviderOrClient
from ui.debt_manager import format_movement_date
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont, QFontMetrics, QIcon, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)

ALL_CONTACTS = "TOUS"

# Filtres de contenu poubelle
MODE_ALL = "Tout"
MODE_ACCOUNTS = "Comptes supprimés"
MODE_OPS = "Opérations seules"


class DebtsTrashViewWidget(FWidget):
    """Corbeille : comptes et/ou opérations soft-deleted de l'activité courante."""

    def __init__(self, parent=0, *args, **kwargs):
        super(DebtsTrashViewWidget, self).__init__(parent=parent, *args, **kwargs)
        self.parent = parent
        self.parentWidget().setWindowTitle(f"{Config.APP_NAME} — Corbeille")
        self.now = datetime.now().strftime(Config.DATEFORMAT)
        self._show_balance_amounts = False

        if Config.CISS:
            self.table = RapportCISSTableWidget(parent=self)
        else:
            self.table = RapportTableWidget(parent=self)

        # —— En-tête ——
        header = QFrame()
        header.setObjectName("trashHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 4, 8)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title_label = QLabel("Corbeille")
        self.title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet("color: palette(mid); font-size: 12px;")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        header_layout.addLayout(title_col, 1)

        self.stats_accounts = self._badge("0 compte")
        self.stats_ops = self._badge("0 opération")
        header_layout.addWidget(self.stats_accounts)
        header_layout.addWidget(self.stats_ops)

        # —— Panneau gauche ——
        left_panel = QFrame()
        left_panel.setObjectName("trashLeft")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_title = QLabel("Éléments")
        left_title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        left_layout.addWidget(left_title)

        self.mode_filter_combo = QComboBox()
        self.mode_filter_combo.addItems([MODE_ALL, MODE_ACCOUNTS, MODE_OPS])
        self.mode_filter_combo.currentTextChanged.connect(self._on_filters_changed)
        left_layout.addWidget(self._field_label("Type d'élément"))
        left_layout.addWidget(self.mode_filter_combo)

        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems(["Clients", "Fournisseurs", "Tous"])
        self.type_filter_combo.currentTextChanged.connect(self._on_filters_changed)
        left_layout.addWidget(self._field_label("Type de compte"))
        left_layout.addWidget(self.type_filter_combo)

        self.search_field = LineEdit()
        self.search_field.setPlaceholderText("Rechercher un compte…")
        self.search_field.textChanged.connect(self.search)
        left_layout.addWidget(self.search_field)

        self.search_count_label = QLabel("0 élément(s)")
        self.search_count_label.setStyleSheet("color: palette(mid); font-size: 11px;")
        left_layout.addWidget(self.search_count_label)

        self.empty_hint = QLabel(
            "La corbeille est vide pour cette activité.\n"
            "Les comptes et opérations supprimés apparaîtront ici."
        )
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setWordWrap(True)
        self.empty_hint.setStyleSheet(
            "color: palette(mid); padding: 24px; font-size: 12px;"
        )

        # Actions créées avant la liste (refresh_ de la liste met à jour empty_btt)
        self.label_owner = FormLabel("")
        self.label_owner.setWordWrap(True)
        self.refresh_btt = Button("Actualiser")
        self.refresh_btt.clicked.connect(self.refresh_period)
        self.restore_btt = Button("Restaurer")
        self.restore_btt.setEnabled(False)
        self.restore_btt.setToolTip(
            "Restaurer le compte ou les opérations sélectionnés (Ctrl+R)"
        )
        self.restore_btt.clicked.connect(self.restoration)
        self.purge_btt = Button("Supprimer définitivement")
        self.purge_btt.setEnabled(False)
        self.purge_btt.setToolTip("Suppression irréversible (Suppr)")
        self.purge_btt.clicked.connect(self._confirm_suppression)
        self.empty_btt = Button("Vider la corbeille")
        self.empty_btt.setToolTip(
            "Supprimer définitivement tout le contenu de la corbeille (activité courante)"
        )
        self.empty_btt.clicked.connect(self._confirm_empty_trash)

        self.table_provid_clt = ProviderOrClientTableWidget(parent=self)
        left_layout.addWidget(self.table_provid_clt, 1)
        left_layout.addWidget(self.empty_hint)

        # —— Barre d'actions ——
        actions = QFrame()
        actions.setObjectName("trashActions")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        actions_layout.addWidget(self.label_owner, 1)
        for b in (self.refresh_btt, self.restore_btt, self.purge_btt, self.empty_btt):
            actions_layout.addWidget(b)

        # —— Pied solde ——
        self.toggle_balance_btt = Button("Afficher le solde")
        self.toggle_balance_btt.clicked.connect(self.toggle_balance_visibility)
        self.label_balance = FormLabel("")
        balance_footer = QFrame()
        balance_row = QHBoxLayout(balance_footer)
        balance_row.setContentsMargins(0, 4, 0, 0)
        balance_row.addWidget(self.toggle_balance_btt)
        balance_row.addWidget(self.label_balance, 1)

        # —— Zone droite ——
        right = QFrame()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        right_title = QLabel("Opérations en corbeille")
        right_title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        right_layout.addWidget(right_title)
        right_layout.addWidget(actions)
        right_layout.addWidget(self.table, 1)
        right_layout.addWidget(balance_footer)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 700])

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)
        root.addWidget(header)
        root.addWidget(splitter, 1)

        # Raccourcis
        QShortcut(QKeySequence("Ctrl+R"), self, self.restoration)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, self._confirm_suppression)
        QShortcut(QKeySequence("F5"), self, self.refresh_period)

        # Alias pour compatibilité code existant
        self.sub_btt = self.restore_btt
        self.add_btt = self.purge_btt
        self.button = self.refresh_btt

        self.refresh_header_stats()
        self.table.refresh_(provid_clt_id=None)
        self._update_empty_state()

    # —— UI helpers ——

    @staticmethod
    def _badge(text):
        lab = QLabel(text)
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lab.setStyleSheet(
            """
            QLabel {
                background: palette(midlight);
                color: palette(window-text);
                border-radius: 10px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            """
        )
        return lab

    @staticmethod
    def _field_label(text):
        lab = QLabel(text)
        lab.setStyleSheet("color: palette(mid); font-size: 11px;")
        return lab

    def current_activity(self):
        return Activity.get_current()

    def trash_stats(self):
        """Comptes / opérations soft-deleted pour l'activité courante."""
        activity = self.current_activity()
        qs_acc = ProviderOrClient.select().where(ProviderOrClient.deleted == True)
        if activity is not None:
            qs_acc = qs_acc.where(ProviderOrClient.activity == activity)
        n_accounts = qs_acc.count()

        qs_pay = Payment.select().where(Payment.deleted == True)
        if activity is not None:
            account_ids = [
                a.id
                for a in ProviderOrClient.select(ProviderOrClient.id).where(
                    ProviderOrClient.activity == activity
                )
            ]
            if account_ids:
                qs_pay = qs_pay.where(Payment.provider_clt.in_(account_ids))
            else:
                qs_pay = qs_pay.where(Payment.id == -1)
        n_ops = qs_pay.count()
        return n_accounts, n_ops

    def refresh_header_stats(self):
        activity = self.current_activity()
        name = getattr(activity, "name", None) or "—"
        if hasattr(self, "subtitle_label"):
            self.subtitle_label.setText(f"Activité « {name} » · éléments soft-deleted")
        n_acc, n_ops = self.trash_stats()
        if hasattr(self, "stats_accounts"):
            self.stats_accounts.setText(
                f"{n_acc} compte{'s' if n_acc != 1 else ''}"
            )
        if hasattr(self, "stats_ops"):
            self.stats_ops.setText(
                f"{n_ops} opération{'s' if n_ops != 1 else ''}"
            )
        if hasattr(self, "empty_btt"):
            self.empty_btt.setEnabled(n_acc > 0 or n_ops > 0)
        self._update_empty_state()

    def _update_empty_state(self):
        if not hasattr(self, "table_provid_clt"):
            return
        n = max(0, self.table_provid_clt.count() - 1)
        empty = n == 0
        if hasattr(self, "empty_hint"):
            self.empty_hint.setVisible(empty)
        if hasattr(self, "search_count_label"):
            self.search_count_label.setText(
                f"{n} élément{'s' if n != 1 else ''} listé{'s' if n != 1 else ''}"
            )

    def set_selection_banner(self, html_or_text):
        self.label_owner.setText(html_or_text)

    def set_action_buttons_enabled(self, enabled):
        self.restore_btt.setEnabled(bool(enabled))
        self.purge_btt.setEnabled(bool(enabled))

    # —— Actions ——

    def toggle_balance_visibility(self):
        self._show_balance_amounts = not self._show_balance_amounts
        self.toggle_balance_btt.setText(
            "Masquer le solde" if self._show_balance_amounts else "Afficher le solde"
        )
        provid_clt_id = getattr(self.table_provid_clt, "provid_clt_id", None)
        self.table.refresh_(provid_clt_id=provid_clt_id)

    def format_balance_text(self, amount_text: str) -> str:
        return amount_text if self._show_balance_amounts else "••••"

    def refresh_period(self):
        self.table_provid_clt.refresh_(
            provid_clt=self.search_field.text().strip() or None
        )
        pid = getattr(self.table_provid_clt, "provid_clt_id", None)
        self.table.refresh_(provid_clt_id=pid if isinstance(pid, int) else None)
        self.refresh_header_stats()

    def _on_filters_changed(self, _text=None):
        self.table_provid_clt.refresh_(
            provid_clt=self.search_field.text().strip() or None
        )
        self.refresh_header_stats()

    def update_accounts_count(self):
        self.refresh_header_stats()

    def search(self):
        self.table_provid_clt.refresh_(
            provid_clt=self.search_field.text().strip() or None
        )
        self._update_empty_state()

    def _selected_item(self):
        item = self.table_provid_clt.currentItem()
        if not isinstance(item, ProviderOrClientQListWidgetItem):
            return None
        if isinstance(item.provid_clt, str):
            return None
        return item

    def _confirm_suppression(self):
        item = self._selected_item()
        if item is None:
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
                    f"du compte « {account.name} » ?\n\n"
                    "Cette action est irréversible."
                )
            else:
                msg = (
                    f"Supprimer définitivement le compte « {account.name} » "
                    f"et toutes ses opérations ?\n\n"
                    "Cette action est irréversible."
                )
            reply = QMessageBox.question(
                self,
                "Suppression définitive",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.suppression()
        except Exception as e:
            logger.exception("confirm purge")
            self.parent.Notify(str(e), "error")

    def suppression(self):
        item = self._selected_item()
        if item is None:
            return
        provid_clt_id = getattr(self.table_provid_clt, "provid_clt_id", None)
        if not isinstance(provid_clt_id, int):
            return
        mode = getattr(item, "list_entry_mode", "account_trash")
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
                    f"Opérations en corbeille de « {account.name} » supprimées",
                    "success",
                )
            else:
                name = account.name
                account.delete_permanate()
                self.parent.Notify(f"Compte « {name} » supprimé définitivement", "success")
            self._after_mutate()
        except Exception as e:
            logger.exception("purge")
            self.parent.Notify(str(e), "error")

    def restoration(self):
        item = self._selected_item()
        if item is None:
            return
        provid_clt_id = getattr(self.table_provid_clt, "provid_clt_id", None)
        if not isinstance(provid_clt_id, int):
            return
        mode = getattr(item, "list_entry_mode", "account_trash")
        try:
            account = ProviderOrClient.get(id=provid_clt_id)
            if mode == "ops_trash":
                n = 0
                for p in (
                    Payment.select()
                    .where(
                        Payment.provider_clt == account,
                        Payment.deleted == True,
                    )
                    .order_by(Payment.date.asc(), Payment.id.asc())
                ):
                    p.restore_from_trash()
                    n += 1
                self.parent.Notify(
                    f"{n} opération(s) restaurée(s) pour « {account.name} »",
                    "success",
                )
            else:
                account.restore_data()
                self.parent.Notify(f"Compte « {account.name} » restauré", "success")
            self._after_mutate()
        except Exception as e:
            logger.exception("restore")
            self.parent.Notify(str(e), "error")

    def _confirm_empty_trash(self):
        n_acc, n_ops = self.trash_stats()
        if n_acc == 0 and n_ops == 0:
            self.parent.Notify("La corbeille est déjà vide", "info")
            return
        activity = self.current_activity()
        act_name = getattr(activity, "name", "") or "courante"
        reply = QMessageBox.warning(
            self,
            "Vider la corbeille",
            f"Vider entièrement la corbeille de l'activité « {act_name} » ?\n\n"
            f"• {n_acc} compte(s) supprimé(s)\n"
            f"• {n_ops} opération(s) en corbeille\n\n"
            "Tout sera effacé définitivement. Cette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._empty_trash()

    def _empty_trash(self):
        activity = self.current_activity()
        try:
            # 1) Opérations soft-deleted (tous comptes de l'activité)
            qs_pay = Payment.select().where(Payment.deleted == True)
            if activity is not None:
                account_ids = [
                    a.id
                    for a in ProviderOrClient.select(ProviderOrClient.id).where(
                        ProviderOrClient.activity == activity
                    )
                ]
                if account_ids:
                    qs_pay = qs_pay.where(Payment.provider_clt.in_(account_ids))
                else:
                    qs_pay = qs_pay.where(Payment.id == -1)
            for p in qs_pay:
                p.deletes_data()

            # 2) Comptes soft-deleted
            qs_acc = ProviderOrClient.select().where(ProviderOrClient.deleted == True)
            if activity is not None:
                qs_acc = qs_acc.where(ProviderOrClient.activity == activity)
            for account in qs_acc:
                account.delete_permanate()

            self.parent.Notify("Corbeille vidée", "success")
            self._after_mutate()
        except Exception as e:
            logger.exception("empty trash")
            self.parent.Notify(str(e), "error")

    def _after_mutate(self):
        self.table_provid_clt.refresh_(
            provid_clt=self.search_field.text().strip() or None
        )
        self.table_provid_clt.provid_clt_id = None
        self.set_action_buttons_enabled(False)
        self.table.refresh_(provid_clt_id=None)
        self.refresh_header_stats()

    def display_balance(self, amount_text):
        amount_text = self.format_balance_text(amount_text)
        return (
            f"<div style='padding: 4px 0;'>"
            f"<span style='color: palette(mid); font-size: 12px;'>Solde du {self.now}</span>"
            f"<div style='font-size: 18px; font-weight: 700; margin-top: 2px;'>{amount_text}</div>"
            f"</div>"
        )


class ProviderOrClientTableWidget(QListWidget):
    """Liste des éléments en corbeille (comptes et/ou opérations)."""

    def __init__(self, parent, *args, **kwargs):
        super(ProviderOrClientTableWidget, self).__init__(parent)
        self.parent = parent
        self.provid_clt_id = None
        self.setAutoScroll(True)
        self.setSpacing(2)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self.itemSelectionChanged.connect(self.handleClicked)
        self.itemDoubleClicked.connect(self._on_double_click)
        self.refresh_()

    def _on_double_click(self, item):
        if not isinstance(item, ProviderOrClientQListWidgetItem) or isinstance(
            item.provid_clt, str
        ):
            return
        self.parent.restoration()

    def _context_menu(self, pos):
        item = self.itemAt(pos)
        if not isinstance(item, ProviderOrClientQListWidgetItem):
            return
        if isinstance(item.provid_clt, str):
            return
        self.setCurrentItem(item)
        menu = QMenu(self)
        act_restore = menu.addAction("Restaurer")
        act_purge = menu.addAction("Supprimer définitivement…")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == act_restore:
            self.parent.restoration()
        elif chosen == act_purge:
            self.parent._confirm_suppression()

    def refresh_(self, provid_clt=None):
        self.clear()
        self.addItem(ProviderOrClientQListWidgetItem(ALL_CONTACTS))

        type_filter = "Clients"
        if hasattr(self.parent, "type_filter_combo"):
            type_filter = self.parent.type_filter_combo.currentText()
        mode_filter = MODE_ALL
        if hasattr(self.parent, "mode_filter_combo"):
            mode_filter = self.parent.mode_filter_combo.currentText()

        def _apply_type(q):
            if type_filter == "Clients":
                return q.where(ProviderOrClient.type_ == ProviderOrClient.CLT)
            if type_filter == "Fournisseurs":
                return q.where(ProviderOrClient.type_ == ProviderOrClient.FSEUR)
            return q

        activity = (
            self.parent.current_activity()
            if hasattr(self.parent, "current_activity")
            else Activity.get_current()
        )

        qs_deleted = None
        if mode_filter in (MODE_ALL, MODE_ACCOUNTS):
            qs_deleted = _apply_type(
                ProviderOrClient.select().where(ProviderOrClient.deleted == True)
            )
            if activity is not None:
                qs_deleted = qs_deleted.where(ProviderOrClient.activity == activity)

        qs_ops = None
        if mode_filter in (MODE_ALL, MODE_OPS):
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
                if activity is not None:
                    qs_ops = qs_ops.where(ProviderOrClient.activity == activity)

        if provid_clt:
            search = str(provid_clt).strip()
            if search:
                if qs_deleted is not None:
                    qs_deleted = qs_deleted.where(ProviderOrClient.name.contains(search))
                if qs_ops is not None:
                    qs_ops = qs_ops.where(ProviderOrClient.name.contains(search))

        if qs_deleted is not None:
            for p in qs_deleted.order_by(ProviderOrClient.name):
                self.addItem(ProviderOrClientQListWidgetItem(p, "account_trash"))
        if qs_ops is not None:
            for p in qs_ops.order_by(ProviderOrClient.name):
                self.addItem(ProviderOrClientQListWidgetItem(p, "ops_trash"))

        if hasattr(self.parent, "update_accounts_count"):
            self.parent.update_accounts_count()
        if hasattr(self.parent, "_update_empty_state"):
            self.parent._update_empty_state()
        self._autosize_width_to_longest_text()

    def _autosize_width_to_longest_text(self):
        fm = QFontMetrics(self.font())
        max_w = 160
        for i in range(self.count()):
            it = self.item(i)
            if it is None:
                continue
            max_w = max(max_w, fm.horizontalAdvance(it.text()))
        self.setMinimumWidth(min(max_w + 48, 420))

    def handleClicked(self):
        item = self.currentItem()
        if item is None:
            return
        self.provid_clt = item
        self.provid_clt_id = item.provid_clt_id

        if isinstance(self.provid_clt_id, int):
            self.parent.set_action_buttons_enabled(True)
        else:
            if Config.DEVISE_PEP_PROV:
                return
            self.parent.set_action_buttons_enabled(False)
        self.parent.table.refresh_(provid_clt_id=self.provid_clt_id)


class ProviderOrClientQListWidgetItem(QListWidgetItem):
    """account_trash = compte soft-deleted ; ops_trash = compte actif avec ops en corbeille."""

    def __init__(self, provid_clt, list_entry_mode="account_trash"):
        super(ProviderOrClientQListWidgetItem, self).__init__()
        self.provid_clt = provid_clt
        self.list_entry_mode = list_entry_mode
        self._item_height = 40
        self.setSizeHint(QSize(0, self._item_height))
        icon = QIcon()
        if not isinstance(self.provid_clt, str):
            icon_path = "{}.png".format(
                Config.img_media + "debt"
                if self.provid_clt.is_indebted()
                else Config.img_cmedia + "user_active"
            )
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
                self.setText(f"{self.provid_clt.name}  ·  {n} op. en corbeille")
                self.setToolTip(
                    f"Compte actif « {self.provid_clt.name} » avec {n} opération(s) "
                    "supprimée(s). Double-clic pour restaurer les opérations."
                )
            else:
                self.setText(f"{self.provid_clt.name}  ·  compte")
                self.setToolTip(
                    f"Compte « {self.provid_clt.name} » en corbeille. "
                    "Double-clic pour restaurer."
                )
        except AttributeError:
            font = QFont()
            font.setBold(True)
            self.setFont(font)
            self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setText("Tous les éléments")
            self.setToolTip("Afficher toutes les opérations en corbeille")
        self._update_min_width_from_text()

    def _update_min_width_from_text(self):
        fm = QFontMetrics(self.font())
        min_w = fm.horizontalAdvance(self.text()) + 48
        self.setSizeHint(QSize(max(0, int(min_w)), self._item_height))

    @property
    def provid_clt_id(self):
        try:
            return self.provid_clt.id
        except AttributeError:
            return self.provid_clt


class RapportTableWidget(FTableWidget):
    def __init__(self, parent, *args, **kwargs):
        FTableWidget.__init__(self, parent=parent, *args, **kwargs)

        self.hheaders = ["Date", "Libellé", "Débit", "Crédit", "Solde", ""]
        self.parent = parent

        self.sorter = False
        self.stretch_columns = [1]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r"}
        self.ecart = -15
        self.display_vheaders = False
        self.provider_clt = None
        self._libelle_column = 1
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._popup_row)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self._apply_column_resize_modes()

    def _apply_column_resize_modes(self):
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        last_col = len(self.hheaders) - 1
        libelle_col = getattr(self, "_libelle_column", 1)
        for col in range(header.count() or len(self.hheaders)):
            if col == last_col:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            elif col == libelle_col:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

    def _format_for_table(self, value):
        from decimal import Decimal
        from datetime import date as date_cls

        if isinstance(value, float):
            return format_number_table_no_round(value)
        if isinstance(value, Decimal):
            return format_number_table_no_round(value)
        if isinstance(value, (datetime, date_cls)):
            return format_movement_date(value)
        return super()._format_for_table(value)

    def refresh_(self, provid_clt_id=None, search=None):
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
        self._apply_column_resize_modes()

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
                self.parent.set_selection_banner(
                    "<b>Compte introuvable</b> (déjà purgé ?)"
                )
                if hasattr(self.parent, "table_provid_clt"):
                    self.parent.table_provid_clt.refresh_(
                        provid_clt=self.parent.search_field.text().strip() or None
                    )
                return
            qs = qs.where(Payment.provider_clt == self.provider_clt)
            solde = device_amount(self.provider_clt.last_remaining(), self.provider_clt)
            solde = self.parent.format_balance_text(solde)
            n_ops = qs.count()
            mode = "compte en corbeille"
            try:
                item = self.parent.table_provid_clt.currentItem()
                if (
                    isinstance(item, ProviderOrClientQListWidgetItem)
                    and getattr(item, "list_entry_mode", "") == "ops_trash"
                ):
                    mode = "opérations en corbeille"
            except Exception:
                pass
            tel = self.provider_clt.phone or "—"
            msg = (
                f"<b>{self.provider_clt.name}</b> · {mode}<br>"
                f"<span style='color:palette(mid); font-size:12px;'>"
                f"{n_ops} opération(s) · Solde {solde} · Tél. {tel}</span>"
            )
        else:
            self.provider_clt = "Tous"
            activity = (
                self.parent.current_activity()
                if hasattr(self.parent, "current_activity")
                else Activity.get_current()
            )
            if activity is not None:
                account_ids = [
                    a.id
                    for a in ProviderOrClient.select(ProviderOrClient.id).where(
                        ProviderOrClient.activity == activity
                    )
                ]
                if account_ids:
                    qs = qs.where(Payment.provider_clt.in_(account_ids))
                else:
                    qs = qs.where(Payment.id == -1)
            n_ops = qs.count()
            msg = (
                f"<b>Toutes les opérations</b><br>"
                f"<span style='color:palette(mid); font-size:12px;'>"
                f"{n_ops} opération(s) en corbeille</span>"
            )
        self.parent.set_selection_banner(msg)

        self.data = [
            (
                format_movement_date(pay.date),
                pay.libelle,
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
        act_restore = menu.addAction("Restaurer cette opération")
        act_erase = menu.addAction("Supprimer définitivement…")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen is None:
            return
        mw = self._main_window()
        try:
            payment = Payment.get(id=self.data[row][-1])
            if chosen == act_restore:
                payment.restore_from_trash()
                if mw:
                    mw.Notify("Opération restaurée", "success")
            elif chosen == act_erase:
                reply = QMessageBox.question(
                    self,
                    "Suppression définitive",
                    "Supprimer définitivement cette opération ?\nCette action est irréversible.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    payment.deletes_data()
                    if mw:
                        mw.Notify("Opération supprimée définitivement", "success")
        except Exception as e:
            logger.exception("Poubelle menu opération: %s", e)
            if mw:
                mw.Notify(str(e), "error")
        if hasattr(self.parent, "table_provid_clt"):
            self.parent.table_provid_clt.refresh_(
                provid_clt=self.parent.search_field.text().strip() or None
            )
        if hasattr(self.parent, "refresh_header_stats"):
            self.parent.refresh_header_stats()
        pid = self.provid_clt_id if isinstance(self.provid_clt_id, int) else None
        self.refresh_(provid_clt_id=pid)

    def extend_rows(self):
        nb_rows = self.rowCount()
        self.setRowCount(nb_rows + 1)
        self.setSpan(nb_rows + 2, 2, 2, 4)
        self.totals_debit = 0
        self.totals_credit = 0
        self.balance_tt = 0
        for row_num in range(0, self.data.__len__()):
            mtt_debit = is_float(str(self.item(row_num, 2).text()))
            mtt_credit = is_float(str(self.item(row_num, 3).text()))
            self.totals_debit += mtt_debit
            self.totals_credit += mtt_credit

        self.balance_tt = self.totals_credit - self.totals_debit

        self.label_mov_tt = "Totaux : "
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
        client_name = (
            self.provider_clt.name
            if hasattr(self.provider_clt, "name")
            else str(self.provider_clt)
        )
        client_id = (
            getattr(self.provider_clt, "id", None)
            if hasattr(self.provider_clt, "id")
            else None
        )
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
        self.parent = parent

        self.sorter = False
        self.stretch_columns = [1]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r", 5: "r"}
        self.display_vheaders = False
        self.provider_clt = None
        self._libelle_column = 1
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._popup_row)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self._apply_column_resize_modes()

    def _apply_column_resize_modes(self):
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        last_col = len(self.hheaders) - 1
        libelle_col = getattr(self, "_libelle_column", 1)
        for col in range(header.count() or len(self.hheaders)):
            if col == last_col:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            elif col == libelle_col:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

    def _format_for_table(self, value):
        from decimal import Decimal
        from datetime import date as date_cls

        if isinstance(value, float):
            return format_number_table_no_round(value)
        if isinstance(value, Decimal):
            return format_number_table_no_round(value)
        if isinstance(value, (datetime, date_cls)):
            return format_movement_date(value)
        return super()._format_for_table(value)

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
        self._apply_column_resize_modes()

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
                self.parent.set_selection_banner(
                    "<b>Compte introuvable</b> (déjà purgé ?)"
                )
                if hasattr(self.parent, "table_provid_clt"):
                    self.parent.table_provid_clt.refresh_(
                        provid_clt=self.parent.search_field.text().strip() or None
                    )
                return
            qs = qs.where(Payment.provider_clt == self.provider_clt)
            solde = device_amount(self.provider_clt.last_remaining(), self.provider_clt)
            solde = self.parent.format_balance_text(solde)
            tel = self.provider_clt.phone or "—"
            n_ops = qs.count()
            msg = (
                f"<b>{self.provider_clt.name}</b><br>"
                f"<span style='color:palette(mid); font-size:12px;'>"
                f"{n_ops} opération(s) · Solde {solde} · Tél. {tel}</span>"
            )
        else:
            self.provider_clt = "Tous"
            activity = (
                self.parent.current_activity()
                if hasattr(self.parent, "current_activity")
                else Activity.get_current()
            )
            if activity is not None:
                account_ids = [
                    a.id
                    for a in ProviderOrClient.select(ProviderOrClient.id).where(
                        ProviderOrClient.activity == activity
                    )
                ]
                if account_ids:
                    qs = qs.where(Payment.provider_clt.in_(account_ids))
                else:
                    qs = qs.where(Payment.id == -1)
            n_ops = qs.count()
            msg = (
                f"<b>Toutes les opérations</b><br>"
                f"<span style='color:palette(mid); font-size:12px;'>"
                f"{n_ops} opération(s) en corbeille</span>"
            )
        self.parent.set_selection_banner(msg)

        self.data = [
            (
                format_movement_date(pay.date),
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
        act_restore = menu.addAction("Restaurer cette opération")
        act_erase = menu.addAction("Supprimer définitivement…")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen is None:
            return
        mw = self._main_window()
        try:
            payment = Payment.get(id=self.data[row][-1])
            if chosen == act_restore:
                payment.restore_from_trash()
                if mw:
                    mw.Notify("Opération restaurée", "success")
            elif chosen == act_erase:
                reply = QMessageBox.question(
                    self,
                    "Suppression définitive",
                    "Supprimer définitivement cette opération ?\nCette action est irréversible.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    payment.deletes_data()
                    if mw:
                        mw.Notify("Opération supprimée définitivement", "success")
        except Exception as e:
            logger.exception("Poubelle menu opération (CISS): %s", e)
            if mw:
                mw.Notify(str(e), "error")
        if hasattr(self.parent, "table_provid_clt"):
            self.parent.table_provid_clt.refresh_(
                provid_clt=self.parent.search_field.text().strip() or None
            )
        if hasattr(self.parent, "refresh_header_stats"):
            self.parent.refresh_header_stats()
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
        for row_num in range(0, self.data.__len__()):
            mtt_weight = is_float(str(self.item(row_num, 2).text()))
            mtt_debit = is_float(str(self.item(row_num, 3).text()))
            mtt_credit = is_float(str(self.item(row_num, 4).text()))
            self.totals_weight += mtt_weight
            self.totals_debit += mtt_debit
            self.totals_credit += mtt_credit

        self.balance_tt = self.totals_credit - self.totals_debit

        self.label_mov_tt = "Totaux : "
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
        client_name = (
            self.provider_clt.name
            if hasattr(self.provider_clt, "name")
            else str(self.provider_clt)
        )
        client_id = (
            getattr(self.provider_clt, "id", None)
            if hasattr(self.provider_clt, "id")
            else None
        )
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
            "format_money": ["C:C", "D:D", "E:E"],
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
