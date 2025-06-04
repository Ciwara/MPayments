#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fad
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

from Common.cdatabase import AdminDatabase
from Common.models import Owner
from models import Payment, ProviderOrClient
from playhouse.migrate import BooleanField, CharField, DateTimeField, IntegerField


class Setup(AdminDatabase):

    """docstring for FixtInit"""

    def __init__(self):
        super(AdminDatabase, self).__init__()

        # Ajouter Owner en premier pour s'assurer qu'il est créé avant Payment
        self.LIST_CREAT.append(Owner)
        self.LIST_CREAT.append(ProviderOrClient)
        self.LIST_CREAT.append(Payment)
        self.MIG_VERSION = 21
        self.LIST_MIGRATE += [
            ("ProviderOrClient", "deleted", BooleanField(default=False)),
            ("ProviderOrClient", "is_syncro", BooleanField(default=False)),
            ("ProviderOrClient", "devise", CharField(default="xof")),
            ("ProviderOrClient", "phone", IntegerField(null=True)),
            (
                "ProviderOrClient",
                "last_update_date",
                DateTimeField(default=datetime.now),
            ),
            # ('Payment', 'weight', FloatField(null=True)),
            ("Payment", "name", CharField(null=True)),
            ("Payment", "is_syncro", BooleanField(default=False)),
            ("Payment", "last_update_date", DateTimeField(default=datetime.now)),
        ]
    
    def create_default_owner(self):
        """Crée un Owner par défaut si aucun n'existe avec islog == True"""
        try:
            # Vérifier si un Owner avec islog == True existe déjà
            Owner.get(Owner.islog == True)
        except Owner.DoesNotExist:
            # Créer un Owner par défaut avec la structure correcte
            # Utiliser une approche différente pour éviter l'erreur force_insert
            current_time = datetime.now()
            
            # Créer l'instance sans sauvegarder immédiatement
            owner = Owner(
                username="admin",
                islog=True,
                group="administrators",
                phone="0000000000",
                password="admin123",
                isactive=True,
                last_login=current_time,
                login_count=0,
                is_syncro=False,
                last_update_date=current_time
            )
            
            # Sauvegarder sans force_insert
            try:
                owner.save()
                print("Owner par défaut créé avec succès")
            except Exception as e:
                print(f"Erreur lors de la création de l'Owner: {str(e)}")
                # Alternative: utiliser une requête SQL directe
                try:
                    Owner._meta.database.execute_sql(
                        """INSERT INTO owner (username, islog, "group", phone, password, 
                           isactive, last_login, login_count, is_syncro, last_update_date)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        ("admin", 1, "administrators", "0000000000", "admin123", 
                         1, current_time.isoformat(), 0, 0, current_time.isoformat())
                    )
                    print("Owner par défaut créé avec succès (méthode alternative)")
                except Exception as e2:
                    print(f"Impossible de créer l'Owner: {str(e2)}")
