#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Script fixture pour créer des données de test MPayments

import sqlite3
import random
from datetime import datetime, timedelta

# Données pour la génération de fixtures
PRENOMS = [
    "Amadou", "Fatou", "Moussa", "Aissatou", "Ousmane", "Mariama", "Ibrahima", "Kadiatou",
    "Mamadou", "Fatoumata", "Sekou", "Hawa", "Alpha", "Safiatou", "Boubacar", "Aminata",
    "Lansana", "Djénéba", "Mohamed", "Rokiatou", "Saliou", "Mariam", "Fodé", "Bineta",
    "Thierno", "Adama", "Souleymane", "Oumou", "Abdoulaye", "Coumba"
]

NOMS = [
    "Diallo", "Bah", "Barry", "Camara", "Diané", "Condé", "Sylla", "Keita",
    "Touré", "Cissé", "Kaba", "Bangoura", "Soumah", "Fofana", "Traoré", "Sangaré",
    "Doumbouya", "Konaté", "Diabaté", "Savané", "Kourouma", "Baldé", "Dramé", "Kone",
    "Sidibé", "Doumbias", "Kamara", "Yansané", "Koivogui", "Millimono"
]

VILLES = [
    "Conakry", "Kankan", "Labé", "Nzérékoré", "Kindia", "Mamou", "Boké", "Faranah",
    "Siguiri", "Kouroussa", "Dabola", "Dinguiraye", "Télimélé", "Pita", "Dalaba",
    "Mali", "Tougué", "Lélouma", "Gaoual", "Koundara", "Kamsar", "Fria", "Boffa",
    "Dubreka", "Coyah", "Forecariah", "Macenta", "Guéckédou", "Kissidougou", "Beyla"
]

LIBELLES_CREDIT = [
    "Vente marchandises", "Paiement facture", "Règlement client", "Encaissement vente",
    "Paiement comptant", "Règlement commande", "Vente au détail", "Facturation service",
    "Encaissement créance", "Paiement livraison", "Règlement prestation", "Vente produits",
    "Paiement services", "Facturation client", "Encaissement vente"
]

LIBELLES_DEBIT = [
    "Achat marchandises", "Paiement fournisseur", "Règlement facture", "Achat stock",
    "Paiement commande", "Règlement livraison", "Achat matériel", "Paiement service",
    "Règlement dette", "Achat produits", "Paiement prestation", "Règlement charge",
    "Achat fournitures", "Paiement transport", "Règlement frais"
]

def generate_phone():
    """Génère un numéro de téléphone guinéen réaliste"""
    prefixes = ["620", "621", "622", "623", "624", "625", "626", "627", "628", "629",
                "660", "661", "662", "663", "664", "665", "666", "667", "668", "669"]
    prefix = random.choice(prefixes)
    number = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    return int(prefix + number)

def generate_email(nom, prenom):
    """Génère un email réaliste"""
    domains = ["gmail.com", "yahoo.fr", "hotmail.com", "orange-guinee.com", "sotelgui.net.gn"]
    separators = [".", "_", ""]
    
    sep = random.choice(separators)
    domain = random.choice(domains)
    
    email = f"{prenom.lower()}{sep}{nom.lower()}@{domain}"
    return email

def create_tables_if_not_exist(cursor):
    """Crée les tables si elles n'existent pas"""
    print("Vérification/création des tables...")
    
    # Table Owner (nécessaire pour les paiements)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS owner (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255) UNIQUE NOT NULL,
            islog INTEGER DEFAULT 0,
            "group" VARCHAR(255) DEFAULT 'users',
            phone VARCHAR(20),
            password VARCHAR(255),
            isactive INTEGER DEFAULT 1,
            last_login DATETIME,
            login_count INTEGER DEFAULT 0,
            is_syncro INTEGER DEFAULT 0,
            last_update_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table ProviderOrClient
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS providerorclient (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) UNIQUE NOT NULL,
            address TEXT,
            phone INTEGER,
            email VARCHAR(255),
            legal_infos TEXT,
            type_ VARCHAR(30) DEFAULT 'Client',
            picture_id INTEGER,
            devise VARCHAR(10) DEFAULT 'xof',
            deleted INTEGER DEFAULT 0,
            is_syncro INTEGER DEFAULT 0,
            last_update_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table Payment
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            provider_clt_id INTEGER NOT NULL,
            date DATETIME NOT NULL,
            debit REAL NOT NULL DEFAULT 0,
            credit REAL NOT NULL DEFAULT 0,
            libelle VARCHAR(255),
            balance REAL NOT NULL DEFAULT 0,
            weight REAL DEFAULT 0,
            type_ VARCHAR(10) NOT NULL,
            deleted INTEGER DEFAULT 0,
            status INTEGER DEFAULT 0,
            is_syncro INTEGER DEFAULT 0,
            last_update_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            name VARCHAR(255),
            FOREIGN KEY (owner_id) REFERENCES owner (id),
            FOREIGN KEY (provider_clt_id) REFERENCES providerorclient (id)
        )
    """)
    
    # Table Settings (nécessaire pour l'application)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            is_syncro INTEGER NOT NULL DEFAULT 0,
            last_update_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            slug VARCHAR(255) NOT NULL UNIQUE,
            is_login INTEGER NOT NULL DEFAULT 0,
            after_cam INTEGER NOT NULL DEFAULT 2,
            toolbar INTEGER NOT NULL DEFAULT 1,
            toolbar_position VARCHAR(255) NOT NULL DEFAULT 'TOP',
            url VARCHAR(255) NOT NULL DEFAULT '',
            theme VARCHAR(255) NOT NULL DEFAULT 'default',
            devise VARCHAR(255) NOT NULL DEFAULT 'xof'
        )
    """)
    
    print("✓ Tables vérifiées/créées")

def ensure_default_owner(cursor):
    """S'assure qu'un Owner par défaut existe"""
    # Vérifier si un Owner avec islog=1 existe
    cursor.execute("SELECT id FROM owner WHERE islog = 1 LIMIT 1")
    owner = cursor.fetchone()
    
    if not owner:
        print("Création d'un Owner par défaut...")
        try:
            from datetime import datetime
            current_time = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO owner 
                (username, islog, "group", phone, password, isactive, 
                 last_login, login_count, is_syncro, last_update_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "admin", 1, "administrators", "0000000000", "admin123", 
                1, current_time, 0, 0, current_time
            ))
            owner_id = cursor.lastrowid
            print(f"✓ Owner par défaut créé avec ID: {owner_id}")
            return owner_id
        except Exception as e:
            print(f"❌ Erreur création Owner: {str(e)}")
            return None
    else:
        owner_id = owner[0]
        print(f"✓ Owner existant trouvé avec ID: {owner_id}")
        return owner_id

def ensure_default_settings(cursor):
    """S'assure que les paramètres par défaut existent"""
    # Vérifier si des paramètres existent
    cursor.execute("SELECT COUNT(*) FROM settings")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("Création des paramètres par défaut...")
        try:
            from datetime import datetime
            current_time = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO settings 
                (is_syncro, last_update_date, slug, is_login, after_cam, toolbar, 
                 toolbar_position, url, theme, devise)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                0, current_time, "default", 0, 2, 1, 
                "TOP", "", "default", "xof"
            ))
            print("✓ Paramètres par défaut créés")
        except Exception as e:
            print(f"❌ Erreur création paramètres: {str(e)}")
    else:
        print(f"✓ Paramètres existants trouvés ({count} entrées)")

def create_fixture_data(num_clients=20, num_payments_per_client=30, reset_data=True):
    """Crée les données de fixture"""
    db_path = "database.db"
    
    try:
        print(f"=== Création de {num_clients} clients avec {num_payments_per_client} paiements chacun ===")
        print("Connexion à la base de données...")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Créer les tables si elles n'existent pas
        create_tables_if_not_exist(cursor)
        
        # S'assurer qu'un Owner par défaut existe
        owner_id = ensure_default_owner(cursor)
        if not owner_id:
            print("❌ Impossible de créer ou récupérer un Owner")
            return False
        
        # S'assurer que les paramètres par défaut existent
        ensure_default_settings(cursor)
        
        # Nettoyer les données existantes si demandé
        if reset_data:
            print("Nettoyage des données existantes...")
            cursor.execute("DELETE FROM payment")
            cursor.execute("DELETE FROM providerorclient")
        
        conn.commit()
        
        # Créer les ProviderOrClient
        print(f"Création de {num_clients} ProviderOrClient...")
        client_ids = []
        
        for i in range(num_clients):
            prenom = random.choice(PRENOMS)
            nom = random.choice(NOMS)
            ville = random.choice(VILLES)
            
            # 75% clients, 25% fournisseurs
            type_client = "Client" if i < (num_clients * 0.75) else "Fournisseur"
            
            phone = generate_phone()
            email = generate_email(nom, prenom)
            address = f"Quartier {random.choice(['Kaloum', 'Dixinn', 'Matam', 'Ratoma', 'Matoto'])}, {ville}"
            devise = random.choice(["xof", "euro", "dollar"])
            
            # Assurer l'unicité du nom avec plus de variabilité
            name = f"{prenom} {nom}"
            legal_infos = f"Entreprise {name} - {ville}"
            created = False
            
            for attempt in range(20):  # Augmenter les tentatives
                try:
                    if attempt > 0:
                        # Après le premier échec, ajouter des variantes
                        if attempt < 10:
                            name = f"{prenom} {nom} {attempt}"
                        else:
                            # Si encore des conflits, changer complètement
                            prenom = random.choice(PRENOMS)
                            nom = random.choice(NOMS)
                            name = f"{prenom} {nom} {attempt}"
                        legal_infos = f"Entreprise {name} - {ville}"
                    
                    cursor.execute("""
                        INSERT INTO providerorclient 
                        (name, phone, email, address, type_, devise, legal_infos, deleted, is_syncro, last_update_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (name, phone, email, address, type_client, devise, legal_infos, 0, 0, datetime.now().isoformat()))
                    
                    client_id = cursor.lastrowid
                    client_ids.append(client_id)
                    print(f"✓ Créé: {name} ({type_client}) - ID: {client_id}")
                    created = True
                    break
                    
                except sqlite3.IntegrityError as e:
                    if attempt == 19:  # Dernier essai
                        print(f"❌ Impossible de créer un client après 20 tentatives (conflit: {str(e)})")
                    continue
            
            if not created:
                print(f"⚠️  Client non créé après toutes les tentatives")
        
        conn.commit()
        print(f"✓ {len(client_ids)} ProviderOrClient créés")
        
        # Créer les paiements pour chaque client
        print("Création des paiements...")
        total_payments = 0
        start_date = datetime.now() - timedelta(days=180)
        
        for client_id in client_ids:
            # Récupérer le nom du client pour les logs
            cursor.execute("SELECT name FROM providerorclient WHERE id = ?", (client_id,))
            client_name = cursor.fetchone()[0]
            
            print(f"  Création de {num_payments_per_client} paiements pour {client_name}...")
            
            balance_courante = 0.0
            
            for j in range(num_payments_per_client):
                # Date progressive (étalée sur 6 mois)
                payment_date = start_date + timedelta(days=random.randint(0, 180))
                payment_date_str = payment_date.isoformat()
                
                # 75% crédit, 25% débit
                is_credit = random.choice([True, True, True, False])
                
                if is_credit:
                    # Montants de crédit (recettes)
                    amount = round(random.uniform(5000, 500000), 2)
                    libelle = random.choice(LIBELLES_CREDIT)
                    payment_type = "Credit"
                    credit = amount
                    debit = 0.0
                    balance_courante += amount
                else:
                    # Montants de débit (dépenses)
                    amount = round(random.uniform(2000, 200000), 2)
                    libelle = random.choice(LIBELLES_DEBIT)
                    payment_type = "Debit"
                    credit = 0.0
                    debit = amount
                    balance_courante -= amount
                
                # Poids pour les débits
                weight = 0.0
                if payment_type == "Debit":
                    weight = round(random.uniform(0.5, 50.0), 2)
                
                try:
                    cursor.execute("""
                        INSERT INTO payment 
                        (owner_id, provider_clt_id, date, debit, credit, libelle, 
                         balance, weight, type_, deleted, status, is_syncro, last_update_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        owner_id, client_id, payment_date_str, debit, credit, 
                        libelle, balance_courante, weight, payment_type, 0, 0, 0, payment_date_str
                    ))
                    
                    total_payments += 1
                    
                except Exception as e:
                    print(f"❌ Erreur création paiement {j+1} pour {client_name}: {str(e)}")
            
            print(f"  ✓ {num_payments_per_client} paiements créés pour {client_name} - Balance: {balance_courante:,.2f}")
        
        conn.commit()
        
        # Résumé final
        print(f"\n=== RÉSUMÉ FINAL ===")
        print(f"✅ Clients créés: {len(client_ids)}")
        print(f"✅ Paiements créés: {total_payments}")
        if len(client_ids) > 0:
            print(f"✅ Moyenne: {total_payments/len(client_ids):.1f} paiements par client")
        else:
            print("⚠️  Aucun client créé, impossible de calculer la moyenne")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des fixtures: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def verify_data():
    """Vérifie les données créées"""
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM providerorclient")
        clients_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM payment")
        payments_count = cursor.fetchone()[0]
        
        print(f"\n🔍 Vérification:")
        print(f"   Clients en base: {clients_count}")
        print(f"   Paiements en base: {payments_count}")
        
        # Répartition clients/fournisseurs
        cursor.execute("SELECT type_, COUNT(*) FROM providerorclient GROUP BY type_")
        print(f"\n📊 Répartition clients/fournisseurs:")
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]}")
        
        # Répartition crédits/débits
        cursor.execute("SELECT type_, COUNT(*) FROM payment GROUP BY type_")
        print(f"\n💰 Répartition crédits/débits:")
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]}")
        
        # Quelques exemples
        cursor.execute("""
            SELECT p.name, COUNT(pay.id) as nb_payments, 
                   ROUND(SUM(pay.credit) - SUM(pay.debit), 2) as balance
            FROM providerorclient p 
            LEFT JOIN payment pay ON p.id = pay.provider_clt_id 
            GROUP BY p.id, p.name 
            ORDER BY balance DESC
            LIMIT 5
        """)
        
        print(f"\n📈 Top 5 clients par balance:")
        for row in cursor.fetchall():
            if row[2] is not None:
                print(f"   {row[0]}: {row[1]} paiements, balance: {row[2]:,.2f}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {str(e)}")
        return False

def main():
    """Fonction principale avec options"""
    import sys
    
    print("=== Script de création de fixtures MPayments ===")
    
    # Paramètres par défaut
    num_clients = 20
    num_payments = 30
    reset_data = True
    
    # Parse arguments simples
    if len(sys.argv) > 1:
        try:
            num_clients = int(sys.argv[1])
        except ValueError:
            print("❌ Nombre de clients invalide, utilisation de 20 par défaut")
    
    if len(sys.argv) > 2:
        try:
            num_payments = int(sys.argv[2])
        except ValueError:
            print("❌ Nombre de paiements invalide, utilisation de 30 par défaut")
    
    if len(sys.argv) > 3:
        reset_data = sys.argv[3].lower() not in ['false', 'non', '0']
    
    print(f"Paramètres: {num_clients} clients, {num_payments} paiements/client")
    if reset_data:
        print("⚠️  Les données existantes seront supprimées!")
    
    if create_fixture_data(num_clients, num_payments, reset_data):
        print("\n✅ Données de fixture créées avec succès !")
        verify_data()
        print(f"\n🚀 Total: {num_clients} clients × {num_payments} paiements = {num_clients * num_payments} paiements")
    else:
        print("\n❌ Échec de la création des données de fixture")

if __name__ == "__main__":
    main() 