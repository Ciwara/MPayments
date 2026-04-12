#!/usr/bin/env python
# -*- encoding: utf-8
# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fad
from __future__ import unicode_literals, absolute_import, division, print_function

from Common.ui.util import format_number_table_no_round, formatted_number
import sqlite3
from datetime import datetime


def check_befor_update_payment(pay):
    from models import Payment

    balance = pay.balance
    lt = []
    for rpt in pay.next_rpts():
        previous_balance = int(rpt.last_balance_payment())
        if rpt.type_ == Payment.CREDIT:
            balance = previous_balance + int(rpt.credit)
            lt.append("{} = last {} + {}".format(balance, previous_balance, rpt.credit))
        if rpt.type_ == Payment.DEBIT:
            balance = previous_balance - int(rpt.debit)
            lt.append("{} = last {} - {}".format(balance, previous_balance, rpt.debit))
        # if balance < 0:
        #     return False
    return True


def device_amount(value, provider=None, dvs=None, aftergam=2, preserve_decimals=False):

    from Common.models import Settings
    from configuration import Config
    from models import ProviderOrClient

    def _fmt(v):
        return format_number_table_no_round(v) if preserve_decimals else formatted_number(
            v, aftergam=aftergam
        )

    if dvs:
        return "{} {}".format(_fmt(value), dvs)

    organ = Settings().get(id=1)

    if not Config.DEVISE_PEP_PROV or not provider:
        dvs = organ.DEVISE.get(organ.devise)
    else:
        if isinstance(provider, str):
            dvs = organ.DEVISE.get(organ.devise)
        elif isinstance(provider, int):
            provider = ProviderOrClient().get(id=int(provider))
            dvs = provider.DEVISE.get(provider.devise)
        else:
            provider = provider
            dvs = provider.DEVISE.get(provider.devise)

    v = _fmt(value)
    if dvs == "$":
        return "{d}{v}".format(v=v, d=dvs)
    else:
        return "{v}{d}".format(v=v, d=dvs)

def get_default_owner(db_path="database.db"):
    """
    Récupère l'owner par défaut depuis la base de données
    Returns: dict avec les informations de l'owner ou None si non trouvé
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Récupérer l'owner connecté (is_identified = 1, colonne du modèle Common.Owner)
        cursor.execute("""
            SELECT id, username, is_identified, "group", phone, password, 
                   isactive, last_login, login_count
            FROM owner 
            WHERE is_identified = 1 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'username': row[1],
                'islog': bool(row[2]),
                'group': row[3],
                'phone': row[4],
                'password': row[5],
                'isactive': bool(row[6]),
                'last_login': row[7],
                'login_count': row[8]
            }
        else:
            return None
            
    except Exception as e:
        print(f"Erreur lors de la récupération de l'owner: {e}")
        return None

def get_owner_by_id(owner_id, db_path="database.db"):
    """
    Récupère un owner par son ID
    Returns: dict avec les informations de l'owner ou None si non trouvé
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, is_identified, "group", phone, password, 
                   isactive, last_login, login_count
            FROM owner 
            WHERE id = ?
        """, (owner_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'username': row[1],
                'islog': bool(row[2]),
                'group': row[3],
                'phone': row[4],
                'password': row[5],
                'isactive': bool(row[6]),
                'last_login': row[7],
                'login_count': row[8]
            }
        else:
            return None
            
    except Exception as e:
        print(f"Erreur lors de la récupération de l'owner {owner_id}: {e}")
        return None

def update_owner_login(owner_id, db_path="database.db"):
    """
    Met à jour les informations de connexion d'un owner
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        
        # Incrémenter le compteur de connexions et mettre à jour la dernière connexion
        cursor.execute("""
            UPDATE owner 
            SET login_count = login_count + 1,
                last_login = ?,
                last_update_date = ?
            WHERE id = ?
        """, (current_time, current_time, owner_id))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de la mise à jour de l'owner {owner_id}: {e}")
        return False

def list_all_owners(db_path="database.db"):
    """
    Liste tous les owners de la base de données
    Returns: liste de dictionnaires
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, is_identified, "group", phone, 
                   isactive, last_login, login_count
            FROM owner 
            ORDER BY id
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        owners = []
        for row in rows:
            owners.append({
                'id': row[0],
                'username': row[1],
                'islog': bool(row[2]),
                'group': row[3],
                'phone': row[4],
                'isactive': bool(row[5]),
                'last_login': row[6],
                'login_count': row[7]
            })
        
        return owners
        
    except Exception as e:
        print(f"Erreur lors de la récupération des owners: {e}")
        return []

if __name__ == "__main__":
    # Test des fonctions
    print("=== Test des fonctions de gestion des owners ===")
    
    owner = get_default_owner()
    if owner:
        print(f"✅ Owner par défaut trouvé: {owner['username']} (ID: {owner['id']})")
        
        # Test de mise à jour de connexion
        if update_owner_login(owner['id']):
            print("✅ Informations de connexion mises à jour")
        
        # Récupérer à nouveau pour voir les changements
        updated_owner = get_owner_by_id(owner['id'])
        if updated_owner:
            print(f"✅ Compteur de connexions: {updated_owner['login_count']}")
    else:
        print("❌ Aucun owner par défaut trouvé")
    
    # Lister tous les owners
    all_owners = list_all_owners()
    print(f"📋 Total owners en base: {len(all_owners)}")
    for owner in all_owners:
        status = "Actif" if owner['isactive'] else "Inactif"
        logged = "Connecté" if owner['islog'] else "Déconnecté"
        print(f"  - {owner['username']} (ID: {owner['id']}) - {status}, {logged}")
