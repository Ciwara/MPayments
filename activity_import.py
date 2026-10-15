#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Import d'une sauvegarde SQLite (.db) dans une activité (comptes + paiements).

Ne remplace pas toute la base : les utilisateurs, l'organisation et les autres
activités restent intacts. Les données sont rattachées à l'activité cible.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path


class ActivityImportError(Exception):
    """Erreur métier lors de l'import vers une activité."""


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def outside_internal(path) -> Path:
    """``C:\\Business\\_internal\\database.db`` → ``C:\\Business\\database.db``."""
    path = Path(path)
    parts = path.parts
    lowered = [part.lower() for part in parts]
    if "_internal" not in lowered:
        return path
    idx = lowered.index("_internal")
    return Path(*parts[:idx]) / path.name


def resolve_sqlite_file(path, *, role="fichier") -> Path:
    """Retourne un fichier .db, y compris si ``path`` est un dossier (ex. C:\\Business)."""
    path = outside_internal(path)
    if path.is_file():
        return path
    if path.is_dir():
        direct = path / "database.db"
        if direct.is_file():
            return direct
        matches = sorted(p for p in path.glob("*.db") if p.is_file())
        if len(matches) == 1:
            return matches[0]
        if matches:
            names = ", ".join(p.name for p in matches[:8])
            raise ActivityImportError(
                f"{role} : « {path} » est un dossier. Choisissez un fichier .db ({names})."
            )
        raise ActivityImportError(
            f"{role} : aucun fichier .db dans le dossier « {path} »."
        )
    raise ActivityImportError(f"Fichier introuvable : {path}")


def resolve_app_database(explicit=None) -> Path:
    """Base ouverte par l'application (à côté de l'exe, pas dans _internal)."""
    candidates = []
    try:
        from Common.models import DB_FILE, dbh

        live = getattr(dbh, "database", None) if dbh is not None else None
        if live:
            candidates.append(Path(live))
        if DB_FILE:
            candidates.append(Path(DB_FILE))
    except Exception:
        pass
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "database.db")
    if explicit:
        candidates.append(Path(explicit))
    try:
        from configuration import Config

        if getattr(Config, "DB_PATH", None):
            candidates.append(Path(Config.DB_PATH))
    except Exception:
        pass

    seen = set()
    last = None
    for candidate in candidates:
        candidate = outside_internal(candidate)
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        last = candidate
        try:
            return resolve_sqlite_file(candidate, role="Base de l'application")
        except ActivityImportError:
            continue
    if last is not None:
        raise ActivityImportError(f"Fichier introuvable : {last}")
    raise ActivityImportError("Base de l'application introuvable.")


def _connect(path: Path) -> sqlite3.Connection:
    path = resolve_sqlite_file(path)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def preview_source(src_path) -> dict:
    """Compte comptes / paiements dans la source (pour l'UI)."""
    src = _connect(Path(src_path))
    try:
        # Vérifie que ce ressemble à une base MPayments / Common
        tables = {
            r[0]
            for r in src.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "providerorclient" not in tables or "payment" not in tables:
            raise ActivityImportError(
                "Ce fichier n'est pas une sauvegarde compatible "
                "(tables providerorclient / payment manquantes)."
            )
        accounts = src.execute(
            "SELECT COUNT(*) AS n FROM providerorclient "
            "WHERE deleted = 0 OR deleted IS NULL"
        ).fetchone()["n"]
        payments = src.execute("SELECT COUNT(*) AS n FROM payment").fetchone()["n"]
        return {"accounts": int(accounts), "payments": int(payments)}
    finally:
        src.close()


def _ensure_activity(dest: sqlite3.Connection, name: str) -> int:
    name = (name or "").strip()
    if not name:
        raise ActivityImportError("Le nom de l'activité est obligatoire")
    row = dest.execute(
        "SELECT id FROM activity WHERE name = ? AND deleted = 0",
        (name,),
    ).fetchone()
    if row:
        return int(row["id"])

    # Table activity absente (très ancienne base cible)
    tables = {
        r[0]
        for r in dest.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "activity" not in tables:
        raise ActivityImportError(
            "La base actuelle n'a pas de table activité. "
            "Redémarrez l'application pour appliquer les migrations."
        )

    org = dest.execute("SELECT id FROM organization ORDER BY id LIMIT 1").fetchone()
    owner = dest.execute(
        "SELECT id FROM owner WHERE isactive = 1 ORDER BY id LIMIT 1"
    ).fetchone()
    cur = dest.execute(
        """
        INSERT INTO activity (
            is_syncro, last_update_date, organization_id, owner_id,
            name, description, is_current, deleted
        ) VALUES (0, ?, ?, ?, ?, ?, 0, 0)
        """,
        (
            _now(),
            int(org["id"]) if org else None,
            int(owner["id"]) if owner else None,
            name,
            "Import de sauvegarde",
        ),
    )
    return int(cur.lastrowid)


def _default_owner_id(dest: sqlite3.Connection) -> int:
    row = dest.execute(
        "SELECT id FROM owner WHERE isactive = 1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        raise ActivityImportError("Aucun utilisateur actif dans la base actuelle")
    return int(row["id"])


def _clear_activity_data(dest: sqlite3.Connection, activity_id: int) -> int:
    poc_ids = [
        int(r["id"])
        for r in dest.execute(
            "SELECT id FROM providerorclient WHERE activity_id = ?",
            (activity_id,),
        )
    ]
    if not poc_ids:
        return 0
    placeholders = ",".join("?" * len(poc_ids))
    dest.execute(
        f"DELETE FROM payment WHERE provider_clt_id IN ({placeholders})",
        poc_ids,
    )
    dest.execute(
        "DELETE FROM providerorclient WHERE activity_id = ?",
        (activity_id,),
    )
    return len(poc_ids)


def import_into_activity(
    src_path,
    dest_path,
    activity_name: str,
    replace: bool = True,
) -> dict:
    """Importe comptes + paiements de ``src_path`` dans l'activité ``activity_name``.

    Returns
    -------
    dict
        activity_id, activity_name, accounts, payments, skipped, cleared, created
    """
    src_path = resolve_sqlite_file(src_path, role="Sauvegarde")
    dest_path = resolve_app_database(dest_path)
    if src_path.resolve() == dest_path.resolve():
        raise ActivityImportError(
            "La sauvegarde choisie est la base actuellement ouverte. "
            "Sélectionnez un autre fichier .db."
        )
    preview_source(src_path)  # validation précoce

    src = _connect(src_path)
    dest = _connect(dest_path)
    created = False
    try:
        existing = dest.execute(
            "SELECT id FROM activity WHERE name = ? AND deleted = 0",
            (activity_name.strip(),),
        ).fetchone()
        created = existing is None
        activity_id = _ensure_activity(dest, activity_name)
        owner_id = _default_owner_id(dest)

        cleared = 0
        if replace:
            cleared = _clear_activity_data(dest, activity_id)

        accounts = src.execute(
            """
            SELECT id, name, address, phone, email, legal_infos, type_,
                   devise, deleted, is_syncro, last_update_date
            FROM providerorclient
            WHERE deleted = 0 OR deleted IS NULL
            ORDER BY id
            """
        ).fetchall()
        if not accounts:
            raise ActivityImportError("Aucun compte dans la sauvegarde source")

        id_map = {}
        now = _now()
        for acc in accounts:
            name = (acc["name"] or "").strip()
            if not name:
                continue
            existing_poc = dest.execute(
                """
                SELECT id FROM providerorclient
                WHERE name = ? AND activity_id = ? AND deleted = 0
                """,
                (name, activity_id),
            ).fetchone()
            if existing_poc:
                id_map[int(acc["id"])] = int(existing_poc["id"])
                continue

            cur = dest.execute(
                """
                INSERT INTO providerorclient (
                    is_syncro, last_update_date, name, address, phone, email,
                    legal_infos, type_, picture_id, devise, deleted, activity_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
                """,
                (
                    int(acc["is_syncro"] or 0),
                    acc["last_update_date"] or now,
                    name,
                    acc["address"],
                    acc["phone"],
                    acc["email"],
                    acc["legal_infos"],
                    acc["type_"] or "Client",
                    acc["devise"] or "xof",
                    int(acc["deleted"] or 0),
                    activity_id,
                ),
            )
            id_map[int(acc["id"])] = int(cur.lastrowid)

        payments = src.execute(
            """
            SELECT owner_id, provider_clt_id, date, debit, credit, libelle,
                   balance, weight, type_, deleted, status, is_syncro,
                   last_update_date
            FROM payment
            ORDER BY date ASC, id ASC
            """
        ).fetchall()

        inserted = 0
        skipped = 0
        for pay in payments:
            new_poc = id_map.get(int(pay["provider_clt_id"]))
            if new_poc is None:
                skipped += 1
                continue
            dest.execute(
                """
                INSERT INTO payment (
                    is_syncro, last_update_date, owner_id, provider_clt_id,
                    date, debit, credit, libelle, balance, weight,
                    type_, deleted, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(pay["is_syncro"] or 0),
                    pay["last_update_date"] or now,
                    owner_id,
                    new_poc,
                    pay["date"],
                    float(pay["debit"] or 0),
                    float(pay["credit"] or 0),
                    pay["libelle"],
                    float(pay["balance"] or 0),
                    pay["weight"],
                    pay["type_"] or "Credit",
                    int(pay["deleted"] or 0),
                    int(pay["status"] or 0),
                ),
            )
            inserted += 1

        dest.commit()
        return {
            "activity_id": activity_id,
            "activity_name": activity_name.strip(),
            "accounts": len(id_map),
            "payments": inserted,
            "skipped": skipped,
            "cleared": cleared,
            "created": created,
        }
    except ActivityImportError:
        dest.rollback()
        raise
    except sqlite3.Error as exc:
        dest.rollback()
        raise ActivityImportError(f"Erreur SQLite : {exc}") from exc
    finally:
        src.close()
        dest.close()
