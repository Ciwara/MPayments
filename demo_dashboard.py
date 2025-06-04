#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de démonstration du tableau de bord MPayments
"""

import sys
import os
from datetime import datetime

def test_dashboard():
    """Test du tableau de bord en mode standalone"""
    print("🚀 Démarrage du test du tableau de bord")
    print("=" * 50)
    
    try:
        # Initialisation de l'application Qt
        from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
        
        app = QApplication(sys.argv)
        app.setApplicationName("Test Dashboard MPayments")
        
        print("📊 Vérification de la base de données...")
        
        # Vérification simple de la base de données
        import sqlite3
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM payment WHERE deleted = 0")
            payment_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM providerorclient WHERE deleted = 0")
            client_count = cursor.fetchone()[0]
            
            print(f"✅ Base de données accessible: {payment_count} paiements, {client_count} clients")
            conn.close()
        except Exception as e:
            print(f"❌ Problème avec la base de données: {e}")
            return
        
        # Import du tableau de bord après vérification
        print("🔧 Import du module dashboard...")
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import progressif pour éviter les imports circulaires
        from ui.dashboard import DashboardWidget
        
        # Création de la fenêtre principale
        main_window = QMainWindow()
        main_window.setWindowTitle("📊 Tableau de Bord MPayments - Démonstration")
        main_window.setGeometry(100, 100, 1200, 800)
        
        # Widget central
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # Ajout du dashboard
        print("🔧 Création du tableau de bord...")
        dashboard = DashboardWidget()
        layout.addWidget(dashboard)
        
        central_widget.setLayout(layout)
        main_window.setCentralWidget(central_widget)
        
        # Affichage
        main_window.show()
        print("✅ Tableau de bord affiché avec succès!")
        print("💡 Utilisez Ctrl+C ou fermez la fenêtre pour quitter")
        
        # Démarrage de l'application
        sys.exit(app.exec_())
        
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print("💡 Assurez-vous que tous les modules sont disponibles")
        print("💡 Essayez de lancer l'application principale : python main.py")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def test_imports():
    """Test des imports nécessaires"""
    print("🔍 Test des imports...")
    
    modules_to_test = [
        "PyQt5.QtWidgets",
        "PyQt5.QtCore", 
        "PyQt5.QtGui",
        "models",
        "configuration",
        "data_helper"
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except ImportError as e:
            print(f"   ❌ {module} : {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n⚠️  Modules manquants: {', '.join(failed_imports)}")
        return False
    else:
        print("\n✅ Tous les modules sont disponibles")
        return True

def main():
    """Fonction principale"""
    print("📊 Démonstration du Tableau de Bord MPayments")
    print("=" * 60)
    print(f"🕒 Date/Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    print("\n🎯 Objectifs de cette démonstration:")
    print("   • Tester l'interface du tableau de bord")
    print("   • Vérifier la collecte des données")
    print("   • Valider l'affichage des métriques")
    print("   • Tester les graphiques et tableaux")
    
    print("\n🔍 Vérifications préalables...")
    
    # Test des imports
    if not test_imports():
        print("\n❌ Impossible de continuer à cause des imports manquants")
        print("💡 Lancez l'application principale avec : python main.py")
        return
    
    print("\n🚀 Lancement du test...")
    test_dashboard()

if __name__ == "__main__":
    main() 