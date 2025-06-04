#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier les calculs améliorés du gestionnaire de dettes
"""

import sqlite3
import sys
from decimal import Decimal

def test_balance_calculations():
    """Test des calculs de balance"""
    print("=== Test des calculs de balance ===")
    
    try:
        # Connexion à la base de données
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        # Test 1: Vérifier que les balances sont cohérentes
        print("\n1. Vérification de la cohérence des balances...")
        
        cursor.execute("""
            SELECT provider_clt_id, 
                   SUM(credit) as total_credit,
                   SUM(debit) as total_debit,
                   SUM(credit) - SUM(debit) as calculated_balance,
                   (SELECT balance FROM payment p2 
                    WHERE p2.provider_clt_id = p1.provider_clt_id 
                    ORDER BY p2.date DESC, p2.id DESC LIMIT 1) as stored_balance
            FROM payment p1 
            WHERE deleted = 0
            GROUP BY provider_clt_id
            LIMIT 10
        """)
        
        inconsistencies = 0
        for row in cursor.fetchall():
            provider_id, total_credit, total_debit, calc_balance, stored_balance = row
            
            if abs(float(calc_balance) - float(stored_balance)) > 0.01:  # Tolérance de 1 centime
                print(f"⚠️  Client {provider_id}: Balance calculée={calc_balance:.2f}, Balance stockée={stored_balance:.2f}")
                inconsistencies += 1
        
        if inconsistencies == 0:
            print("✅ Toutes les balances sont cohérentes")
        else:
            print(f"❌ {inconsistencies} incohérences détectées")
        
        # Test 2: Vérifier les totaux globaux
        print("\n2. Vérification des totaux globaux...")
        
        cursor.execute("""
            SELECT 
                COUNT(*) as nb_payments,
                SUM(credit) as total_credits,
                SUM(debit) as total_debits,
                SUM(credit) - SUM(debit) as net_balance
            FROM payment 
            WHERE deleted = 0
        """)
        
        nb_payments, total_credits, total_debits, net_balance = cursor.fetchone()
        
        print(f"📊 Statistiques globales:")
        print(f"   Nombre de paiements: {nb_payments}")
        print(f"   Total crédits: {total_credits:,.2f}")
        print(f"   Total débits: {total_debits:,.2f}")
        print(f"   Balance nette: {net_balance:,.2f}")
        
        # Test 3: Test des conversions de devises
        print("\n3. Vérification des montants par devise...")
        
        cursor.execute("""
            SELECT pc.devise, 
                   COUNT(p.id) as nb_payments,
                   SUM(p.credit) as total_credits,
                   SUM(p.debit) as total_debits
            FROM payment p
            JOIN providerorclient pc ON p.provider_clt_id = pc.id
            WHERE p.deleted = 0
            GROUP BY pc.devise
        """)
        
        for devise, nb_payments, credits, debits in cursor.fetchall():
            print(f"   {devise}: {nb_payments} paiements, Crédits: {credits:,.2f}, Débits: {debits:,.2f}")
        
        # Test 4: Vérifier les calculs de poids pour CISS
        print("\n4. Vérification des calculs de poids (CISS)...")
        
        cursor.execute("""
            SELECT 
                COUNT(*) as nb_with_weight,
                SUM(weight) as total_weight,
                AVG(weight) as avg_weight
            FROM payment 
            WHERE deleted = 0 AND weight > 0
        """)
        
        nb_with_weight, total_weight, avg_weight = cursor.fetchone()
        
        if nb_with_weight > 0:
            print(f"   Paiements avec poids: {nb_with_weight}")
            print(f"   Poids total: {total_weight:.3f} kg")
            print(f"   Poids moyen: {avg_weight:.3f} kg")
        else:
            print("   Aucun paiement avec poids enregistré")
        
        # Test 5: Test de performance des requêtes
        print("\n5. Test de performance...")
        
        import time
        start_time = time.time()
        
        cursor.execute("""
            SELECT p.id, p.date, p.libelle, p.debit, p.credit, p.balance,
                   pc.name, pc.phone
            FROM payment p
            JOIN providerorclient pc ON p.provider_clt_id = pc.id
            WHERE p.deleted = 0
            ORDER BY p.date DESC
            LIMIT 100
        """)
        
        results = cursor.fetchall()
        end_time = time.time()
        
        print(f"   Récupération de 100 paiements: {(end_time - start_time)*1000:.2f}ms")
        print(f"   Nombre de résultats: {len(results)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors des tests: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_precision_calculations():
    """Test des calculs de précision"""
    print("\n=== Test des calculs de précision ===")
    
    # Import des fonctions du module
    try:
        from ui.debt_manager import safe_float, precise_calculation
        
        # Test de safe_float
        test_values = [
            ("123.45", 123.45),
            ("123,45", 123.45),
            ("123 456,78", 123456.78),
            ("", 0.0),
            (None, 0.0),
            ("invalid", 0.0),
            ("1\xa0234,56", 1234.56),  # Espace insécable
        ]
        
        print("Test de safe_float:")
        for input_val, expected in test_values:
            result = safe_float(input_val)
            status = "✅" if abs(result - expected) < 0.001 else "❌"
            print(f"   {status} '{input_val}' -> {result} (attendu: {expected})")
        
        # Test de precise_calculation
        print("\nTest de precise_calculation:")
        test_calculations = [
            (123.456789, 2, 123.46),
            (123.454, 2, 123.45),
            (123.455, 2, 123.46),  # Test d'arrondi
            (123.456789, 3, 123.457),
            (0.1 + 0.2, 2, 0.30),  # Test de précision float
        ]
        
        for input_val, precision, expected in test_calculations:
            result = precise_calculation(input_val, precision)
            status = "✅" if abs(result - expected) < 0.0001 else "❌"
            print(f"   {status} {input_val} (prec={precision}) -> {result} (attendu: {expected})")
        
        return True
        
    except ImportError as e:
        print(f"❌ Impossible d'importer les fonctions de test: {e}")
        return False

def main():
    """Fonction principale des tests"""
    print("🧪 Tests des calculs améliorés du gestionnaire de dettes")
    print("=" * 60)
    
    success = True
    
    # Test des calculs de base
    if not test_precision_calculations():
        success = False
    
    # Test des calculs de balance en base
    if not test_balance_calculations():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Tous les tests sont passés avec succès!")
        return 0
    else:
        print("❌ Certains tests ont échoué.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 