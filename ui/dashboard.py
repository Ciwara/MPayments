#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tableau de bord MPayments - Résumé des statistiques et métriques
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QLabel, QFrame, QPushButton, QComboBox, QProgressBar,
    QScrollArea, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon

from Common.ui.common import FWidget
from configuration import Config
from data_helper import device_amount
from models import Payment, ProviderOrClient
from ui.debt_manager import safe_float, precise_calculation

# Configuration du logger
logger = logging.getLogger(__name__)


class MetricsCard(QFrame):
    """Widget carte pour afficher une métrique"""
    
    def __init__(self, title, value, trend=None, color="#2196F3", icon=None):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        
        layout = QVBoxLayout()
        
        # En-tête avec icône
        header_layout = QHBoxLayout()
        
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(QPixmap(icon).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10))
        title_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Valeur principale
        value_label = QLabel(str(value))
        value_label.setFont(QFont("Arial", 18, QFont.Bold))
        value_label.setStyleSheet("color: #333; margin: 5px 0;")
        layout.addWidget(value_label)
        
        # Tendance (optionnel)
        if trend:
            trend_label = QLabel(trend)
            trend_color = "#4CAF50" if trend.startswith("+") else "#F44336"
            trend_label.setStyleSheet(f"color: {trend_color}; font-size: 12px;")
            layout.addWidget(trend_label)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setFixedHeight(120)


class ChartWidget(QFrame):
    """Widget graphique simple"""
    
    def __init__(self, title, data, chart_type="bar"):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Titre du graphique
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_label.setStyleSheet("color: #333; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Zone de graphique simplifié (barres de progression)
        chart_layout = QVBoxLayout()
        
        if data:
            max_value = max(data.values()) if data.values() else 1
            
            for label, value in data.items():
                item_layout = QHBoxLayout()
                
                # Label
                label_widget = QLabel(str(label)[:20])
                label_widget.setMinimumWidth(100)
                label_widget.setStyleSheet("font-size: 10px;")
                item_layout.addWidget(label_widget)
                
                # Barre de progression
                progress = QProgressBar()
                progress.setMaximum(100)
                progress.setValue(int((value / max_value) * 100) if max_value > 0 else 0)
                progress.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        background-color: #f0f0f0;
                        height: 20px;
                    }
                    QProgressBar::chunk {
                        background-color: #2196F3;
                        border-radius: 3px;
                    }
                """)
                item_layout.addWidget(progress)
                
                # Valeur
                value_label = QLabel(f"{value:,.0f}")
                value_label.setMinimumWidth(80)
                value_label.setStyleSheet("font-size: 10px; font-weight: bold;")
                item_layout.addWidget(value_label)
                
                chart_layout.addLayout(item_layout)
        
        layout.addLayout(chart_layout)
        layout.addStretch()
        self.setLayout(layout)


class TopClientsWidget(QTableWidget):
    """Widget pour afficher le top des clients"""
    
    def __init__(self):
        super().__init__()
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Client", "Nb Paiements", "Total Crédit", "Balance"])
        
        # Style du tableau
        self.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                gridline-color: #E0E0E0;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                padding: 8px;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        
        # Redimensionnement automatique
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)


class DataUpdateThread(QThread):
    """Thread pour mettre à jour les données en arrière-plan"""
    
    data_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = True
    
    def run(self):
        """Collecte les données en arrière-plan"""
        try:
            data = self.collect_dashboard_data()
            self.data_updated.emit(data)
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des données: {e}")
    
    def collect_dashboard_data(self):
        """Collecte toutes les données du tableau de bord"""
        logger.debug("Collecte des données du tableau de bord")
        
        data = {
            'clients_count': 0,
            'providers_count': 0,
            'total_payments': 0,
            'total_credit': 0.0,
            'total_debit': 0.0,
            'balance_total': 0.0,
            'monthly_stats': {},
            'top_clients': [],
            'recent_activity': [],
            'payment_trends': {}
        }
        
        try:
            # Statistiques de base
            clients_query = ProviderOrClient.select().where(
                ProviderOrClient.type_ == ProviderOrClient.CLT,
                ProviderOrClient.deleted == False
            )
            data['clients_count'] = clients_query.count()
            
            providers_query = ProviderOrClient.select().where(
                ProviderOrClient.type_ == ProviderOrClient.FSEUR,
                ProviderOrClient.deleted == False
            )
            data['providers_count'] = providers_query.count()
            
            # Statistiques des paiements
            payments_query = Payment.select().where(Payment.deleted == False)
            all_payments = list(payments_query.iterator())
            
            data['total_payments'] = len(all_payments)
            
            for payment in all_payments:
                data['total_credit'] += safe_float(payment.credit)
                data['total_debit'] += safe_float(payment.debit)
            
            data['balance_total'] = data['total_credit'] - data['total_debit']
            
            # Fonction helper pour parser les dates
            def parse_payment_date(payment_date):
                """Parse une date de paiement qui peut être string ou datetime"""
                if payment_date is None:
                    return None
                
                if isinstance(payment_date, str):
                    try:
                        # Essayer différents formats de date
                        formats = [
                            '%Y-%m-%dT%H:%M:%S.%f',      # Format ISO avec microsecondes
                            '%Y-%m-%dT%H:%M:%S',         # Format ISO sans microsecondes
                            '%Y-%m-%d %H:%M:%S.%f',      # Format avec espace et microsecondes
                            '%Y-%m-%d %H:%M:%S',         # Format avec espace sans microsecondes
                            '%Y-%m-%d',                  # Date seulement YYYY-MM-DD
                            '%d/%m/%Y %H:%M:%S',         # Format français avec heure
                            '%d/%m/%Y'                   # Format français sans heure
                        ]
                        
                        for fmt in formats:
                            try:
                                return datetime.strptime(payment_date, fmt).date()
                            except ValueError:
                                continue
                        
                        logger.warning(f"Format de date non reconnu: {payment_date}")
                        return None
                    except Exception as e:
                        logger.warning(f"Erreur lors du parsing de la date {payment_date}: {e}")
                        return None
                elif hasattr(payment_date, 'date'):
                    # Si c'est un objet datetime
                    return payment_date.date()
                elif hasattr(payment_date, 'strftime'):
                    # Si c'est déjà un objet date
                    return payment_date
                else:
                    logger.warning(f"Type de date inattendu: {type(payment_date)} - {payment_date}")
                    return None
            
            # Statistiques mensuelles (6 derniers mois)
            today = date.today()
            for i in range(6):
                month_date = today - timedelta(days=30*i)
                month_key = month_date.strftime("%Y-%m")
                
                month_payments = []
                for p in all_payments:
                    parsed_date = parse_payment_date(p.date)
                    if parsed_date and parsed_date.strftime("%Y-%m") == month_key:
                        month_payments.append(p)
                
                month_credit = sum(safe_float(p.credit) for p in month_payments)
                month_debit = sum(safe_float(p.debit) for p in month_payments)
                
                data['monthly_stats'][month_date.strftime("%b %Y")] = {
                    'count': len(month_payments),
                    'credit': month_credit,
                    'debit': month_debit,
                    'balance': month_credit - month_debit
                }
            
            # Top clients par volume
            client_stats = {}
            for payment in all_payments:
                if payment.provider_clt_id not in client_stats:
                    try:
                        client = ProviderOrClient.get(id=payment.provider_clt_id)
                        if client.deleted:  # Ignorer les clients supprimés
                            continue
                        client_stats[payment.provider_clt_id] = {
                            'name': client.name if client.name else f"Client #{client.id}",
                            'phone': getattr(client, 'phone', 'N/A'),
                            'count': 0,
                            'credit': 0.0,
                            'debit': 0.0
                        }
                    except Exception as e:
                        logger.warning(f"Impossible de récupérer le client {payment.provider_clt_id}: {e}")
                        continue
                
                if payment.provider_clt_id in client_stats:
                    client_stats[payment.provider_clt_id]['count'] += 1
                    client_stats[payment.provider_clt_id]['credit'] += safe_float(payment.credit)
                    client_stats[payment.provider_clt_id]['debit'] += safe_float(payment.debit)
            
            # Trier par balance et prendre le top 10
            if client_stats:
                top_clients = sorted(
                    client_stats.values(),
                    key=lambda x: x['credit'] - x['debit'],
                    reverse=True
                )[:10]
            else:
                top_clients = []
            
            data['top_clients'] = top_clients
            
            logger.debug(f"Données collectées: {data['clients_count']} clients, {data['total_payments']} paiements")
            logger.debug(f"Total crédit: {data['total_credit']}, Total débit: {data['total_debit']}, Balance: {data['balance_total']}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return data
    
    def stop(self):
        self.running = False


class DashboardWidget(FWidget):
    """Widget principal du tableau de bord"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("Initialisation du tableau de bord")
        
        self.data = {}
        self.update_thread = None
        
        # Timer pour mise à jour automatique
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_data)
        self.update_timer.start(30000)  # 30 secondes
        
        self.init_ui()
        self.refresh_data()
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        main_layout = QVBoxLayout()
        
        # En-tête du tableau de bord
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📊 Tableau de Bord MPayments")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #333; margin: 10px 0;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Bouton de rafraîchissement
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        header_layout.addWidget(refresh_btn)
        
        # Sélecteur de période
        period_combo = QComboBox()
        period_combo.addItems(["Aujourd'hui", "Cette semaine", "Ce mois", "6 derniers mois", "Cette année"])
        period_combo.setCurrentText("Ce mois")
        period_combo.currentTextChanged.connect(self.on_period_changed)
        header_layout.addWidget(period_combo)
        
        main_layout.addLayout(header_layout)
        
        # Zone de défilement pour le contenu
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        
        # Section des métriques principales
        metrics_group = QGroupBox("📈 Métriques Principales")
        metrics_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                margin: 10px 0;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        
        metrics_layout = QGridLayout()
        
        # Cartes de métriques
        self.clients_card = MetricsCard("👥 Clients", "0", color="#4CAF50")
        self.payments_card = MetricsCard("💳 Paiements", "0", color="#2196F3")
        self.credit_card = MetricsCard("💰 Total Crédits", "0 F", color="#FF9800")
        self.balance_card = MetricsCard("⚖️ Balance", "0 F", color="#9C27B0")
        
        metrics_layout.addWidget(self.clients_card, 0, 0)
        metrics_layout.addWidget(self.payments_card, 0, 1)
        metrics_layout.addWidget(self.credit_card, 0, 2)
        metrics_layout.addWidget(self.balance_card, 0, 3)
        
        metrics_group.setLayout(metrics_layout)
        content_layout.addWidget(metrics_group)
        
        # Section des graphiques
        charts_group = QGroupBox("📊 Analyse des Tendances")
        charts_group.setStyleSheet(metrics_group.styleSheet())
        charts_layout = QHBoxLayout()
        
        self.monthly_chart = ChartWidget("Évolution Mensuelle", {})
        self.top_clients_chart = ChartWidget("Top Clients par Balance", {})
        
        charts_layout.addWidget(self.monthly_chart)
        charts_layout.addWidget(self.top_clients_chart)
        
        charts_group.setLayout(charts_layout)
        content_layout.addWidget(charts_group)
        
        # Section du top clients
        clients_group = QGroupBox("🏆 Top 10 Clients")
        clients_group.setStyleSheet(metrics_group.styleSheet())
        clients_layout = QVBoxLayout()
        
        self.top_clients_table = TopClientsWidget()
        clients_layout.addWidget(self.top_clients_table)
        
        clients_group.setLayout(clients_layout)
        content_layout.addWidget(clients_group)
        
        # Informations système
        system_group = QGroupBox("ℹ️ Informations Système")
        system_group.setStyleSheet(metrics_group.styleSheet())
        system_layout = QVBoxLayout()
        
        self.system_info = QLabel("Chargement des informations système...")
        self.system_info.setStyleSheet("padding: 10px; background-color: #F5F5F5; border-radius: 4px;")
        system_layout.addWidget(self.system_info)
        
        system_group.setLayout(system_layout)
        content_layout.addWidget(system_group)
        
        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
    
    def refresh_data(self):
        """Lance la mise à jour des données"""
        logger.debug("Démarrage de la mise à jour des données")
        
        if self.update_thread and self.update_thread.isRunning():
            return
        
        self.update_thread = DataUpdateThread()
        self.update_thread.data_updated.connect(self.update_display)
        self.update_thread.start()
    
    def update_display(self, data):
        """Met à jour l'affichage avec les nouvelles données"""
        logger.debug("Mise à jour de l'affichage du tableau de bord")
        
        self.data = data
        
        try:
            # Mise à jour des cartes de métriques avec protection contre les erreurs
            try:
                # Clients card
                clients_labels = self.clients_card.findChildren(QLabel)
                if len(clients_labels) >= 3:
                    clients_labels[0].setText("👥 Clients")
                    clients_labels[2].setText(str(data.get('clients_count', 0)))
                
                # Payments card
                payments_labels = self.payments_card.findChildren(QLabel)
                if len(payments_labels) >= 3:
                    payments_labels[2].setText(str(data.get('total_payments', 0)))
                
                # Credit card
                credit_labels = self.credit_card.findChildren(QLabel)
                if len(credit_labels) >= 3:
                    total_credit = data.get('total_credit', 0)
                    credit_labels[2].setText(device_amount(total_credit))
                
                # Balance card
                balance_labels = self.balance_card.findChildren(QLabel)
                if len(balance_labels) >= 3:
                    balance = data.get('balance_total', 0)
                    balance_labels[2].setText(device_amount(balance))
                    
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour des cartes: {e}")
            
            # Mise à jour des graphiques avec protection contre les erreurs
            try:
                # Préparation des données mensuelles
                monthly_data = {}
                monthly_stats = data.get('monthly_stats', {})
                
                if monthly_stats:
                    for month, stats in monthly_stats.items():
                        if isinstance(stats, dict):
                            monthly_data[month] = stats.get('balance', 0)
                        else:
                            monthly_data[month] = 0
                else:
                    # Données par défaut si aucune donnée n'est disponible
                    for i in range(6):
                        month_date = date.today() - timedelta(days=30*i)
                        monthly_data[month_date.strftime("%b %Y")] = 0
                
                # Recréer le graphique mensuel
                charts_layout = self.monthly_chart.parent().layout()
                if charts_layout:
                    charts_layout.removeWidget(self.monthly_chart)
                    self.monthly_chart.deleteLater()
                    self.monthly_chart = ChartWidget("Évolution Mensuelle (Balance)", monthly_data)
                    charts_layout.insertWidget(0, self.monthly_chart)
                
                # Top clients pour graphique
                top_clients_data = {}
                top_clients = data.get('top_clients', [])
                
                if top_clients:
                    for client in top_clients[:5]:
                        if isinstance(client, dict):
                            balance = client.get('credit', 0) - client.get('debit', 0)
                            name = client.get('name', 'Inconnu')[:15]
                            top_clients_data[name] = balance
                        else:
                            logger.warning(f"Format de client inattendu: {client}")
                else:
                    top_clients_data["Aucun client"] = 0
                
                # Recréer le graphique des top clients
                if charts_layout:
                    charts_layout.removeWidget(self.top_clients_chart)
                    self.top_clients_chart.deleteLater()
                    self.top_clients_chart = ChartWidget("Top 5 Clients (Balance)", top_clients_data)
                    charts_layout.addWidget(self.top_clients_chart)
                    
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour des graphiques: {e}")
            
            # Mise à jour du tableau des top clients
            try:
                top_clients = data.get('top_clients', [])
                self.update_top_clients_table(top_clients)
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour du tableau des clients: {e}")
            
            # Mise à jour des informations système
            try:
                now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                providers_count = data.get('providers_count', 0)
                clients_count = data.get('clients_count', 0)
                total_payments = data.get('total_payments', 0)
                total_credit = data.get('total_credit', 0)
                total_debit = data.get('total_debit', 0)
                balance_total = data.get('balance_total', 0)
                
                system_text = f"""🕒 Dernière mise à jour: {now}
                                👥 Clients: {clients_count:,} | 🏢 Fournisseurs: {providers_count:,}
                                💳 Total paiements: {total_payments:,}
                                💰 Crédits: {device_amount(total_credit)} | 💸 Débits: {device_amount(total_debit)}
                                ⚖️ Balance générale: {device_amount(balance_total)}"""
                
                self.system_info.setText(system_text.strip())
                
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour des informations système: {e}")
                self.system_info.setText(f"Erreur lors de la mise à jour: {e}")
            
            logger.debug("Affichage mis à jour avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'affichage: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def update_top_clients_table(self, top_clients):
        """Met à jour le tableau des top clients"""
        try:
            # Vérifier que top_clients est bien une liste
            if not isinstance(top_clients, list):
                logger.warning(f"top_clients n'est pas une liste: {type(top_clients)}")
                top_clients = []
            
            # Limiter à 10 clients maximum
            top_clients = top_clients[:10]
            
            self.top_clients_table.setRowCount(len(top_clients))
            
            if not top_clients:
                # Afficher une ligne indiquant qu'il n'y a pas de données
                self.top_clients_table.setRowCount(1)
                no_data_item = QTableWidgetItem("Aucune donnée disponible")
                empty_item1 = QTableWidgetItem("-")
                empty_item2 = QTableWidgetItem("-")
                empty_item3 = QTableWidgetItem("-")
                
                self.top_clients_table.setItem(0, 0, no_data_item)
                self.top_clients_table.setItem(0, 1, empty_item1)
                self.top_clients_table.setItem(0, 2, empty_item2)
                self.top_clients_table.setItem(0, 3, empty_item3)
                return
            
            for row, client in enumerate(top_clients):
                try:
                    # Vérifier que client est bien un dictionnaire
                    if not isinstance(client, dict):
                        logger.warning(f"Client invalide à la ligne {row}: {client}")
                        continue
                    
                    # Extraire les données avec des valeurs par défaut
                    name = client.get('name', f'Client #{row + 1}')
                    count = client.get('count', 0)
                    credit = client.get('credit', 0.0)
                    debit = client.get('debit', 0.0)
                    balance = credit - debit
                    
                    # Créer les éléments du tableau
                    name_item = QTableWidgetItem(str(name))
                    count_item = QTableWidgetItem(str(count))
                    credit_item = QTableWidgetItem(device_amount(credit))
                    balance_item = QTableWidgetItem(device_amount(balance))
                    
                    # Coloration de la balance
                    if balance > 0:
                        balance_item.setBackground(QColor("#E8F5E8"))  # Vert clair
                    elif balance < 0:
                        balance_item.setBackground(QColor("#FFE8E8"))  # Rouge clair
                    else:
                        balance_item.setBackground(QColor("#F5F5F5"))  # Gris clair
                    
                    # Ajouter les éléments au tableau
                    self.top_clients_table.setItem(row, 0, name_item)
                    self.top_clients_table.setItem(row, 1, count_item)
                    self.top_clients_table.setItem(row, 2, credit_item)
                    self.top_clients_table.setItem(row, 3, balance_item)
                    
                except Exception as e:
                    logger.error(f"Erreur lors de l'ajout du client à la ligne {row}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du tableau des clients: {e}")
            # En cas d'erreur, afficher au moins une ligne d'erreur
            try:
                self.top_clients_table.setRowCount(1)
                error_item = QTableWidgetItem(f"Erreur: {str(e)}")
                self.top_clients_table.setItem(0, 0, error_item)
                for col in range(1, 4):
                    self.top_clients_table.setItem(0, col, QTableWidgetItem("-"))
            except:
                pass  # Si même ça échoue, on abandonne silencieusement
    
    def on_period_changed(self, period):
        """Gestionnaire du changement de période"""
        logger.debug(f"Changement de période: {period}")
        # TODO: Implémenter le filtrage par période
        self.refresh_data()
    
    def closeEvent(self, event):
        """Nettoyage lors de la fermeture"""
        if self.update_timer:
            self.update_timer.stop()
        
        if self.update_thread and self.update_thread.isRunning():
            self.update_thread.stop()
            self.update_thread.wait(1000)
        
        event.accept() 