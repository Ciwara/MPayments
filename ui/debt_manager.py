#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fadiga

import logging
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# Racine du projet dans sys.path si on exécute ce fichier directement
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from Common.ui.common import (Button, FormLabel,
                              FWidget, LineEdit)
from Common.ui.table import FTableWidget, TotalsWidget
from Common.ui.util import is_float
from configuration import Config
from data_helper import device_amount
from models import Payment, ProviderOrClient
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont, QIcon, QPixmap, QShortcut, QKeySequence
from PyQt6.QtWidgets import (QGridLayout, QHBoxLayout, QListWidget,
                             QListWidgetItem, QMenu, QSplitter, QFrame, QVBoxLayout, QLabel,
                             QAbstractItemView, QHeaderView, QComboBox)
from ui.payment_edit_add import EditOrAddPaymentrDialog
from ui.provider_client_edit_add import EditOrAddClientOrProviderDialog

# Configuration du logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Palette de couleurs moderne (cohérente avec dashboard et statistics)
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
    """Shows the debts view page"""

    def __init__(self, parent=0, *args, **kwargs):
        logger.debug("Initialisation de DebtsViewWidget avec design moderne")
        super(DebtsViewWidget, self).__init__(parent=parent, *args, **kwargs)

        self.parent = parent
        self.parentWidget().setWindowTitle(Config.APP_NAME + " Gestion des dettes")
        logger.debug("Titre de la fenêtre défini")

        # Style moderne pour le widget principal - SIMPLIFIÉ

        # Optimisation de la mise en cache des données
        self._cached_data = {}
        self._last_refresh = None
        
        self.title = "Gestion des dettes"
        self.now = datetime.now().strftime(Config.DATEFORMAT)
        logger.debug(f"Date actuelle: {self.now}")

        # Configuration moderne des labels - SIMPLIFIÉ
        self.label_balance = QLabel("")
        # self.label_balance.setFont(QFont("Segoe UI", 14, QFont.Bold))
        # self.label_balance.setFixedHeight(60)
        
        self.label_owner = QLabel("")
        # self.label_owner.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        # self.label_owner.setFixedHeight(50)

        # Configuration optimisée de la table avec style moderne
        if Config.CISS:
            logger.debug("Configuration CISS activée")
            self.table = RapportCISSTableWidget(parent=self)
        else:
            logger.debug("Configuration CISS désactivée")
            self.table = RapportTableWidget(parent=self)
        
        # Table des fournisseurs/clients avec style moderne  
        self.table_provid_clt = ProviderOrClientTableWidget(parent=self)
        logger.debug("Table des fournisseurs/clients initialisée avec style moderne")

        # Filtre par type de compte (Clients / Fournisseurs / Tous)
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems(["Clients", "Fournisseurs", "Tous"])
        self.type_filter_combo.currentTextChanged.connect(self._on_type_filter_changed)
        logger.debug("Filtre par type configuré")

        # Champ de recherche avec placeholder
        self.search_field = LineEdit()
        self.search_field.setPlaceholderText("Rechercher par nom ou téléphone...")
        self.search_field.textChanged.connect(self.search)
        logger.debug("Champ de recherche configuré")

        # Indicateur du nombre de résultats
        self.search_count_label = QLabel("0 compte(s)")
        self.search_count_label.setStyleSheet("color: palette(window-text); font-size: 11px;")
        logger.debug("Label nombre de résultats configuré")

        # Raccourci clavier Nouveau compte
        QShortcut(QKeySequence("Ctrl+N"), self, self.add_prov_or_clt)

        # Configuration optimisée des boutons d'action - SIMPLIFIÉ
        self.add_btt = Button("💰 Créditer")
        self.add_btt.setEnabled(False)
        self.add_btt.clicked.connect(self.add_payment)
        logger.debug("Bouton d'ajout configuré avec style moderne")

        self.sub_btt = Button("💸 Débiter")
        self.sub_btt.setEnabled(False)
        self.sub_btt.clicked.connect(self.sub_payment)
        logger.debug("Bouton de soustraction configuré avec style moderne")

        self.add_prov_btt = Button("➕ Nouveau Compte")
        self.add_prov_btt.clicked.connect(self.add_prov_or_clt)
        logger.debug("Bouton d'ajout de compte configuré avec style moderne")

        # Boutons d'export modernes - SIMPLIFIÉ
        self.button = Button("🔄")
        self.button.clicked.connect(self.refresh_period)

        self.btt_pdf_export = Button("📄")
        self.btt_pdf_export.clicked.connect(self.export_pdf)
        
        self.btt_xlsx_export = Button("📊")
        self.btt_xlsx_export.clicked.connect(self.export_xlsx)
        logger.debug("Boutons d'export configurés avec style moderne")

        # Conteneurs modernes pour l'organisation
        left_container = QFrame()
        left_container.setObjectName("accounts_panel")
        left_title = QLabel("👥 Comptes")
        left_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        left_title.setStyleSheet("color: palette(window-text);")

        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(left_title)
        type_label = QLabel("Afficher :")
        type_label.setStyleSheet("color: palette(window-text); font-size: 11px;")
        left_layout.addWidget(type_label)
        left_layout.addWidget(self.type_filter_combo)
        left_layout.addWidget(self.search_field)
        left_layout.addWidget(self.search_count_label)
        left_layout.addWidget(self.table_provid_clt)
        left_layout.addWidget(self.add_prov_btt)
        left_container.setLayout(left_layout)

        # Conteneur de droite avec titre
        right_container = QFrame()
        
        right_title = QLabel("💳 Gestion des Mouvements")
        right_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))

        # Zone de contrôles modernes
        controls_container = QFrame()
        
        controls_layout = QGridLayout()
        controls_layout.setSpacing(12)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Première ligne - Info client
        controls_layout.addWidget(self.label_owner, 0, 0, 1, 5)
        
        # Deuxième ligne - Boutons d'action
        controls_layout.addWidget(self.sub_btt, 1, 0)
        controls_layout.addWidget(self.add_btt, 1, 1)
        controls_layout.addWidget(self.button, 1, 2)
        controls_layout.addWidget(self.btt_pdf_export, 1, 3)
        controls_layout.addWidget(self.btt_xlsx_export, 1, 4)
        
        # Espacement flexible
        controls_layout.setColumnStretch(5, 1)
        controls_container.setLayout(controls_layout)

        # Table des mouvements dans un conteneur
        table_container = QFrame()
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.table)
        table_container.setLayout(table_layout)

        # Balance dans un conteneur centré
        balance_container = QFrame()
        balance_layout = QHBoxLayout()
        balance_layout.addStretch()
        balance_layout.addWidget(self.label_balance)
        balance_layout.addStretch()
        balance_container.setLayout(balance_layout)

        # Layout principal du conteneur de droite
        right_layout = QVBoxLayout()
        right_layout.setSpacing(16)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(right_title)
        right_layout.addWidget(controls_container)
        right_layout.addWidget(table_container)
        right_layout.addWidget(balance_container)
        right_container.setLayout(right_layout)

        # Splitter principal moderne - SIMPLIFIÉ
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(3)
        main_splitter.addWidget(left_container)
        main_splitter.addWidget(right_container)
        main_splitter.setSizes([350, 850])  # Proportion initiale

        # Layout principal
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

        self.update_accounts_count()
        logger.debug("DebtsViewWidget initialisé avec succès - Design moderne appliqué")

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

    def _on_type_filter_changed(self, _text):
        """Recharge la liste selon le type (Clients / Fournisseurs / Tous)."""
        self.table_provid_clt.refresh_(provid_clt=self.search_field.text().strip() or None)
        self.update_accounts_count()

    def update_accounts_count(self):
        """Met à jour le label du nombre de comptes affichés."""
        table = getattr(self, "table_provid_clt", None)
        label = getattr(self, "search_count_label", None)
        if table is None or label is None:
            return
        n = max(0, table.count() - 1)  # -1 pour la ligne "TOUS"
        label.setText(f"{n} compte(s)")

    def search(self):
        """Recherche avec mise à jour du nombre de résultats."""
        search_text = self.search_field.text()
        logger.debug(f"Recherche avec le texte: {search_text}")

        if search_text in self._cached_data:
            self.table_provid_clt.refresh_(provid_clt=search_text.strip() or None)
        else:
            self.table_provid_clt.refresh_(provid_clt=search_text.strip() or None)
            self._cached_data[search_text] = search_text
        self.update_accounts_count()

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
        return f"""
        <div style="text-align: center;">
            <h3 style="margin: 0; color: white; font-weight: 700; font-family: 'Segoe UI';">
                💰 Solde du {self.now}
            </h3>
            <h2 style="margin: 8px 0 0 0; color: white; font-weight: 700; font-size: 18px; font-family: 'Segoe UI';">
                {amount_text}
            </h2>
        </div>
        """


class ProviderOrClientTableWidget(QListWidget):

    """affiche tout le nom de tous les provid_cltes"""

    def __init__(self, parent, *args, **kwargs):
        super(ProviderOrClientTableWidget, self).__init__(parent)

        self.parent = parent
        self.setAutoScroll(True)
        # self.setAutoFillBackground(True)
        self.itemSelectionChanged.connect(self.handleClicked)
        self.itemDoubleClicked.connect(self._on_double_click)
        self.refresh_()

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.popup)

    def _on_double_click(self, item):
        """Double-clic sur un compte : ouvrir l'édition."""
        if not isinstance(item, ProviderOrClientQListWidgetItem):
            return
        if isinstance(item.provid_clt, str):
            return
        self.parent.open_dialog(
            EditOrAddClientOrProviderDialog,
            modal=True,
            prov_clt=item.provid_clt,
            table_p=self,
        )

    def popup(self, pos):
        from ui.deleteview_cpt import DeleteViewWidget

        row = self.selectionModel().selection().indexes()[0].row()
        if row < 1:
            return
        item = self.item(row)
        if not isinstance(item, ProviderOrClientQListWidgetItem) or isinstance(item.provid_clt, str):
            return
        provid_clt = item.provid_clt
        menu = QMenu()
        editaction = menu.addAction("Modifier l'info.")
        delaction = menu.addAction("Supprimer ce compte")
        action = menu.exec(self.mapToGlobal(pos))

        if action == editaction:
            self.parent.open_dialog(
                EditOrAddClientOrProviderDialog,
                modal=True,
                prov_clt=provid_clt,
                table_p=self,
            )
        elif action == delaction:
            self.parent.open_dialog(
                DeleteViewWidget, modal=True, table_p=self, obj=provid_clt
            )

    def refresh_(self, provid_clt=None):
        """Rafraîchir la liste des comptes (clients/fournisseurs) selon le filtre et la recherche."""
        self.clear()
        self.addItem(ProviderOrClientQListWidgetItem(ALL_CONTACTS))

        type_filter = "Clients"
        if hasattr(self.parent, "type_filter_combo"):
            type_filter = self.parent.type_filter_combo.currentText()

        qs = ProviderOrClient.select().where(ProviderOrClient.deleted == False)
        if type_filter == "Clients":
            qs = qs.where(ProviderOrClient.type_ == ProviderOrClient.CLT)
        elif type_filter == "Fournisseurs":
            qs = qs.where(ProviderOrClient.type_ == ProviderOrClient.FSEUR)
        # "Tous" : pas de filtre sur le type

        if provid_clt:
            search = str(provid_clt).strip()
            if search:
                qs = qs.where(ProviderOrClient.name.contains(search))
        for p in qs.order_by(ProviderOrClient.name):
            self.addItem(ProviderOrClientQListWidgetItem(p))

        if hasattr(self.parent, "update_accounts_count"):
            self.parent.update_accounts_count()

    def handleClicked(self):
        # Peut être déclenché sans item courant (ex: refresh/clear en cours)
        if hasattr(self.parent, "btt_xlsx_export"):
            self.parent.btt_xlsx_export.setEnabled(False)

        self.provid_clt = self.currentItem()
        if self.provid_clt is None:
            self.provid_clt_id = None
            self.parent.sub_btt.setEnabled(False)
            self.parent.add_btt.setEnabled(False)
            return

        self.provid_clt_id = getattr(self.provid_clt, "provid_clt_id", None)

        if isinstance(self.provid_clt_id, int):
            self.parent.sub_btt.setEnabled(True)
            self.parent.add_btt.setEnabled(True)
        else:
            if Config.DEVISE_PEP_PROV:
                # print("DEVISE_PEP_PROV handleClicked")
                return
            self.parent.sub_btt.setEnabled(False)
            self.parent.add_btt.setEnabled(False)
        if self.provid_clt_id is not None:
            self.parent.table.refresh_(provid_clt_id=self.provid_clt_id)


class ProviderOrClientQListWidgetItem(QListWidgetItem):
    def __init__(self, provid_clt):
        super(ProviderOrClientQListWidgetItem, self).__init__()
        from PyQt6.QtCore import QSize

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
                QIcon.Mode.Normal,
                QIcon.State.Off,
            )

        self.setIcon(icon)
        self.init_text()

    def init_text(self):
        try:
            solde = self.provid_clt.last_remaining()
            montant = device_amount(solde, self.provid_clt)
            self.setText(f"{self.provid_clt.name} — {montant}")
        except AttributeError:
            font = QFont()
            font.setBold(True)
            self.setFont(font)
            self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
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

        self.hheaders = [
            "📅 Date", 
            "📝 Libellé opération", 
            "💸 Débit", 
            "💰 Crédit", 
            "📊 Solde", 
            ""
        ]
        
        # Style moderne pour le tableau standard - SIMPLIFIÉ
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.popup)

        self.parent = parent

        self.sorter = False
        self.stretch_columns = [0, 1, 2, 3, 4]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r"}
        self.ecart = -15
        self.display_vheaders = False
        
        # Configuration moderne du tableau
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
        
        self.label_mov_tt = "-"
        self.provider_clt = None
        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.balance_tt = 0.0

    def refresh_(self, provid_clt_id=None, search=None):
        """Rafraîchissement avec calculs améliorés"""
        logger.debug(f"Rafraîchissement des données pour client {provid_clt_id}")
        
        # Initialisation des totaux
        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.balance_tt = 0.0
        self._totals_row_added = False
        
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
            solde = device_amount(self.provider_clt.last_remaining(), self.provider_clt)
            tel = self.provider_clt.phone or "—"
            msg = f"<h3>Compte : {self.provider_clt.name} — Solde : {solde}</h3><h4>Tel : {tel}</h4>"
            logger.debug(f"Filtre sur le compte: {self.provider_clt.name}")
        else:
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
        action = menu.exec(self.mapToGlobal(pos))
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
        # Éviter les appels multiples (Qt peut rappeler extend_rows plusieurs fois)
        if getattr(self, "_totals_row_added", False):
            return
        self._totals_row_added = True

        nb_rows = self.rowCount()
        self.setRowCount(nb_rows + 1)
        
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

    def _format_date_for_export(self, date_val):
        """Formate une date pour l'export PDF (lisible)."""
        if date_val is None:
            return ""
        if hasattr(date_val, "strftime"):
            return date_val.strftime("%d/%m/%Y")
        return str(date_val)[:10] if len(str(date_val)) >= 10 else str(date_val)

    def dict_data(self):
        """Données d'export PDF/XLSX : titre, en-têtes, lignes formatées + totaux, période, infos compte."""
        client_name = self.provider_clt.name if hasattr(self.provider_clt, "name") else str(self.provider_clt)
        client_id = getattr(self.provider_clt, "id", None) if hasattr(self.provider_clt, "id") else None
        is_single = isinstance(self.provider_clt, ProviderOrClient)

        # Totaux (initialisés dans __init__, recalculés dans extend_rows())
        totals_debit = getattr(self, "totals_debit", 0.0)
        totals_credit = getattr(self, "totals_credit", 0.0)
        balance_tt = getattr(self, "balance_tt", 0.0)

        title = "Relevé des mouvements"
        if is_single:
            title = f"{title} — {client_name}"
        else:
            title = f"{title} — Tous les comptes"

        # Lignes formatées pour le PDF (5 colonnes, sans id) : Date, Libellé, Débit, Crédit, Solde
        export_rows = []
        for row in self.data:
            date_val, libelle, debit, credit, balance, _ = row
            export_rows.append([
                self._format_date_for_export(date_val),
                str(libelle or ""),
                device_amount(debit, client_id),
                device_amount(credit, client_id),
                device_amount(balance, client_id),
            ])
        # Ligne de séparation visuelle avant totaux (vide)
        export_rows.append(["", "", "", "", ""])
        # Ligne des totaux
        export_rows.append([
            "",
            "Totaux",
            device_amount(totals_debit, client_id),
            device_amount(totals_credit, client_id),
            device_amount(balance_tt, client_id),
        ])

        date_str = self.parent.now
        if is_single:
            date_str = f"Au {date_str} — Solde : {device_amount(balance_tt, client_id)}"

        # Période couverte par les mouvements
        period_str = ""
        nb_movements = len(self.data)
        if self.data:
            first_date = self._format_date_for_export(self.data[0][0])
            last_date = self._format_date_for_export(self.data[-1][0])
            period_str = f"Période : du {first_date} au {last_date} — {nb_movements} mouvement(s)"

        # Nom de fichier sécurisé (caractères interdits Windows/Unix)
        safe_name = client_name if is_single else "tous_comptes"
        for c in r'\/:*?"<>|':
            safe_name = safe_name.replace(c, "_")
        safe_name = safe_name.replace(" ", "_")[:40].strip("_") or "compte"
        file_name = f"Releve_mouvements_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M')}"

        # Excel: le nom d'onglet doit être <= 31 caractères
        sheet_name = "Mouvements"
        if is_single:
            sheet_name = f"Mouv. {safe_name}"
        else:
            sheet_name = "Mouv. Tous"
        sheet_name = sheet_name[:31]

        # Bloc d'en-tête pour le PDF (compte, type, tél., solde, période)
        others = [
            ("A7", "C7", "Compte : {}".format(client_name)),
        ]
        if is_single:
            type_label = getattr(self.provider_clt, "type_", None) or "Compte"
            others.append(("A8", "C8", "Type : {}".format(type_label)))
            tel = getattr(self.provider_clt, "phone", None)
            others.append(("A9", "C9", "Tél. : {}".format(tel if tel is not None else "—")))
            others.append(("A10", "C10", "Solde au {} : {}".format(self.parent.now, device_amount(balance_tt, client_id))))
            if period_str:
                others.append(("A11", "E11", period_str))
        else:
            others.append(("A8", "C8", "Solde au {} : {}".format(self.parent.now, device_amount(balance_tt, client_id))))
            if period_str:
                others.append(("A9", "E9", period_str))

        return {
            "file_name": file_name,
            "title": title,
            "date": date_str,
            "headers": ["Date", "Libellé", "Débit", "Crédit", "Solde"],
            "data": export_rows,
            "extend_rows": [
                (1, self.label_mov_tt),
                (2, totals_debit),
                (3, totals_credit),
            ],
            "sheet": sheet_name,
            "widths": self.stretch_columns,
            "format_money": ["C:C", "D:D", "E:E"],
            "exclude_row": len(self.data) - 1,
            "others": others,
            "period": period_str,
            "nb_movements": nb_movements,
        }


class RapportCISSTableWidget(FTableWidget):
    def __init__(self, parent, *args, **kwargs):
        FTableWidget.__init__(self, parent=parent, *args, **kwargs)

        self.hheaders = [
            "📅 Date",
            "📝 Libellé opération",
            "⚖️ Poids (kg)",
            "💸 Débit",
            "💰 Crédit",
            "📊 Solde",
            "",
        ]
        
        # Style moderne pour le tableau CISS - SIMPLIFIÉ
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.popup)

        self.parent = parent

        self.sorter = False
        self.stretch_columns = [0, 1, 2, 3, 4, 5]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r", 5: "r"}
        self.display_vheaders = False
        
        # Configuration moderne du tableau
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
        self.provider_clt = None

    def refresh_(self, provid_clt_id=None, search=None):
        """Rafraîchissement avec calculs améliorés pour CISS"""
        logger.debug(f"Rafraîchissement CISS pour client {provid_clt_id}")

        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.totals_weight = 0.0
        self.balance_tt = 0.0
        self._totals_row_added = False
        
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
        action = menu.exec(self.mapToGlobal(pos))
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
        if getattr(self, "_totals_row_added", False):
            return
        self._totals_row_added = True

        nb_rows = self.rowCount()
        self.setRowCount(nb_rows + 1)
        
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
