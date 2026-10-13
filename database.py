#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fad
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

from Common.cdatabase import AdminDatabase
from Common.cstatic import logger
from Common.models import Owner, dbh
from models import Activity, Payment, ProviderOrClient
from playhouse.migrate import BooleanField, CharField, DateTimeField, IntegerField


class Setup(AdminDatabase):

    """docstring for FixtInit"""

    def __init__(self):
        super().__init__()

        # Activity avant ProviderOrClient (FK)
        self.LIST_CREAT.append(Owner)
        self.LIST_CREAT.append(Activity)
        self.LIST_CREAT.append(ProviderOrClient)
        self.LIST_CREAT.append(Payment)
        self.MIG_VERSION = 22
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
            ("ProviderOrClient", "activity_id", IntegerField(null=True)),
            # ('Payment', 'weight', FloatField(null=True)),
            ("Payment", "name", CharField(null=True)),
            ("Payment", "is_syncro", BooleanField(default=False)),
            ("Payment", "last_update_date", DateTimeField(default=datetime.now)),
        ]

    def create_all_or_pass(self):
        super().create_all_or_pass()
        self._ensure_activity_schema()

    def _table_columns(self, table_name):
        if dbh is None:
            return set()
        try:
            rows = dbh.get_columns(table_name)
            return {c.name for c in rows}
        except Exception:
            try:
                cursor = dbh.execute_sql(f'PRAGMA table_info("{table_name}")')
                return {row[1] for row in cursor.fetchall()}
            except Exception as exc:
                logger.warning(f"Impossible de lire les colonnes de {table_name}: {exc}")
                return set()

    def _ensure_activity_schema(self):
        """Crée Activity, ajoute activity_id aux comptes, backfill activité par défaut."""
        if dbh is None:
            return
        if dbh.is_closed():
            dbh.connect()

        try:
            dbh.create_tables([Activity], safe=True)
        except Exception as exc:
            logger.error(f"Création table Activity: {exc}")
            return

        cols = self._table_columns("providerorclient")
        if cols and "activity_id" not in cols:
            try:
                dbh.execute_sql(
                    'ALTER TABLE "providerorclient" ADD COLUMN "activity_id" INTEGER NULL'
                )
                logger.info("Colonne providerorclient.activity_id ajoutée")
            except Exception as exc:
                logger.warning(f"Ajout activity_id: {exc}")

        self._relax_provider_name_unique()
        self._backfill_default_activity()

    def _relax_provider_name_unique(self):
        """Autorise le même nom de compte dans des activités différentes (SQLite)."""
        if dbh is None:
            return
        try:
            indexes = dbh.execute_sql('PRAGMA index_list("providerorclient")').fetchall()
        except Exception:
            return

        for idx in indexes:
            # seq, name, unique, origin, partial
            if len(idx) < 3 or not idx[2]:
                continue
            idx_name = idx[1]
            try:
                info = dbh.execute_sql(f'PRAGMA index_info("{idx_name}")').fetchall()
                cols = [row[2] for row in info]
            except Exception:
                continue
            if cols == ["name"]:
                try:
                    dbh.execute_sql(f'DROP INDEX IF EXISTS "{idx_name}"')
                    logger.info(f"Index unique sur ProviderOrClient.name retiré ({idx_name})")
                except Exception as exc:
                    logger.warning(f"Drop index {idx_name}: {exc}")

        try:
            dbh.execute_sql(
                'CREATE UNIQUE INDEX IF NOT EXISTS "providerorclient_name_activity" '
                'ON "providerorclient" ("name", "activity_id")'
            )
        except Exception as exc:
            logger.warning(f"Index unique (name, activity_id): {exc}")

    def _backfill_default_activity(self):
        try:
            activity = Activity.ensure_default()
        except Exception as exc:
            logger.error(f"ensure_default Activity: {exc}")
            return

        try:
            (
                ProviderOrClient.update(activity=activity)
                .where(ProviderOrClient.activity.is_null(True))
                .execute()
            )
        except Exception:
            try:
                dbh.execute_sql(
                    'UPDATE "providerorclient" SET "activity_id" = ? '
                    'WHERE "activity_id" IS NULL',
                    (activity.id,),
                )
            except Exception as exc:
                logger.warning(f"Backfill activity_id: {exc}")
