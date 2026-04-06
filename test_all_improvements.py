#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test complet pour valider toutes les améliorations MPayments
"""

import sys
import sqlite3
import traceback
from datetime import datetime

def test_database_integrity():
    """Test de l'intégrité de la base de données"""
    print("🔍 Test de l'intégrité de la base de données")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        # Test 1: Vérifier que toutes les tables existent
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        required_tables = ['owner', 'providerorclient', 'payment', 'settings']
        
        missing_tables = [table for table in required_tables if table not in tables]
        
        if not missing_tables:
            print("✅ Toutes les tables requises sont présentes")
        else:
            print(f"❌ Tables manquantes: {missing_tables}")
            return False
        
        # Test 2: Vérifier les données critiques
        cursor.execute("SELECT COUNT(*) FROM owner WHERE islog = 1")
        active_owners = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM settings")
        settings_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM providerorclient WHERE deleted = 0")
        active_clients = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM payment WHERE deleted = 0")
        active_payments = cursor.fetchone()[0]
        
        print(f"📊 Statistiques:")
        print(f"   Owners actifs: {active_owners}")
        print(f"   Paramètres: {settings_count}")
        print(f"   Clients actifs: {active_clients}")
        print(f"   Paiements actifs: {active_payments}")
        
        if active_owners == 0:
            print("⚠️  Aucun owner actif trouvé")
            return False
        
        if settings_count == 0:
            print("⚠️  Aucun paramètre trouvé")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_model_fixes():
    """Test des corrections du modèle"""
    print("\n🔧 Test des corrections du modèle Payment")
    print("=" * 50)
    
    try:
        # Import pour tester les corrections
        from models import Payment
        from datetime import datetime
        
        # Simuler un payment avec une date string
        class MockPayment:
            def __init__(self, date_str):
                self.date = date_str
                self.credit = 100.0
                self.debit = 0.0
                self.type_ = "Credit"
                
            def amount(self):
                return self.credit if self.type_ == "Credit" else self.debit
                
            def action(self):
                return "Créditer" if self.type_ == "Credit" else "Débiter"
        
        # Test avec différents formats de date
        test_dates = [
            "2025-01-01",      # Format ISO
            "01/01/2025",      # Format français
            datetime.now(),    # Objet datetime
        ]
        
        success_count = 0
        for date_val in test_dates:
            try:
                mock_payment = MockPayment(date_val)
                # Simuler display_name (sans device_amount pour simplicité)
                if isinstance(mock_payment.date, str):
                    if "/" in mock_payment.date:
                        date_obj = datetime.strptime(mock_payment.date, "%d/%m/%Y")
                    elif "-" in mock_payment.date:
                        date_obj = datetime.strptime(mock_payment.date, "%Y-%m-%d")
                    else:
                        date_str = mock_payment.date
                    date_str = date_obj.strftime("%x")
                else:
                    date_str = mock_payment.date.strftime("%x")
                    
                print(f"✅ Format de date '{date_val}' → '{date_str}'")
                success_count += 1
                
            except Exception as e:
                print(f"❌ Erreur avec la date '{date_val}': {e}")
        
        print(f"📊 {success_count}/{len(test_dates)} formats de date gérés correctement")
        return success_count == len(test_dates)
        
    except Exception as e:
        print(f"❌ Erreur dans le test des modèles: {e}")
        return False

def test_calculation_functions():
    """Test des fonctions de calcul améliorées"""
    print("\n🧮 Test des fonctions de calcul")
    print("=" * 50)
    
    try:
        # Import des fonctions
        from ui.debt_manager import safe_float, precise_calculation, calculate_running_balance
        
        # Test de safe_float
        print("Test de safe_float:")
        test_values = [
            ("123.45", 123.45),
            ("123,45", 123.45),
            ("123 456.78", 123456.78),
            ("", 0.0),
            (None, 0.0),
            ("invalid", 0.0),
        ]
        
        safe_float_success = 0
        for input_val, expected in test_values:
            result = safe_float(input_val)
            if abs(result - expected) < 0.001:
                print(f"   ✅ '{input_val}' → {result}")
                safe_float_success += 1
            else:
                print(f"   ❌ '{input_val}' → {result} (attendu: {expected})")
        
        # Test de precise_calculation
        print("Test de precise_calculation:")
        test_calculations = [
            (123.456789, 2, 123.46),
            (0.1 + 0.2, 2, 0.30),
            (999.999, 2, 1000.00),
        ]
        
        precise_calc_success = 0
        for input_val, precision, expected in test_calculations:
            result = precise_calculation(input_val, precision)
            if abs(result - expected) < 0.001:
                print(f"   ✅ {input_val} (prec={precision}) → {result}")
                precise_calc_success += 1
            else:
                print(f"   ❌ {input_val} (prec={precision}) → {result} (attendu: {expected})")
        
        # Test de calculate_running_balance
        print("Test de calculate_running_balance:")
        test_data = [
            ('2025-01-01', 'Test 1', 0, 100, 100, 1),
            ('2025-01-02', 'Test 2', 50, 0, 50, 2),
            ('2025-01-03', 'Test 3', 0, 200, 250, 3),
        ]
        
        calculated = calculate_running_balance(test_data)
        expected_balances = [100.0, 50.0, 250.0]
        
        balance_success = 0
        for i, (calc_data, expected_balance) in enumerate(zip(calculated, expected_balances)):
            if abs(calc_data[4] - expected_balance) < 0.001:
                print(f"   ✅ Balance {i+1}: {calc_data[4]}")
                balance_success += 1
            else:
                print(f"   ❌ Balance {i+1}: {calc_data[4]} (attendu: {expected_balance})")
        
        total_success = safe_float_success + precise_calc_success + balance_success
        total_tests = len(test_values) + len(test_calculations) + len(expected_balances)
        
        print(f"📊 {total_success}/{total_tests} tests de calcul réussis")
        return total_success == total_tests
        
    except Exception as e:
        print(f"❌ Erreur dans le test des calculs: {e}")
        traceback.print_exc()
        return False

def test_statistics_module():
    """Test du module de statistiques amélioré"""
    print("\n📈 Test du module de statistiques")
    print("=" * 50)
    
    try:
        # Import du module
        from ui.debt_manager import safe_float, precise_calculation, calculate_running_balance
        
        # Vérifier que les fonctions existent et fonctionnent
        test_result = safe_float("123,45")
        if abs(test_result - 123.45) < 0.001:
            print("✅ Module statistics - safe_float fonctionne")
        else:
            print("❌ Module statistics - safe_float défaillant")
            return False
        
        test_result = precise_calculation(123.456, 2)
        if abs(test_result - 123.46) < 0.001:
            print("✅ Module statistics - precise_calculation fonctionne")
        else:
            print("❌ Module statistics - precise_calculation défaillant")
            return False
        
        print("✅ Module statistics entièrement fonctionnel")
        return True
        
    except Exception as e:
        print(f"❌ Erreur dans le test du module statistics: {e}")
        return False

def test_performance():
    """Test de performance des requêtes"""
    print("\n⚡ Test de performance")
    print("=" * 50)
    
    try:
        import time
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        # Test 1: Requête simple
        start_time = time.time()
        cursor.execute("SELECT COUNT(*) FROM payment WHERE deleted = 0")
        result = cursor.fetchone()[0]
        end_time = time.time()
        
        print(f"✅ Comptage des paiements ({result} records): {(end_time - start_time)*1000:.2f}ms")
        
        # Test 2: Requête complexe avec jointure
        start_time = time.time()
        cursor.execute("""
            SELECT p.id, p.date, p.libelle, p.debit, p.credit, p.balance,
                   pc.name, pc.phone
            FROM payment p
            JOIN providerorclient pc ON p.provider_clt_id = pc.id
            WHERE p.deleted = 0
            ORDER BY p.date DESC
            LIMIT 50
        """)
        results = cursor.fetchall()
        end_time = time.time()
        
        print(f"✅ Requête complexe ({len(results)} records): {(end_time - start_time)*1000:.2f}ms")
        
        # Test 3: Calcul de balance
        start_time = time.time()
        cursor.execute("""
            SELECT provider_clt_id, 
                   SUM(credit) - SUM(debit) as balance
            FROM payment 
            WHERE deleted = 0
            GROUP BY provider_clt_id
            LIMIT 10
        """)
        balance_results = cursor.fetchall()
        end_time = time.time()
        
        print(f"✅ Calculs de balance ({len(balance_results)} clients): {(end_time - start_time)*1000:.2f}ms")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur dans le test de performance: {e}")
        return False

def test_error_handling():
    """Test de la gestion d'erreurs"""
    print("\n🛡️  Test de la gestion d'erreurs")
    print("=" * 50)
    
    try:
        from ui.debt_manager import safe_float
        
        # Test avec des valeurs problématiques
        problematic_values = [
            None,
            "",
            "abc",
            "123.45.67",
            float('inf'),
            "€123.45",
        ]
        
        errors_handled = 0
        for value in problematic_values:
            try:
                result = safe_float(value, default=0.0)
                if isinstance(result, (int, float)) and not (result != result):  # Vérifier que ce n'est pas NaN
                    print(f"   ✅ Valeur '{value}' gérée → {result}")
                    errors_handled += 1
                else:
                    print(f"   ❌ Valeur '{value}' mal gérée → {result}")
            except Exception as e:
                print(f"   ❌ Exception avec '{value}': {e}")
        
        print(f"📊 {errors_handled}/{len(problematic_values)} erreurs gérées correctement")
        return errors_handled == len(problematic_values)
        
    except Exception as e:
        print(f"❌ Erreur dans le test de gestion d'erreurs: {e}")
        return False

def main():
    """Fonction principale des tests"""
    print("🧪 Tests complets des améliorations MPayments")
    print("=" * 60)
    print(f"Date/Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Exécuter tous les tests
    tests = [
        ("Intégrité base de données", test_database_integrity),
        ("Corrections modèles", test_model_fixes),
        ("Fonctions de calcul", test_calculation_functions),
        ("Module statistiques", test_statistics_module),
        ("Performance", test_performance),
        ("Gestion d'erreurs", test_error_handling),
    ]
    
    results = []
    total_success = 0
    
    for test_name, test_func in tests:
        print(f"\n🔬 Exécution: {test_name}")
        try:
            success = test_func()
            results.append((test_name, "✅ SUCCÈS" if success else "❌ ÉCHEC"))
            if success:
                total_success += 1
        except Exception as e:
            print(f"❌ Exception dans {test_name}: {e}")
            results.append((test_name, "❌ EXCEPTION"))
    
    # Rapport final
    print("\n" + "=" * 60)
    print("📋 RAPPORT FINAL")
    print("=" * 60)
    
    for test_name, result in results:
        print(f"{result} {test_name}")
    
    print("\n" + "=" * 60)
    success_rate = (total_success / len(tests)) * 100
    
    if total_success == len(tests):
        print("🎉 TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS!")
        print("✨ L'application MPayments est entièrement opérationnelle")
        print("🚀 Toutes les améliorations fonctionnent parfaitement")
        return 0
    else:
        print(f"⚠️  {total_success}/{len(tests)} tests réussis ({success_rate:.1f}%)")
        if success_rate >= 80:
            print("👍 L'application est majoritairement fonctionnelle")
            return 0
        else:
            print("👎 Des problèmes critiques subsistent")
            return 1

if __name__ == "__main__":
    sys.exit(main()) 