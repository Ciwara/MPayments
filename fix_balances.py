#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour corriger et recalculer toutes les balances dans la base de données
"""

import sqlite3
from datetime import datetime

def fix_all_balances():
    """Recalcule et corrige toutes les balances dans la base de données"""
    print("=== Correction des balances dans la base de données ===")
    
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        # Récupérer tous les clients avec leurs paiements
        cursor.execute("""
            SELECT DISTINCT provider_clt_id 
            FROM payment 
            WHERE deleted = 0
            ORDER BY provider_clt_id
        """)
        
        client_ids = [row[0] for row in cursor.fetchall()]
        print(f"Traitement de {len(client_ids)} clients...")
        
        total_corrected = 0
        
        for client_id in client_ids:
            print(f"\nTraitement du client {client_id}...")
            
            # Récupérer tous les paiements du client par ordre chronologique
            cursor.execute("""
                SELECT id, date, debit, credit, balance
                FROM payment 
                WHERE provider_clt_id = ? AND deleted = 0
                ORDER BY date ASC, id ASC
            """, (client_id,))
            
            payments = cursor.fetchall()
            print(f"  {len(payments)} paiements trouvés")
            
            # Recalculer les balances séquentiellement
            running_balance = 0.0
            corrections = 0
            
            for payment_id, date, debit, credit, stored_balance in payments:
                # Calcul de la nouvelle balance
                running_balance += float(credit) - float(debit)
                new_balance = round(running_balance, 2)
                
                # Vérifier si une correction est nécessaire
                if abs(new_balance - float(stored_balance)) > 0.01:
                    # Mettre à jour la balance
                    cursor.execute("""
                        UPDATE payment 
                        SET balance = ?, last_update_date = ?
                        WHERE id = ?
                    """, (new_balance, datetime.now().isoformat(), payment_id))
                    
                    corrections += 1
                    total_corrected += 1
                    
                    print(f"    Paiement {payment_id}: {stored_balance:.2f} → {new_balance:.2f}")
            
            if corrections > 0:
                print(f"  ✅ {corrections} corrections effectuées pour le client {client_id}")
            else:
                print(f"  ✓ Aucune correction nécessaire pour le client {client_id}")
        
        # Valider les modifications
        conn.commit()
        
        print(f"\n=== RÉSUMÉ ===")
        print(f"✅ {total_corrected} balances corrigées au total")
        print(f"✅ {len(client_ids)} clients traités")
        
        # Vérification finale
        print("\n=== Vérification finale ===")
        cursor.execute("""
            SELECT provider_clt_id,
                   COUNT(*) as nb_payments,
                   SUM(credit) - SUM(debit) as calculated_balance,
                   (SELECT balance FROM payment p2 
                    WHERE p2.provider_clt_id = p1.provider_clt_id 
                    ORDER BY p2.date DESC, p2.id DESC LIMIT 1) as final_balance
            FROM payment p1 
            WHERE deleted = 0
            GROUP BY provider_clt_id
            HAVING ABS(calculated_balance - final_balance) > 0.01
        """)
        
        remaining_issues = cursor.fetchall()
        
        if not remaining_issues:
            print("✅ Toutes les balances sont maintenant cohérentes !")
        else:
            print(f"⚠️  {len(remaining_issues)} incohérences restantes détectées")
            for issue in remaining_issues:
                client_id, nb_payments, calc_balance, final_balance = issue
                print(f"   Client {client_id}: calculé={calc_balance:.2f}, final={final_balance:.2f}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la correction: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def backup_database():
    """Crée une sauvegarde de la base avant modifications"""
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"database_backup_{timestamp}.db"
    
    try:
        shutil.copy2("database.db", backup_name)
        print(f"✅ Sauvegarde créée: {backup_name}")
        return backup_name
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")
        return None

def main():
    """Fonction principale"""
    print("🔧 Outil de correction des balances MPayments")
    print("=" * 50)
    
    # Créer une sauvegarde
    backup_file = backup_database()
    if not backup_file:
        print("⚠️  Impossible de créer une sauvegarde, arrêt du processus")
        return 1
    
    # Demander confirmation
    print("\n⚠️  ATTENTION: Ce script va modifier les balances dans la base de données.")
    print(f"Une sauvegarde a été créée: {backup_file}")
    
    response = input("\nVoulez-vous continuer? (oui/non): ").lower().strip()
    if response not in ['oui', 'o', 'yes', 'y']:
        print("Opération annulée")
        return 0
    
    # Effectuer les corrections
    if fix_all_balances():
        print("\n✅ Correction terminée avec succès !")
        print(f"💾 Sauvegarde disponible: {backup_file}")
        return 0
    else:
        print("\n❌ Erreur pendant la correction")
        print(f"💾 Restaurez la sauvegarde si nécessaire: {backup_file}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 