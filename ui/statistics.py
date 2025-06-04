#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fad

import logging
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

from PyQt5.QtWidgets import QVBoxLayout, QGridLayout, QMenu
from PyQt5.QtCore import Qt, QDate

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
        logger.debug("Initialisation de StatisticsViewWidget")
        super(StatisticsViewWidget, self).__init__(parent=parent, *args, **kwargs)
        FPeriodHolder.__init__(self, *args, **kwargs)

        self.parent = parent

        self.title = u"Movements"
        self.compte = self.compte_name = "Tous"

        # Optimisation des champs de date
        self.on_date_field = FormatDate(QDate(date.today().year, date.today().month, 1))
        self.on_date_field.dateChanged.connect(self.refresh_prov_clt)
        self.end_date_field = FormatDate(QDate.currentDate())
        self.end_date_field.dateChanged.connect(self.refresh_prov_clt)
        self.now = datetime.now().strftime(Config.DATEFORMAT)
        
        # Configuration optimisée des labels
        self.balanceField = FormLabel("")
        self.balanceField.setFixedHeight(30)
        
        balance_box = QGridLayout()
        balance_box.addWidget(self.balanceField, 0, 3)
        balance_box.setColumnStretch(0, 1)

        # Cache pour optimiser les requêtes fréquentes
        self._cached_client_list = None
        self._last_client_refresh = None
        
        # Récupération optimisée de la liste des clients
        self.refresh_client_list()
        
        self.title_field = FPageTitle("Tous")
        self.title_field.setFixedHeight(40)
        
        self.compte_field = ExtendedComboBox()
        self.compte_field.addItems(self.string_list)
        self.compte_field.setToolTip("Nom du compte")
        self.compte_field.currentIndexChanged.connect(self.refresh_prov_clt)
        self.compte_field.setFixedHeight(35)

        # Configuration optimisée des boutons d'export
        self.btt_pdf_export = BttExportPDF("")
        self.btt_pdf_export.clicked.connect(self.export_pdf)
        self.btt_pdf_export.setFixedSize(40, 30)
        
        self.btt_xlsx_export = BttExportXLSX("")
        self.btt_xlsx_export.clicked.connect(self.export_xlsx)
        self.btt_xlsx_export.setFixedSize(40, 30)

        # Configuration optimisée de la table
        if Config.CISS:
            logger.debug("Configuration CISS activée pour les statistiques")
            self.table = RapportCISSTableWidget(parent=self)
        else:
            logger.debug("Configuration standard pour les statistiques")
            self.table = RapportTableWidget(parent=self)

        # Mise en page optimisée
        editbox = QGridLayout()
        editbox.setSpacing(5)
        editbox.addWidget(self.compte_field, 1, 0)
        editbox.addWidget(FormLabel(u"Date debut"), 1, 1)
        editbox.addWidget(self.on_date_field, 1, 2)
        editbox.addWidget(FormLabel(u"Date fin"), 1, 3)
        editbox.addWidget(self.end_date_field, 1, 4)
        editbox.setColumnStretch(5, 2)
        editbox.addWidget(self.btt_pdf_export, 1, 6)
        editbox.addWidget(self.btt_xlsx_export, 1, 7)

        vbox = QVBoxLayout()
        vbox.setSpacing(5)
        vbox.addWidget(self.title_field)
        vbox.addLayout(editbox)
        vbox.addWidget(self.table)
        vbox.addLayout(balance_box)
        self.setLayout(vbox)
        
        logger.debug("StatisticsViewWidget initialisé avec succès")

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
        self.title_field.setText(self.compte_name if self.compte_name else "Tous")
        
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
        return """ <h2>Solde du {}: <b>{}</b></h2>
               """.format(
            self.now, amount_text
        )


class RapportCISSTableWidget(FTableWidget):
    def __init__(self, parent, *args, **kwargs):
        logger.debug("Initialisation de RapportCISSTableWidget")
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

        self.sorter = True
        self.stretch_columns = [0, 1, 2, 3, 4, 5]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r", 5: "r"}
        self.display_vheaders = False
        
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
        logger.debug("Initialisation de RapportTableWidget")
        FTableWidget.__init__(self, parent=parent, *args, **kwargs)

        self.hheaders = ["Date", "Libelle opération", "Débit", "Crédit", "Solde", ""]
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.popup)

        self.parent = parent

        self.stretch_columns = [0, 1, 2, 3, 4]
        self.align_map = {0: "l", 1: "l", 2: "r", 3: "r", 4: "r"}
        self.display_vheaders = False
        
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
