#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tableau de bord MPayments - Résumé des statistiques et métriques
Version améliorée avec design moderne
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QLabel, QFrame, QPushButton, QComboBox, QProgressBar,
    QScrollArea, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpacerItem, QSizePolicy, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QLinearGradient, QPainter

from Common.ui.common import FWidget
from configuration import Config
from data_helper import device_amount
from models import Payment, ProviderOrClient
from ui.debt_manager import safe_float, precise_calculation

# Configuration du logger
logger = logging.getLogger(__name__)

# Palette de couleurs moderne
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
    'background': '#F0F2F5',
    'surface': '#FFFFFF',
    'surface_variant': '#F5F5F5',
    'text_primary': '#1a1a2e',
    'text_secondary': '#6c757d',
    'border': '#E0E0E0',
    'shadow': 'rgba(0, 0, 0, 0.08)',
}

# Feuille de style globale du dashboard
DASHBOARD_STYLE = f"""
    QWidget#dashboard_root {{
        background-color: {COLORS['background']};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QFrame#metrics_card {{
        background-color: {COLORS['surface']};
        border-radius: 12px;
        border: 1px solid {COLORS['border']};
        padding: 4px;
    }}
    QFrame#metrics_card:hover {{
        border-color: {COLORS['primary_light']};
        background-color: {COLORS['surface']};
    }}
    QFrame#chart_widget {{
        background-color: {COLORS['surface']};
        border-radius: 12px;
        border: 1px solid {COLORS['border']};
        padding: 12px;
    }}
    QFrame#section_title {{
        background: transparent;
        border: none;
    }}
    QPushButton {{
        background-color: {COLORS['primary']};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {COLORS['primary_dark']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['primary_dark']};
    }}
    QComboBox {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 6px 12px;
        min-width: 140px;
    }}
    QComboBox:hover {{
        border-color: {COLORS['primary_light']};
    }}
    QTableWidget {{
        background-color: {COLORS['surface']};
        border-radius: 8px;
        border: 1px solid {COLORS['border']};
        gridline-color: {COLORS['border']};
    }}
    QTableWidget::item {{
        padding: 8px;
    }}
    QHeaderView::section {{
        background-color: {COLORS['surface_variant']};
        padding: 10px;
        border: none;
        border-bottom: 2px solid {COLORS['primary']};
        font-weight: bold;
    }}
    QProgressBar {{
        border: none;
        border-radius: 4px;
        background-color: {COLORS['surface_variant']};
        text-align: center;
    }}
    QProgressBar::chunk {{
        border-radius: 4px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {COLORS['primary_light']}, stop:1 {COLORS['primary']});
    }}
"""

class MetricsCard(QFrame):
    """Widget carte pour afficher une métrique avec design moderne"""
    
    def __init__(self, title, value, trend=None, color=COLORS['primary'], icon=None):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setObjectName("metrics_card")
        self._color = color
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(16, 14, 16, 14)
        
        # En-tête avec icône
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(QPixmap(icon).scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            header_layout.addWidget(icon_label)
        else:
            color_indicator = QLabel()
            color_indicator.setFixedSize(10, 10)
            color_indicator.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
            header_layout.addWidget(color_indicator)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        title_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Valeur principale — référence conservée pour mise à jour
        self.value_label = QLabel(str(value))
        self.value_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(self.value_label)
        
        if trend:
            trend_layout = QHBoxLayout()
            trend_indicator = QLabel("↗" if trend.startswith("+") else "↘" if trend.startswith("-") else "→")
            trend_label = QLabel(trend)
            trend_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            trend_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            trend_layout.addWidget(trend_indicator)
            trend_layout.addWidget(trend_label)
            trend_layout.addStretch()
            layout.addLayout(trend_layout)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setFixedHeight(130)
    
    def set_value(self, text):
        """Met à jour la valeur affichée."""
        self.value_label.setText(str(text))


class ChartWidget(QFrame):
    """Widget graphique moderne avec design amélioré"""
    
    def __init__(self, title, data=None, chart_type="bar"):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setObjectName("chart_widget")
        self._title = title
        self._chart_type = chart_type
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(16)
        self.main_layout.setContentsMargins(16, 14, 16, 14)
        
        # En-tête du graphique
        header_layout = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        self.title_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        self.count_badge = QLabel("0 éléments")
        self.count_badge.setFont(QFont("Segoe UI", 9))
        self.count_badge.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header_layout.addWidget(self.count_badge)
        self.main_layout.addLayout(header_layout)
        
        # Conteneur des barres (réutilisable)
        self.chart_layout = QVBoxLayout()
        self.chart_layout.setSpacing(8)
        self.main_layout.addLayout(self.chart_layout)
        self.main_layout.addStretch()
        self.setLayout(self.main_layout)
        
        self.update_data(data or {})
    
    def _format_value(self, value):
        if abs(value) >= 1_000_000:
            return f"{value/1_000_000:.1f} M"
        if abs(value) >= 1_000:
            return f"{value/1_000:.1f} K"
        return f"{value:.0f}"
    
    def update_data(self, data):
        """Met à jour les données sans recréer le widget."""
        # Supprimer les anciens éléments du chart_layout
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
        
        self.count_badge.setText(f"{len(data)} élément(s)" if data else "0 élément")
        
        if data:
            max_value = max(abs(v) for v in data.values()) if data.values() else 1
            for i, (label, value) in enumerate(data.items()):
                item_layout = QHBoxLayout()
                item_layout.setSpacing(12)
                
                rank_label = QLabel(f"{i+1}")
                rank_label.setFixedSize(24, 24)
                rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                rank_label.setStyleSheet(
                    f"background-color: {COLORS['primary_light']}; color: white; "
                    "border-radius: 12px; font-weight: bold;"
                )
                rank_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                item_layout.addWidget(rank_label)
                
                label_widget = QLabel(str(label)[:25])
                label_widget.setMinimumWidth(100)
                label_widget.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
                item_layout.addWidget(label_widget)
                
                progress = QProgressBar()
                progress.setMaximum(100)
                progress.setValue(int((abs(value) / max_value) * 100) if max_value > 0 else 0)
                progress.setTextVisible(False)
                progress.setFixedHeight(14)
                item_layout.addWidget(progress, 2)
                
                value_label = QLabel(self._format_value(value))
                value_label.setMinimumWidth(56)
                value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                value_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
                value_label.setStyleSheet(f"color: {COLORS['text_primary']};")
                item_layout.addWidget(value_label)
                
                self.chart_layout.addLayout(item_layout)
        else:
            no_data_label = QLabel("📊 Aucune donnée disponible")
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data_label.setFont(QFont("Segoe UI", 12))
            no_data_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            self.chart_layout.addWidget(no_data_label)
    
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())


class TopClientsWidget(QTableWidget):
    """Widget tableau moderne pour les top clients"""
    
    def __init__(self):
        super().__init__()
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["👤 Client", "📊 Paiements", "💰 Crédit", "⚖️ Balance"])
        
        # Style moderne du tableau
        
        # Configuration du tableau
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)


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
    """Widget principal du tableau de bord avec design moderne"""
    
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
        """Initialise l'interface utilisateur moderne"""
        self.setObjectName("dashboard_root")
        self.setStyleSheet(DASHBOARD_STYLE)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # En-tête moderne du tableau de bord
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)
        
        # Section titre avec icône
        title_section = QHBoxLayout()
        title_section.setSpacing(12)
        
        # Icône du dashboard
        dashboard_icon = QLabel("📊")
        dashboard_icon.setFont(QFont("Segoe UI", 20))
        title_section.addWidget(dashboard_icon)
        
        title_label = QLabel("Tableau de Bord MPayments")
        title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_section.addWidget(title_label)
        
        # Badge de statut en temps réel
        status_badge = QLabel("🟢 En ligne")
        status_badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        title_section.addWidget(status_badge)
        
        header_layout.addLayout(title_section)
        header_layout.addStretch()
        
        # Section contrôles
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        
        # Sélecteur de période avec style moderne
        period_combo = QComboBox()
        period_combo.addItems(["Aujourd'hui", "Cette semaine", "Ce mois", "6 derniers mois", "Cette année"])
        period_combo.setCurrentText("Ce mois")
        period_combo.currentTextChanged.connect(self.on_period_changed)
        controls_layout.addWidget(period_combo)
        
        # Bouton de rafraîchissement avec design moderne
        self.refresh_btn = QPushButton("🔄 Actualiser")
        self.refresh_btn.clicked.connect(self.refresh_data)
        controls_layout.addWidget(self.refresh_btn)
        
        header_layout.addLayout(controls_layout)
        main_layout.addLayout(header_layout)
        
        # Ligne de séparation moderne
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(separator)
        
        # Zone de défilement avec style moderne
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(24)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Section des métriques principales avec titre moderne
        metrics_title = QLabel("📈 Métriques principales")
        metrics_title.setObjectName("section_title")
        metrics_title.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        metrics_title.setStyleSheet(f"color: {COLORS['text_primary']}; margin-bottom: 4px;")
        content_layout.addWidget(metrics_title)
        
        metrics_group = QFrame()
        
        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(16)
        
        # Cartes de métriques avec nouvelles couleurs
        self.clients_card = MetricsCard("👥 Clients Actifs", "0", color=COLORS['success'])
        self.payments_card = MetricsCard("💳 Total Paiements", "0", color=COLORS['info'])
        self.credit_card = MetricsCard("💰 Crédits Totaux", "0 F", color=COLORS['warning'])
        self.balance_card = MetricsCard("⚖️ Balance Générale", "0 F", color=COLORS['primary'])
        
        metrics_layout.addWidget(self.clients_card, 0, 0)
        metrics_layout.addWidget(self.payments_card, 0, 1)
        metrics_layout.addWidget(self.credit_card, 0, 2)
        metrics_layout.addWidget(self.balance_card, 0, 3)
        
        metrics_group.setLayout(metrics_layout)
        content_layout.addWidget(metrics_group)
        
        # Section des graphiques avec titre moderne
        charts_title = QLabel("📊 Analyse des tendances")
        charts_title.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        charts_title.setStyleSheet(f"color: {COLORS['text_primary']}; margin-bottom: 4px;")
        content_layout.addWidget(charts_title)
        
        charts_container = QFrame()
        charts_container.setObjectName("chart_widget")
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(20)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        
        self.monthly_chart = ChartWidget("Évolution mensuelle (balance)", {})
        self.top_clients_chart = ChartWidget("Top 5 clients (balance)", {})
        
        charts_layout.addWidget(self.monthly_chart, 1)
        charts_layout.addWidget(self.top_clients_chart, 1)
        
        charts_container.setLayout(charts_layout)
        content_layout.addWidget(charts_container)
        
        # Section du top clients avec titre moderne
        clients_title = QLabel("🏆 Top 10 clients")
        clients_title.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        clients_title.setStyleSheet(f"color: {COLORS['text_primary']}; margin-bottom: 4px;")
        content_layout.addWidget(clients_title)
        
        clients_container = QFrame()
        clients_layout = QVBoxLayout()
        clients_layout.setContentsMargins(0, 0, 0, 0)
        
        self.top_clients_table = TopClientsWidget()
        clients_layout.addWidget(self.top_clients_table)
        
        clients_container.setLayout(clients_layout)
        content_layout.addWidget(clients_container)
        
        # Informations système avec design moderne
        system_title = QLabel("ℹ️ Informations système")
        system_title.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        system_title.setStyleSheet(f"color: {COLORS['text_primary']}; margin-bottom: 4px;")
        content_layout.addWidget(system_title)
        
        system_container = QFrame()
        system_container.setObjectName("chart_widget")
        system_layout = QVBoxLayout()
        system_layout.setContentsMargins(16, 12, 16, 12)
        
        self.system_info = QLabel("🔄 Chargement des informations...")
        self.system_info.setFont(QFont("Segoe UI", 11))
        self.system_info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.system_info.setWordWrap(True)
        system_layout.addWidget(self.system_info)
        
        system_container.setLayout(system_layout)
        content_layout.addWidget(system_container)
        
        # Espacement final
        content_layout.addStretch()
        
        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
    
    def refresh_data(self):
        """Lance la mise à jour des données"""
        logger.debug("Démarrage de la mise à jour des données")
        
        if self.update_thread and self.update_thread.isRunning():
            return
        
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("⏳ Actualisation...")
        
        self.update_thread = DataUpdateThread()
        self.update_thread.data_updated.connect(self._on_data_updated)
        self.update_thread.start()
    
    def _on_data_updated(self, data):
        """Réactive le bouton puis met à jour l'affichage."""
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("🔄 Actualiser")
        self.update_display(data)
    
    def update_display(self, data):
        """Met à jour l'affichage avec les nouvelles données"""
        logger.debug("Mise à jour de l'affichage du tableau de bord")
        
        self.data = data
        
        try:
            # Mise à jour des cartes de métriques via set_value (référence stable)
            try:
                self.clients_card.set_value(data.get('clients_count', 0))
                self.payments_card.set_value(data.get('total_payments', 0))
                self.credit_card.set_value(device_amount(data.get('total_credit', 0)))
                balance = data.get('balance_total', 0)
                self.balance_card.set_value(device_amount(balance))
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour des cartes: {e}")
            
            # Mise à jour des graphiques sans recréer les widgets
            try:
                monthly_stats = data.get('monthly_stats', {})
                monthly_data = {}
                if monthly_stats:
                    for month, stats in monthly_stats.items():
                        monthly_data[month] = stats.get('balance', 0) if isinstance(stats, dict) else 0
                else:
                    for i in range(6):
                        month_date = date.today() - timedelta(days=30 * i)
                        monthly_data[month_date.strftime("%b %Y")] = 0
                
                self.monthly_chart.update_data(monthly_data)
                
                top_clients = data.get('top_clients', [])
                top_clients_data = {}
                if top_clients:
                    for client in top_clients[:5]:
                        if isinstance(client, dict):
                            balance = client.get('credit', 0) - client.get('debit', 0)
                            top_clients_data[client.get('name', 'Inconnu')[:15]] = balance
                else:
                    top_clients_data["Aucun client"] = 0
                
                self.top_clients_chart.update_data(top_clients_data)
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
                
                system_text = (
                    f"🕒 Dernière mise à jour : {now}\n"
                    f"👥 Clients : {clients_count:,}  |  🏢 Fournisseurs : {providers_count:,}\n"
                    f"💳 Total paiements : {total_payments:,}\n"
                    f"💰 Crédits : {device_amount(total_credit)}  |  💸 Débits : {device_amount(total_debit)}\n"
                    f"⚖️ Balance générale : {device_amount(balance_total)}"
                )
                self.system_info.setText(system_text)
                
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