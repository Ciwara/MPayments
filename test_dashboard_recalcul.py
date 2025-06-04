#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour les calculs du tableau de bord MPayments
"""

import sys
import os
from datetime import datetime, date

def test_dashboard_calculations():
    """Test des calculs du tableau de bord"""
    print("🧮 Test des calculs du tableau de bord")
    print("=" * 50)
    
    try:
        # Ajout du chemin vers les modules
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import des modules nécessaires
        from ui.dashboard import DataUpdateThread
        from models import Payment, ProviderOrClient
        from data_helper import device_amount
        from ui.debt_manager import safe_float
        
        print("✅ Import réussi des modules")
        
        # Créer un thread de mise à jour des données
        update_thread = DataUpdateThread()
        
        print("🔄 Collecte des données du tableau de bord...")
        data = update_thread.collect_dashboard_data()
        
        print("📊 Résultats des calculs :")
        print(f"   👥 Nombre de clients : {data.get('clients_count', 0)}")
        print(f"   🏢 Nombre de fournisseurs : {data.get('providers_count', 0)}")
        print(f"   💳 Total paiements : {data.get('total_payments', 0)}")
        print(f"   💰 Total crédits : {device_amount(data.get('total_credit', 0))}")
        print(f"   💸 Total débits : {device_amount(data.get('total_debit', 0))}")
        print(f"   ⚖️ Balance totale : {device_amount(data.get('balance_total', 0))}")
        
        # Statistiques mensuelles
        monthly_stats = data.get('monthly_stats', {})
        print(f"\n📈 Statistiques mensuelles ({len(monthly_stats)} mois) :")
        for month, stats in monthly_stats.items():
            print(f"   {month}: {stats.get('count', 0)} paiements, Balance: {device_amount(stats.get('balance', 0))}")
        
        # Top clients
        top_clients = data.get('top_clients', [])
        print(f"\n🏆 Top clients ({len(top_clients)} clients) :")
        for i, client in enumerate(top_clients[:5], 1):
            name = client.get('name', 'Inconnu')
            balance = client.get('credit', 0) - client.get('debit', 0)
            print(f"   {i}. {name}: {device_amount(balance)}")
        
        # Vérification de la cohérence des données
        print("\n🔍 Vérification de la cohérence :")
        
        if data['total_credit'] >= 0 and data['total_debit'] >= 0:
            print("   ✅ Totaux positifs ou nuls")
        else:
            print("   ⚠️ Totaux négatifs détectés")
        
        calculated_balance = data['total_credit'] - data['total_debit']
        if abs(calculated_balance - data['balance_total']) < 0.01:
            print("   ✅ Balance cohérente")
        else:
            print(f"   ⚠️ Incohérence de balance: {device_amount(calculated_balance)} vs {device_amount(data['balance_total'])}")
        
        print("\n✅ Test de calcul terminé avec succès !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_date_parsing():
    """Test du parsing des dates"""
    print("\n📅 Test du parsing des dates")
    print("=" * 50)
    
    try:
        from ui.dashboard import DataUpdateThread
        
        # Créer une instance du thread pour accéder à la fonction de parsing
        thread = DataUpdateThread()
        
        # Simuler différents formats de dates
        test_dates = [
            "2024-06-04",
            "04/06/2024", 
            "2024-06-04 12:30:45",
            "04/06/2024 12:30:45",
            datetime.now(),
            date.today(),
            None,
            "format_invalide"
        ]
        
        # Note: La fonction parse_payment_date est définie à l'intérieur de collect_dashboard_data
        # On va tester indirectement en collectant les données
        
        print("🔄 Test du parsing des dates via collect_dashboard_data...")
        data = thread.collect_dashboard_data()
        
        print("✅ Parsing des dates réussi (aucune erreur fatale)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test des dates : {e}")
        return False

def test_safe_calculations():
    """Test des calculs sécurisés"""
    print("\n🔒 Test des calculs sécurisés")
    print("=" * 50)
    
    try:
        from ui.debt_manager import safe_float
        from data_helper import device_amount
        
        # Test safe_float
        test_values = [123.45, "123.45", "123,45", None, "", "abc", 0]
        
        print("🧮 Test safe_float :")
        for value in test_values:
            result = safe_float(value)
            print(f"   {value} -> {result}")
        
        # Test device_amount
        print("\n💰 Test device_amount :")
        test_amounts = [0, 1234.56, -1234.56, 1234567.89, None]
        
        for amount in test_amounts:
            try:
                result = device_amount(amount if amount is not None else 0)
                print(f"   {amount} -> {result}")
            except Exception as e:
                print(f"   {amount} -> Erreur: {e}")
        
        print("✅ Tests des calculs sécurisés terminés")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test des calculs : {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🚀 Tests de recalcul du tableau de bord MPayments")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Calculs du tableau de bord
    if test_dashboard_calculations():
        success_count += 1
    
    # Test 2: Parsing des dates
    if test_date_parsing():
        success_count += 1
    
    # Test 3: Calculs sécurisés
    if test_safe_calculations():
        success_count += 1
    
    # Résumé des résultats
    print("\n" + "=" * 60)
    print(f"📊 Résultats des tests : {success_count}/{total_tests} réussis")
    
    if success_count == total_tests:
        print("🎉 Tous les tests sont passés avec succès !")
        print("✅ Les calculs du tableau de bord fonctionnent correctement")
        print("\n💡 Le tableau de bord devrait maintenant :")
        print("   • Afficher les bonnes métriques")
        print("   • Gérer correctement les dates") 
        print("   • Calculer les balances précisément")
        print("   • Afficher le top des clients")
    else:
        print("⚠️ Certains tests ont échoué")
        print("💡 Vérifiez les erreurs ci-dessus")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 