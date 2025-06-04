#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fad

import logging
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

from PyQt5.QtWidgets import QVBoxLayout, QGridLayout, QMenu, QFrame, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont

from configuration import Config
from Common.ui.common import (
    FormLabel,
    FWidget,
    FPeriodHolder,
    FPageTitle,
    BttExportPDF,
    BttExportXLSX,
    FormatDate,
    ExtendedComboBox,
)
from Common.ui.table import FTableWidget, TotalsWidget
from Common.ui.util import is_float, date_to_datetime, date_on_or_end
from data_helper import device_amount

from models import Payment, ProviderOrClient
from ui.payment_edit_add import EditOrAddPaymentrDialog

# Configuration du logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Palette de couleurs moderne (même que dashboard.py)
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

# Fonctions utilitaires pour les calculs précis (même que debt_manager.py)
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
        if len(payment) == 7:  # Format CISS avec poids
            date_val, libelle, weight, debit, credit, stored_balance, payment_id = payment
            weight_amount = safe_float(weight)
        else:  # Format standard
            date_val, libelle, debit, credit, stored_balance, payment_id = payment
            weight_amount = 0.0
        
        # Utiliser les valeurs réelles de débit/crédit pour recalculer
        debit_amount = safe_float(debit)
        credit_amount = safe_float(credit)
        
        # Calcul de la balance courante
        running_balance += credit_amount - debit_amount
        running_balance = precise_calculation(running_balance)
        
        # Remplacer la balance stockée par la balance calculée
        if len(payment) == 7:  # Format CISS
            calculated_data.append((date_val, libelle, weight_amount, debit_amount, credit_amount, running_balance, payment_id))
        else:  # Format standard
            calculated_data.append((date_val, libelle, debit_amount, credit_amount, running_balance, payment_id))
    
    return calculated_data


class StatisticsViewWidget(FWidget, FPeriodHolder):
    def __init__(self, parent=0, *args, **kwargs):
        logger.debug("Initialisation de StatisticsViewWidget avec design moderne")
        super(StatisticsViewWidget, self).__init__(parent=parent, *args, **kwargs)
        FPeriodHolder.__init__(self, *args, **kwargs)

        self.parent = parent

        self.title = u"Movements"
        self.compte = self.compte_name = "Tous"

        # Style moderne pour le widget principal
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['background']};
                font-family: "Segoe UI", "Arial", sans-serif;
            }}
        """)

        # Optimisation des champs de date avec style moderne
        self.on_date_field = FormatDate(QDate(date.today().year, date.today().month, 1))
        self.on_date_field.dateChanged.connect(self.refresh_prov_clt)
        self.on_date_field.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 11px;
                color: {COLORS['text_primary']};
                min-height: 20px;
            }}
            QDateEdit:focus {{
                border-color: {COLORS['primary']};
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 20px;
            }}
        """)
        
        self.end_date_field = FormatDate(QDate.currentDate())
        self.end_date_field.dateChanged.connect(self.refresh_prov_clt)
        self.end_date_field.setStyleSheet(self.on_date_field.styleSheet())
        
        self.now = datetime.now().strftime(Config.DATEFORMAT)
        
        # Configuration moderne des labels de balance
        self.balanceField = QLabel("")
        self.balanceField.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.balanceField.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS['primary']},
                    stop:1 {COLORS['primary_dark']});
                color: white;
                border-radius: 12px;
                padding: 16px 24px;
                margin: 8px 0;
                font-weight: 700;
            }}
        """)
        self.balanceField.setFixedHeight(60)
        
        # Conteneur moderne pour la balance
        balance_container = QFrame()
        balance_container.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
        """)
        balance_layout = QHBoxLayout()
        balance_layout.addStretch()
        balance_layout.addWidget(self.balanceField)
        balance_layout.addStretch()
        balance_container.setLayout(balance_layout)

        # Cache pour optimiser les requêtes fréquentes
        self._cached_client_list = None
        self._last_client_refresh = None
        
        # Récupération optimisée de la liste des clients
        self.refresh_client_list()
        
        # Titre moderne avec style amélioré
        self.title_field = QLabel("📊 Statistiques - Tous")
        self.title_field.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.title_field.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_primary']};
                margin: 16px 0;
                font-weight: 700;
                letter-spacing: -0.5px;
            }}
        """)
        self.title_field.setFixedHeight(50)
        
        # ComboBox moderne pour les comptes
        self.compte_field = ExtendedComboBox()
        self.compte_field.addItems(self.string_list)
        self.compte_field.setToolTip("Nom du compte")
        self.compte_field.currentIndexChanged.connect(self.refresh_prov_clt)
        self.compte_field.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                min-width: 200px;
                min-height: 20px;
                font-size: 11px;
                font-weight: 500;
                color: {COLORS['text_primary']};
            }}
            QComboBox:hover {{
                border-color: {COLORS['primary_light']};
            }}
            QComboBox:focus {{
                border-color: {COLORS['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
                margin-right: 4px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {COLORS['text_secondary']};
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                selection-background-color: {COLORS['primary_light']};
                padding: 4px;
            }}
        """)

        # Boutons d'export modernes
        self.btt_pdf_export = BttExportPDF("")
        self.btt_pdf_export.clicked.connect(self.export_pdf)
        self.btt_pdf_export.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['error']},
                    stop:1 {COLORS['error_light']});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 11px;
                min-width: 80px;
                min-height: 32px;
            }}
            QPushButton:hover {{
                background: {COLORS['error_light']};
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background: {COLORS['error']};
                transform: translateY(0px);
            }}
        """)
        self.btt_pdf_export.setFixedSize(80, 40)
        
        self.btt_xlsx_export = BttExportXLSX("")
        self.btt_xlsx_export.clicked.connect(self.export_xlsx)
        self.btt_xlsx_export.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['success']},
                    stop:1 {COLORS['success_light']});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 11px;
                min-width: 80px;
                min-height: 32px;
            }}
            QPushButton:hover {{
                background: {COLORS['success_light']};
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background: {COLORS['success']};
                transform: translateY(0px);
            }}
        """)
        self.btt_xlsx_export.setFixedSize(80, 40)

        # Configuration optimisée de la table avec style moderne
        if Config.CISS:
            logger.debug("Configuration CISS activée pour les statistiques")
            self.table = RapportCISSTableWidget(parent=self)
        else:
            logger.debug("Configuration standard pour les statistiques")
            self.table = RapportTableWidget(parent=self)

        # Labels modernes pour les champs
        compte_label = QLabel("👤 Compte")
        compte_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        compte_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600;")

        date_debut_label = QLabel("📅 Date début")
        date_debut_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        date_debut_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600;")

        date_fin_label = QLabel("📅 Date fin")
        date_fin_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        date_fin_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600;")

        export_label = QLabel("📤 Export")
        export_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        export_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600;")

        # Conteneur moderne pour les contrôles
        controls_container = QFrame()
        controls_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                padding: 20px;
                margin: 8px 0;
            }}
        """)

        # Mise en page moderne des contrôles
        controls_layout = QGridLayout()
        controls_layout.setSpacing(16)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Première ligne - Labels
        controls_layout.addWidget(compte_label, 0, 0)
        controls_layout.addWidget(date_debut_label, 0, 1)
        controls_layout.addWidget(date_fin_label, 0, 2)
        controls_layout.addWidget(export_label, 0, 3, 1, 2)
        
        # Deuxième ligne - Contrôles
        controls_layout.addWidget(self.compte_field, 1, 0)
        controls_layout.addWidget(self.on_date_field, 1, 1)
        controls_layout.addWidget(self.end_date_field, 1, 2)
        controls_layout.addWidget(self.btt_pdf_export, 1, 3)
        controls_layout.addWidget(self.btt_xlsx_export, 1, 4)
        
        # Espacement flexible
        controls_layout.setColumnStretch(5, 1)
        
        controls_container.setLayout(controls_layout)

        # Conteneur moderne pour la table
        table_container = QFrame()
        table_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                padding: 0;
                margin: 8px 0;
            }}
        """)
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.table)
        table_container.setLayout(table_layout)

        # Ligne de séparation moderne
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['primary_light']},
                    stop:0.5 {COLORS['primary']},
                    stop:1 {COLORS['primary_light']});
                border: none;
                height: 2px;
                margin: 16px 0;
            }}
        """)

        # Mise en page principale moderne
        vbox = QVBoxLayout()
        vbox.setSpacing(16)
        vbox.setContentsMargins(20, 20, 20, 20)
        vbox.addWidget(self.title_field)
        vbox.addWidget(separator)
        vbox.addWidget(controls_container)
        vbox.addWidget(table_container)
        vbox.addWidget(balance_container)
        self.setLayout(vbox)
        
        logger.debug("StatisticsViewWidget initialisé avec succès - Design moderne appliqué")

    def refresh_client_list(self):
        """Rafraîchit la liste des clients avec mise en cache"""
        current_time = datetime.now()
        
        # Utiliser le cache si disponible et récent (moins de 30 secondes)
        if (self._cached_client_list is not None and 
            self._last_client_refresh is not None and 
            (current_time - self._last_client_refresh).total_seconds() < 30):
            self.string_list = self._cached_client_list
            return
        
        # Actualiser la liste
        try:
            client_names = [
                clt.name for clt in ProviderOrClient.select()
                .where(ProviderOrClient.type_ == ProviderOrClient.CLT, 
                       ProviderOrClient.deleted == False)
                .order_by(ProviderOrClient.name.desc())
            ]
            self.string_list = [""] + client_names
            
            # Mettre à jour le cache
            self._cached_client_list = self.string_list
            self._last_client_refresh = current_time
            
            logger.debug(f"Liste des clients rafraîchie: {len(client_names)} clients")
            
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement de la liste des clients: {e}")
            self.string_list = [""]

    def refresh_prov_clt(self):
        """Rafraîchit les données du fournisseur/client sélectionné"""
        logger.debug("Rafraîchissement du client sélectionné")
        
        self.compte_name = self.compte_field.lineEdit().text()
        self.title_field.setText(f"📊 Statistiques - {self.compte_name if self.compte_name else 'Tous'}")
        
        if self.compte_name and self.compte_name != "":
            try:
                self.compte = ProviderOrClient.get(name=self.compte_name)
                logger.debug(f"Client sélectionné: {self.compte_name}")
            except ProviderOrClient.DoesNotExist:
                logger.warning(f"Client non trouvé: {self.compte_name}")
                self.compte = "Tous"
        else:
            self.compte = "Tous"

        self.table.refresh_()

    def export_pdf(self):
        """Export PDF optimisé"""
        logger.debug("Début de l'export PDF des statistiques")
        try:
            from Common.exports_pdf import export_dynamic_data
            export_dynamic_data(self.table.dict_data())
            logger.debug("Export PDF terminé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'export PDF: {e}")

    def export_xlsx(self):
        """Export XLSX optimisé"""
        logger.debug("Début de l'export XLSX des statistiques")
        try:
            from Common.exports_xlsx import export_dynamic_data
            export_dynamic_data(self.table.dict_data())
            logger.debug("Export XLSX terminé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'export XLSX: {e}")

    def display_balance(self, amount_text):
        return f"""
        <div style="text-align: center;">
            <h3 style="margin: 0; color: white; font-weight: 700;">
                💰 Solde du {self.now}
            </h3>
            <h2 style="margin: 8px 0 0 0; color: white; font-weight: 700; font-size: 18px;">
                {amount_text}
            </h2>
        </div>
        """


class RapportCISSTableWidget(FTableWidget):
    def __init__(self, parent, *args, **kwargs):
        logger.debug("Initialisation de RapportCISSTableWidget avec design moderne")
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
        
        # Style moderne pour le tableau CISS
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['surface']};
                border: none;
                border-radius: 0;
                gridline-color: {COLORS['border']};
                selection-background-color: {COLORS['primary_light']};
                font-family: "Segoe UI";
                font-size: 10px;
                alternate-background-color: {COLORS['surface_variant']};
            }}
            QHeaderView::section {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['primary']},
                    stop:1 {COLORS['primary_dark']});
                color: white;
                border: none;
                padding: 12px 8px;
                font-weight: 600;
                font-size: 11px;
                text-align: left;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {COLORS['surface_variant']};
                font-size: 10px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['primary_light']};
                color: white;
            }}
            QTableWidget::item:hover {{
                background-color: {COLORS['surface_variant']};
            }}
        """)
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.popup)

        self.parent = parent

        self.sorter = True
        self.stretch_columns = [0, 1, 2, 3, 4, 5]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r", 5: "r"}
        self.display_vheaders = False
        
        # Configuration moderne du tableau
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, header.ResizeToContents)
        header.setSectionResizeMode(1, header.Stretch)
        header.setSectionResizeMode(2, header.ResizeToContents)
        header.setSectionResizeMode(3, header.ResizeToContents)
        header.setSectionResizeMode(4, header.ResizeToContents)
        header.setSectionResizeMode(5, header.ResizeToContents)
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(self.SelectRows)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
        
        # Initialisation des totaux
        self.totals_weight = 0.0
        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.balance_tt = 0.0
        
        self.refresh_()

    def refresh_(self):
        """Rafraîchissement avec calculs améliorés pour CISS"""
        logger.debug("Rafraîchissement des données CISS")
        
        # Réinitialisation des totaux
        self.totals_weight = 0.0
        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.balance_tt = 0.0
        
        # Récupération des dates
        self.on_date = date_to_datetime(self.parent.on_date_field.text())
        self.end_date = date_to_datetime(self.parent.end_date_field.text())

        self._reset()
        self.set_data_for()
        self.refresh()

        self.parent.balanceField.setText(
            self.parent.display_balance(device_amount(self.balance_tt))
        )

        self.hideColumn(len(self.hheaders) - 1)

    def set_data_for(self):
        """Récupération des données CISS avec calculs optimisés"""
        logger.debug("Récupération des données CISS pour statistiques")
        
        # Construction de la requête
        qs = Payment.select()
        if not isinstance(self.parent.compte, str):
            qs = qs.where(Payment.provider_clt == self.parent.compte)
            logger.debug(f"Filtre sur le client: {self.parent.compte.name}")
        else:
            self.parent.compte = "Tous"
            logger.debug("Affichage de tous les clients")
            
        qs = (
            qs.select()
            .where(
                Payment.status == False,
                Payment.deleted == False,
                Payment.date <= date_on_or_end(self.end_date, on=False),
                Payment.date >= date_on_or_end(self.on_date),
            )
            .order_by(Payment.date.asc())
        )
        
        # Récupération des données brutes
        raw_data = [
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
        
        # Recalcul des balances pour cohérence
        self.data = calculate_running_balance(raw_data)
        
        logger.debug(f"Données CISS récupérées: {len(self.data)} enregistrements")

    def popup(self, pos):
        """Menu contextuel optimisé"""
        from ui.deleteview import DeleteViewWidget

        try:
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
            elif action == delaction:
                self.parent.open_dialog(
                    DeleteViewWidget, modal=True, table_p=self, obj=payment
                )
        except Exception as e:
            logger.error(f"Erreur dans le menu contextuel CISS: {e}")

    def extend_rows(self):
        """Calcul des totaux CISS avec précision améliorée"""
        logger.debug("Calcul des totaux CISS avec poids")
        
        self.parent.btt_pdf_export.setEnabled(True)
        self.parent.btt_xlsx_export.setEnabled(True)
        nb_rows = self.rowCount()
        self.setRowCount(nb_rows + 2)
        self.setSpan(nb_rows + 2, 2, 2, 4)

        # Initialisation des totaux
        self.totals_weight = 0.0
        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.balance_tt = 0.0
        
        # Calcul des totaux à partir des données calculées
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
        if not isinstance(self.parent.compte, str) and self.data:
            # Pour un client spécifique, utiliser la dernière balance calculée
            self.balance_tt = self.data[-1][5] if self.data else 0.0
        else:
            # Pour tous les clients, calculer la différence des totaux
            self.balance_tt = self.totals_credit - self.totals_debit
        
        self.balance_tt = precise_calculation(self.balance_tt)
        
        logger.debug(f"Totaux CISS calculés - Poids: {self.totals_weight}, Débit: {self.totals_debit}, Crédit: {self.totals_credit}, Balance: {self.balance_tt}")

        self.label_mov_tt = u"Totals mouvements: "
        self.setItem(nb_rows, 1, TotalsWidget(self.label_mov_tt))
        self.setItem(
            nb_rows,
            2,
            TotalsWidget(device_amount(self.totals_weight, dvs="Kg", aftergam=3)),
        )
        self.setItem(nb_rows, 3, TotalsWidget(device_amount(self.totals_debit)))
        self.setItem(nb_rows, 4, TotalsWidget(device_amount(self.totals_credit)))

    def dict_data(self):
        """Données d'export CISS optimisées"""
        title = "versements"
        return {
            "file_name": "{}-{}".format(title, self.parent.now),
            "headers": self.hheaders[:-1],
            "data": self.data,
            "extend_rows": [
                (1, self.label_mov_tt),
                (2, device_amount(self.totals_weight, dvs="Kg", aftergam=3)),
                (3, self.totals_debit),
                (4, self.totals_credit),
            ],
            "footers": [
                (
                    "C",
                    "E",
                    "Solde du {} = {}".format(
                        self.end_date.strftime("%x"), device_amount(self.balance_tt)
                    ),
                )
            ],
            "sheet": title,
            "widths": self.stretch_columns,
            "format_money": [
                "C:C",
                "D:D",
                "E:E",
            ],
            "others": [
                ("A7", "C7", "Compte : {}".format(self.parent.compte_name)),
            ],
            "date": "Du {} au {}".format(
                self.on_date.strftime("%x"), self.end_date.strftime("%x")
            ),
        }


class RapportTableWidget(FTableWidget):
    def __init__(self, parent, *args, **kwargs):
        logger.debug("Initialisation de RapportTableWidget avec design moderne")
        FTableWidget.__init__(self, parent=parent, *args, **kwargs)

        self.hheaders = [
            "📅 Date", 
            "📝 Libellé opération", 
            "💸 Débit", 
            "💰 Crédit", 
            "📊 Solde", 
            ""
        ]
        
        # Style moderne pour le tableau standard
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['surface']};
                border: none;
                border-radius: 0;
                gridline-color: {COLORS['border']};
                selection-background-color: {COLORS['primary_light']};
                font-family: "Segoe UI";
                font-size: 10px;
                alternate-background-color: {COLORS['surface_variant']};
            }}
            QHeaderView::section {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['primary']},
                    stop:1 {COLORS['primary_dark']});
                color: white;
                border: none;
                padding: 12px 8px;
                font-weight: 600;
                font-size: 11px;
                text-align: left;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {COLORS['surface_variant']};
                font-size: 10px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['primary_light']};
                color: white;
            }}
            QTableWidget::item:hover {{
                background-color: {COLORS['surface_variant']};
            }}
        """)
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.popup)

        self.parent = parent

        self.stretch_columns = [0, 1, 2, 3, 4]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r"}
        self.display_vheaders = False
        
        # Configuration moderne du tableau
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, header.ResizeToContents)
        header.setSectionResizeMode(1, header.Stretch)
        header.setSectionResizeMode(2, header.ResizeToContents)
        header.setSectionResizeMode(3, header.ResizeToContents)
        header.setSectionResizeMode(4, header.ResizeToContents)
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(self.SelectRows)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
        
        # Initialisation des totaux
        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.balance_tt = 0.0
        
        if not Config.DEVISE_PEP_PROV:
            self.refresh_()

    def refresh_(self):
        """Rafraîchissement avec calculs améliorés"""
        logger.debug("Rafraîchissement des données statistiques")
        
        # Réinitialisation des totaux
        self.totals_debit = 0.0
        self.totals_credit = 0.0
        self.balance_tt = 0.0
        
        # Récupération des dates
        self.on_date = date_to_datetime(self.parent.on_date_field.text())
        self.end_date = date_to_datetime(self.parent.end_date_field.text())

        self._reset()
        self.set_data_for()
        self.refresh()
        self.refresh()

        self.parent.balanceField.setText(
            self.parent.display_balance(device_amount(self.balance_tt))
        )

        self.hideColumn(len(self.hheaders) - 1)

    def set_data_for(self):
        """Récupération des données avec calculs optimisés"""
        logger.debug("Récupération des données pour statistiques")
        
        # Construction de la requête
        qs = Payment.select()
        if not isinstance(self.parent.compte, str):
            qs = qs.where(Payment.provider_clt == self.parent.compte)
            logger.debug(f"Filtre sur le client: {self.parent.compte.name}")
        else:
            self.parent.compte = "Tous"
            logger.debug("Affichage de tous les clients")
            
        qs = (
            qs.select()
            .where(
                Payment.status == False,
                Payment.deleted == False,
                Payment.date <= date_on_or_end(self.end_date, on=False),
                Payment.date >= date_on_or_end(self.on_date),
            )
            .order_by(Payment.date.asc())
        )
        
        # Récupération des données brutes
        raw_data = [
            (pay.date, pay.libelle, pay.debit, pay.credit, pay.balance, pay.id)
            for pay in qs.iterator()
        ]
        
        # Recalcul des balances pour cohérence
        self.data = calculate_running_balance(raw_data)
        
        logger.debug(f"Données récupérées: {len(self.data)} enregistrements")

    def popup(self, pos):
        """Menu contextuel optimisé"""
        from ui.deleteview import DeleteViewWidget

        try:
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
            elif action == delaction:
                self.parent.open_dialog(
                    DeleteViewWidget, modal=True, table_p=self, obj=payment
                )
        except Exception as e:
            logger.error(f"Erreur dans le menu contextuel: {e}")

    def extend_rows(self):
        """Calcul des totaux avec précision améliorée"""
        logger.debug("Calcul des totaux statistiques")
        
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
        if not isinstance(self.parent.compte, str) and self.data:
            # Pour un client spécifique, utiliser la dernière balance calculée
            self.balance_tt = self.data[-1][4] if self.data else 0.0
        else:
            # Pour tous les clients, calculer la différence des totaux
            self.balance_tt = self.totals_credit - self.totals_debit
        
        self.balance_tt = precise_calculation(self.balance_tt)
        
        logger.debug(f"Totaux calculés - Débit: {self.totals_debit}, Crédit: {self.totals_credit}, Balance: {self.balance_tt}")

        self.label_mov_tt = u"Totals mouvements: "
        self.setItem(nb_rows, 1, TotalsWidget(self.label_mov_tt))
        self.setItem(nb_rows, 2, TotalsWidget(device_amount(self.totals_debit)))
        self.setItem(nb_rows, 3, TotalsWidget(device_amount(self.totals_credit)))

    def dict_data(self):
        """Données d'export optimisées"""
        title = "versements"
        return {
            "file_name": "{}-{}".format(title, self.parent.now),
            "headers": self.hheaders[:-1],
            "data": self.data,
            "extend_rows": [
                (1, self.label_mov_tt),
                (2, self.totals_debit),
                (3, self.totals_credit),
            ],
            "footers": [
                (
                    "C",
                    "E",
                    "Solde du {} = {}".format(
                        self.end_date.strftime("%x"), device_amount(self.balance_tt)
                    ),
                ),
            ],
            "sheet": title,
            "widths": self.stretch_columns,
            "format_money": [
                "C:C",
                "D:D",
                "E:E",
            ],
            "others": [
                ("A7", "C7", "Compte : {}".format(self.parent.compte_name)),
            ],
            "date": "Du {} au {}".format(
                self.on_date.strftime("%x"), self.end_date.strftime("%x")
            ),
        }
