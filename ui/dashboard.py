#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tableau de bord MPayments - Résumé des statistiques et métriques
Version améliorée avec design moderne
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QLabel, QFrame, QPushButton, QComboBox, QProgressBar,
    QScrollArea, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QLinearGradient, QPainter

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
    'background': '#F8F9FA',
    'surface': '#FFFFFF',
    'surface_variant': '#F5F5F5',
    'text_primary': '#212121',
    'text_secondary': '#757575',
    'border': '#E0E0E0',
    'shadow': 'rgba(0, 0, 0, 0.1)'
}

class MetricsCard(QFrame):
    """Widget carte pour afficher une métrique avec design moderne"""
    
    def __init__(self, title, value, trend=None, color=COLORS['primary'], icon=None):
        super().__init__()
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['surface']},
                    stop:1 {COLORS['surface_variant']});
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                padding: 20px;
                margin: 8px;
                box-shadow: 0 4px 12px {COLORS['shadow']};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # En-tête avec icône
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        # Icône colorée
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(QPixmap(icon).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            header_layout.addWidget(icon_label)
        else:
            # Cercle coloré par défaut
            color_indicator = QLabel()
            color_indicator.setFixedSize(12, 12)
            color_indicator.setStyleSheet(f"""
                background-color: {color};
                border-radius: 6px;
                margin: 4px;
            """)
            header_layout.addWidget(color_indicator)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 600;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Valeur principale avec style amélioré
        value_label = QLabel(str(value))
        value_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        value_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            margin: 8px 0;
            font-weight: 700;
            letter-spacing: -0.5px;
        """)
        layout.addWidget(value_label)
        
        # Tendance avec indicateur visuel
        if trend:
            trend_layout = QHBoxLayout()
            
            # Indicateur de tendance
            trend_indicator = QLabel("↗" if trend.startswith("+") else "↘" if trend.startswith("-") else "→")
            trend_color = COLORS['success'] if trend.startswith("+") else COLORS['error'] if trend.startswith("-") else COLORS['text_secondary']
            trend_indicator.setFont(QFont("Segoe UI", 14))
            trend_indicator.setStyleSheet(f"color: {trend_color};")
            
            trend_label = QLabel(trend)
            trend_label.setFont(QFont("Segoe UI", 10, QFont.Medium))
            trend_label.setStyleSheet(f"color: {trend_color}; font-weight: 500;")
            
            trend_layout.addWidget(trend_indicator)
            trend_layout.addWidget(trend_label)
            trend_layout.addStretch()
            
            layout.addLayout(trend_layout)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setFixedHeight(140)
        
        # Effet hover
        self.setObjectName("metrics_card")


class ChartWidget(QFrame):
    """Widget graphique moderne avec design amélioré"""
    
    def __init__(self, title, data, chart_type="bar"):
        super().__init__()
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                padding: 20px;
                margin: 8px;
                box-shadow: 0 4px 12px {COLORS['shadow']};
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # En-tête du graphique avec style moderne
        header_layout = QHBoxLayout()
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
        title_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            margin-bottom: 16px;
            font-weight: 600;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Badge de nombre d'éléments
        count_badge = QLabel(f"{len(data)} éléments")
        count_badge.setFont(QFont("Segoe UI", 9))
        count_badge.setStyleSheet(f"""
            background-color: {COLORS['primary_light']};
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 500;
        """)
        header_layout.addWidget(count_badge)
        
        layout.addLayout(header_layout)
        
        # Zone de graphique avec barres améliorées
        chart_layout = QVBoxLayout()
        chart_layout.setSpacing(8)
        
        if data:
            max_value = max(data.values()) if data.values() else 1
            
            for i, (label, value) in enumerate(data.items()):
                item_layout = QHBoxLayout()
                item_layout.setSpacing(12)
                
                # Label avec numérotation
                rank_label = QLabel(f"{i+1}")
                rank_label.setFixedSize(24, 24)
                rank_label.setAlignment(Qt.AlignCenter)
                rank_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
                rank_label.setStyleSheet(f"""
                    background-color: {COLORS['primary']};
                    color: white;
                    border-radius: 12px;
                    font-weight: 600;
                """)
                item_layout.addWidget(rank_label)
                
                # Nom du client/période
                label_widget = QLabel(str(label)[:25])
                label_widget.setMinimumWidth(120)
                label_widget.setFont(QFont("Segoe UI", 10, QFont.Medium))
                label_widget.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 500;")
                item_layout.addWidget(label_widget)
                
                # Barre de progression moderne
                progress_container = QFrame()
                progress_container.setStyleSheet(f"""
                    background-color: {COLORS['surface_variant']};
                    border-radius: 8px;
                    margin: 2px 0;
                """)
                progress_container.setFixedHeight(16)
                
                progress = QProgressBar()
                progress.setMaximum(100)
                progress.setValue(int((value / max_value) * 100) if max_value > 0 else 0)
                progress.setTextVisible(False)
                
                # Couleur dégradée pour la barre
                color_intensity = min(255, int(180 + (75 * (value / max_value))))
                progress.setStyleSheet(f"""
                    QProgressBar {{
                        border: none;
                        background-color: {COLORS['surface_variant']};
                        border-radius: 8px;
                        height: 16px;
                    }}
                    QProgressBar::chunk {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 {COLORS['primary']},
                            stop:1 {COLORS['primary_light']});
                        border-radius: 8px;
                        margin: 0;
                    }}
                """)
                item_layout.addWidget(progress, 2)
                
                # Valeur avec formatage amélioré
                if abs(value) >= 1000000:
                    display_value = f"{value/1000000:.1f}M"
                elif abs(value) >= 1000:
                    display_value = f"{value/1000:.1f}K"
                else:
                    display_value = f"{value:.0f}"
                    
                value_label = QLabel(display_value)
                value_label.setMinimumWidth(60)
                value_label.setAlignment(Qt.AlignRight)
                value_label.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
                value_label.setStyleSheet(f"color: {COLORS['primary']}; font-weight: 600;")
                item_layout.addWidget(value_label)
                
                chart_layout.addLayout(item_layout)
        else:
            # Message quand pas de données
            no_data_label = QLabel("📊 Aucune donnée disponible")
            no_data_label.setAlignment(Qt.AlignCenter)
            no_data_label.setFont(QFont("Segoe UI", 12))
            no_data_label.setStyleSheet(f"""
                color: {COLORS['text_secondary']};
                padding: 40px;
                border: 2px dashed {COLORS['border']};
                border-radius: 12px;
                background-color: {COLORS['surface_variant']};
            """)
            chart_layout.addWidget(no_data_label)
        
        layout.addLayout(chart_layout)
        layout.addStretch()
        self.setLayout(layout)


class TopClientsWidget(QTableWidget):
    """Widget tableau moderne pour les top clients"""
    
    def __init__(self):
        super().__init__()
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["👤 Client", "📊 Paiements", "💰 Crédit", "⚖️ Balance"])
        
        # Style moderne du tableau
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                gridline-color: {COLORS['border']};
                selection-background-color: {COLORS['primary_light']};
                font-family: "Segoe UI";
                font-size: 10px;
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
            QHeaderView::section:first {{
                border-top-left-radius: 12px;
            }}
            QHeaderView::section:last {{
                border-top-right-radius: 12px;
            }}
            QTableWidget::item {{
                padding: 12px 8px;
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
        
        # Configuration du tableau
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
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
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Définir le style de fond pour le widget principal
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['background']};
                font-family: "Segoe UI", "Arial", sans-serif;
            }}
        """)
        
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
        title_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            margin: 0;
            font-weight: 700;
            letter-spacing: -0.5px;
        """)
        title_section.addWidget(title_label)
        
        # Badge de statut en temps réel
        status_badge = QLabel("🟢 En ligne")
        status_badge.setFont(QFont("Segoe UI", 10, QFont.Medium))
        status_badge.setStyleSheet(f"""
            background-color: {COLORS['success_light']};
            color: white;
            padding: 6px 12px;
            border-radius: 15px;
            font-weight: 500;
            margin-left: 12px;
        """)
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
        period_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                min-width: 140px;
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
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {COLORS['text_secondary']};
                margin-right: 5px;
            }}
        """)
        controls_layout.addWidget(period_combo)
        
        # Bouton de rafraîchissement avec design moderne
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['primary']},
                    stop:1 {COLORS['primary_dark']});
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 11px;
                min-width: 120px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['primary_light']},
                    stop:1 {COLORS['primary']});
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background: {COLORS['primary_dark']};
                transform: translateY(0px);
            }}
        """)
        controls_layout.addWidget(refresh_btn)
        
        header_layout.addLayout(controls_layout)
        main_layout.addLayout(header_layout)
        
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
                margin: 8px 0;
            }}
        """)
        main_layout.addWidget(separator)
        
        # Zone de défilement avec style moderne
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {COLORS['surface_variant']};
                width: 12px;
                border-radius: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['primary_light']};
                border-radius: 6px;
                min-height: 30px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['primary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(24)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Section des métriques principales avec titre moderne
        metrics_title = QLabel("📈 Métriques Principales")
        metrics_title.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        metrics_title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            margin: 16px 0 8px 0;
            font-weight: 600;
        """)
        content_layout.addWidget(metrics_title)
        
        metrics_group = QFrame()
        metrics_group.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
        """)
        
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
        charts_title = QLabel("📊 Analyse des Tendances")
        charts_title.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        charts_title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            margin: 16px 0 8px 0;
            font-weight: 600;
        """)
        content_layout.addWidget(charts_title)
        
        charts_container = QFrame()
        charts_container.setStyleSheet("QFrame { background-color: transparent; border: none; }")
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(16)
        
        self.monthly_chart = ChartWidget("Évolution Mensuelle", {})
        self.top_clients_chart = ChartWidget("Top Clients par Balance", {})
        
        charts_layout.addWidget(self.monthly_chart)
        charts_layout.addWidget(self.top_clients_chart)
        
        charts_container.setLayout(charts_layout)
        content_layout.addWidget(charts_container)
        
        # Section du top clients avec titre moderne
        clients_title = QLabel("🏆 Top 10 Clients")
        clients_title.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        clients_title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            margin: 16px 0 8px 0;
            font-weight: 600;
        """)
        content_layout.addWidget(clients_title)
        
        clients_container = QFrame()
        clients_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                padding: 0;
                margin: 8px;
            }}
        """)
        clients_layout = QVBoxLayout()
        clients_layout.setContentsMargins(0, 0, 0, 0)
        
        self.top_clients_table = TopClientsWidget()
        clients_layout.addWidget(self.top_clients_table)
        
        clients_container.setLayout(clients_layout)
        content_layout.addWidget(clients_container)
        
        # Informations système avec design moderne
        system_title = QLabel("ℹ️ Informations Système")
        system_title.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        system_title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            margin: 16px 0 8px 0;
            font-weight: 600;
        """)
        content_layout.addWidget(system_title)
        
        system_container = QFrame()
        system_container.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS['surface']},
                    stop:1 {COLORS['surface_variant']});
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                padding: 20px;
                margin: 8px;
            }}
        """)
        system_layout = QVBoxLayout()
        
        self.system_info = QLabel("🔄 Chargement des informations système...")
        self.system_info.setFont(QFont("Segoe UI", 11))
        self.system_info.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            background-color: transparent;
            border: none;
            padding: 0;
            line-height: 24px;
        """)
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