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
        self.MIG_VERSION = 23
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
        """Crée Activity, ajoute activity_id, répare index, backfill → Principale."""
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

        self._repair_activity_indexes()
        self._relax_provider_name_unique()
        self._backfill_default_activity()
        self._verify_principale_visibility()

    def _repair_activity_indexes(self):
        """
        Répare les index activity_id corrompus.
        Un index cassé fait échouer silencieusement WHERE activity_id IS NULL
        (0 ligne) alors que les comptes ont bien activity_id NULL.
        """
        if dbh is None:
            return
        try:
            integrity = dbh.execute_sql("PRAGMA integrity_check").fetchall()
            bad = [r[0] for r in integrity if r and r[0] != "ok"]
            if bad:
                logger.warning("Intégrité SQLite dégradée: %s", "; ".join(bad[:5]))
        except Exception as exc:
            logger.warning("PRAGMA integrity_check: %s", exc)
            bad = ["unknown"]

        # Toujours recréer l'index FK activity_id (souvent source des erreurs)
        try:
            dbh.execute_sql('DROP INDEX IF EXISTS "providerorclient_activity_id"')
            dbh.execute_sql(
                'CREATE INDEX IF NOT EXISTS "providerorclient_activity_id" '
                'ON "providerorclient" ("activity_id")'
            )
            logger.info("Index providerorclient_activity_id recréé")
        except Exception as exc:
            logger.warning(f"Recréation index activity_id: {exc}")

        try:
            dbh.execute_sql("REINDEX")
            logger.info("REINDEX effectué")
        except Exception as exc:
            logger.warning(f"REINDEX: {exc}")

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
        """Anciennes données (import / migration) → activité « Principale » (courante)."""
        try:
            activity, updated = Activity.assign_legacy_accounts_to_principale()
            logger.info(
                "Activité « %s » (id=%s) courante — %s compte(s) rattaché(s)",
                activity.name,
                activity.id,
                updated if updated is not None else "?",
            )
        except Exception as exc:
            logger.error(f"Backfill activité Principale: {exc}")
            try:
                principale = Activity.get_or_create_principale()
                Activity.set_current(principale)
                dbh.execute_sql(
                    'UPDATE "providerorclient" SET "activity_id" = ?',
                    (principale.id,),
                )
                logger.info("Backfill forcé : tous les comptes → Principale id=%s", principale.id)
            except Exception as exc2:
                logger.warning(f"Backfill activity_id (SQL forcé): {exc2}")

    def _verify_principale_visibility(self):
        """Log de contrôle : comptes visibles sous Principale après migration."""
        try:
            principale = Activity.get_or_create_principale()
            Activity.set_current(principale)
            n_accounts = (
                ProviderOrClient.select()
                .where(
                    ProviderOrClient.activity == principale,
                    ProviderOrClient.deleted == False,
                )
                .count()
            )
            n_orphan = dbh.execute_sql(
                'SELECT COUNT(*) FROM "providerorclient" '
                'WHERE "activity_id" IS NULL OR "activity_id" NOT IN '
                '(SELECT "id" FROM "activity")'
            ).fetchone()[0]
            if n_orphan:
                logger.warning(
                    "Encore %s compte(s) sans activité valide — rattachement forcé",
                    n_orphan,
                )
                dbh.execute_sql(
                    'UPDATE "providerorclient" SET "activity_id" = ? '
                    'WHERE "activity_id" IS NULL OR "activity_id" NOT IN '
                    '(SELECT "id" FROM "activity")',
                    (principale.id,),
                )
                n_accounts = (
                    ProviderOrClient.select()
                    .where(
                        ProviderOrClient.activity == principale,
                        ProviderOrClient.deleted == False,
                    )
                    .count()
                )
            logger.info(
                "Visibilité Principale OK : %s compte(s) actif(s) rattaché(s)",
                n_accounts,
            )
        except Exception as exc:
            logger.warning(f"Vérification Principale: {exc}")
