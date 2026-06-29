from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from app.classifier.merchant_normalizer import (
    build_road_address_summary,
    normalize_business_number,
    normalize_merchant_name,
    normalize_road_address,
    sanitize_optional_text,
)
from app.core.config import AppConfig
from app.db.database import get_connection, init_db


@dataclass(frozen=True)
class MerchantMasterInput:
    merchant_name: str
    source: str
    source_row_hash: str
    source_batch_id: str
    business_number: str | None = None
    branch_name: str | None = None
    area_hint: str | None = None
    category_large: str | None = None
    category_medium: str | None = None
    category_small: str | None = None
    road_name: str | None = None
    building_main_number: str | None = None
    building_sub_number: str | None = None
    building_name: str | None = None
    road_address: str | None = None


@dataclass(frozen=True)
class MerchantAliasInput:
    alias_name: str
    source: str
    merchant_master_id: str | None = None
    business_number: str | None = None


@dataclass(frozen=True)
class MerchantSearchRow:
    id: str
    merchant_name: str
    normalized_name: str
    business_number: str | None
    source: str
    match_source: str
    branch_name: str | None = None
    area_hint: str | None = None
    category_large: str | None = None
    category_medium: str | None = None
    category_small: str | None = None
    road_name: str | None = None
    building_main_number: str | None = None
    building_sub_number: str | None = None
    building_name: str | None = None
    road_address: str | None = None
    normalized_road_address: str | None = None
    address_summary: str | None = None
    source_batch_id: str | None = None


class MerchantRepository:
    def __init__(
        self,
        *,
        config: AppConfig | None = None,
        db_path: Path | str | None = None,
    ) -> None:
        self.config = config
        self.db_path = db_path
        init_db(config=config, db_path=db_path)

    def add_master(self, item: MerchantMasterInput) -> bool:
        return self.add_masters([item]) == 1

    def add_masters(self, items: list[MerchantMasterInput]) -> int:
        values = [self._master_values(item) for item in items]
        values = [item for item in values if item is not None]
        if not values:
            return 0
        with get_connection(config=self.config, db_path=self.db_path) as connection:
            before_changes = connection.total_changes
            connection.executemany(_INSERT_MASTER_SQL, values)
            return connection.total_changes - before_changes

    def add_masters_stream(self, items: Iterable[MerchantMasterInput], *, chunk_size: int = 5000) -> int:
        inserted = 0
        chunk: list[dict[str, object]] = []
        with get_connection(config=self.config, db_path=self.db_path) as connection:
            _apply_bulk_import_pragmas(connection)
            before_changes = connection.total_changes
            for item in items:
                values = self._master_values(item)
                if values is None:
                    continue
                chunk.append(values)
                if len(chunk) >= chunk_size:
                    connection.executemany(_INSERT_MASTER_SQL, chunk)
                    chunk = []
            if chunk:
                connection.executemany(_INSERT_MASTER_SQL, chunk)
            inserted = connection.total_changes - before_changes
        return inserted

    def _master_values(self, item: MerchantMasterInput) -> dict[str, object] | None:
        now = _now()
        normalized_name = normalize_merchant_name(item.merchant_name)
        if not normalized_name:
            return None
        business_number = normalize_business_number(item.business_number)
        return {
            "id": str(uuid4()),
            "merchant_name": sanitize_optional_text(item.merchant_name, max_length=160),
            "normalized_merchant_name": normalized_name,
            "business_number": business_number,
            "branch_name": sanitize_optional_text(item.branch_name, max_length=80),
            "area_hint": sanitize_optional_text(item.area_hint, max_length=120),
            "category_large": sanitize_optional_text(item.category_large, max_length=80),
            "category_medium": sanitize_optional_text(item.category_medium, max_length=80),
            "category_small": sanitize_optional_text(item.category_small, max_length=80),
            "road_name": sanitize_optional_text(item.road_name, max_length=120),
            "building_main_number": sanitize_optional_text(item.building_main_number, max_length=20),
            "building_sub_number": sanitize_optional_text(item.building_sub_number, max_length=20),
            "building_name": sanitize_optional_text(item.building_name, max_length=120),
            "road_address": sanitize_optional_text(item.road_address, max_length=220),
            "normalized_road_address": normalize_road_address(item.road_address),
            "source": sanitize_optional_text(item.source, max_length=80) or "unknown",
            "source_row_hash": sanitize_optional_text(item.source_row_hash, max_length=80) or str(uuid4()),
            "source_batch_id": sanitize_optional_text(item.source_batch_id, max_length=80) or "manual",
            "created_at": now,
            "updated_at": now,
        }

    def add_alias(self, item: MerchantAliasInput) -> bool:
        normalized_name = normalize_merchant_name(item.alias_name)
        if not normalized_name:
            return False
        business_number = normalize_business_number(item.business_number)
        source = sanitize_optional_text(item.source, max_length=80) or "unknown"
        values = {
            "id": str(uuid4()),
            "merchant_master_id": sanitize_optional_text(item.merchant_master_id, max_length=80),
            "alias_name": sanitize_optional_text(item.alias_name, max_length=160),
            "normalized_alias_name": normalized_name,
            "business_number": business_number,
            "source": source,
            "created_at": _now(),
        }
        with get_connection(config=self.config, db_path=self.db_path) as connection:
            existing = connection.execute(
                """
                SELECT 1
                FROM merchant_alias
                WHERE normalized_alias_name = ?
                  AND COALESCE(business_number, '') = COALESCE(?, '')
                  AND source = ?
                LIMIT 1
                """,
                (normalized_name, business_number, source),
            ).fetchone()
            if existing is not None:
                return False
            cursor = connection.execute(
                """
                INSERT INTO merchant_alias (
                    id, merchant_master_id, alias_name, normalized_alias_name,
                    business_number, source, created_at
                ) VALUES (
                    :id, :merchant_master_id, :alias_name, :normalized_alias_name,
                    :business_number, :source, :created_at
                )
                """,
                values,
            )
            return cursor.rowcount > 0

    def find_master_by_business_number(self, business_number: object, *, limit: int = 10) -> list[MerchantSearchRow]:
        normalized = normalize_business_number(business_number)
        if not normalized:
            return []
        return self._query_masters("business_number = ?", [normalized], limit=limit)

    def find_master_by_normalized_name(self, normalized_name: str, *, limit: int = 20) -> list[MerchantSearchRow]:
        if not normalized_name:
            return []
        return self._query_masters("normalized_merchant_name = ?", [normalized_name], limit=limit)

    def list_master_name_candidates(self, normalized_name: str, *, limit: int = 300) -> list[MerchantSearchRow]:
        if not normalized_name:
            return []
        prefix = normalized_name[:2] if len(normalized_name) >= 2 else normalized_name[:1]
        params: list[Any] = [f"{prefix}%"] if prefix else ["%"]
        rows = self._query_masters("normalized_merchant_name LIKE ?", params, limit=limit)
        if rows:
            return rows[:limit]
        return self._query_masters("1 = 1", [], limit=limit)

    def list_master_address_candidates(
        self,
        *,
        road_name: object = None,
        building_main_number: object = None,
        building_sub_number: object = None,
        normalized_road_address: str | None = None,
        limit: int = 20,
    ) -> list[MerchantSearchRow]:
        road_name_text = sanitize_optional_text(road_name, max_length=120)
        main_number = sanitize_optional_text(building_main_number, max_length=20)
        sub_number = sanitize_optional_text(building_sub_number, max_length=20)
        where_parts: list[str] = []
        params: list[Any] = []
        if road_name_text and main_number:
            where_parts.append(
                """
                building_main_number = ?
                AND (road_name = ? OR road_name LIKE ?)
                AND (
                    ? IS NULL
                    OR ? = ''
                    OR building_sub_number IS NULL
                    OR building_sub_number = ''
                    OR building_sub_number = '0'
                    OR building_sub_number = ?
                )
                """
            )
            params.extend([main_number, road_name_text, f"% {road_name_text}", sub_number, sub_number, sub_number])
            where_parts.append(
                """
                road_name = ?
                AND building_main_number = ?
                AND (
                    ? IS NULL
                    OR ? = ''
                    OR building_sub_number IS NULL
                    OR building_sub_number = ''
                    OR building_sub_number = '0'
                    OR building_sub_number = ?
                )
                """
            )
            params.extend([road_name_text, main_number, sub_number, sub_number, sub_number])
        if normalized_road_address:
            where_parts.append("normalized_road_address = ?")
            params.append(normalized_road_address)
        if not where_parts:
            return []
        return self._query_masters(f"({' OR '.join(where_parts)})", params, limit=limit)

    def search_masters(
        self,
        *,
        merchant_name: object = None,
        road_name: object = None,
        building_main_number: object = None,
        branch_name: object = None,
        category: object = None,
        limit: int = 50,
    ) -> list[MerchantSearchRow]:
        normalized_name = normalize_merchant_name(merchant_name)
        road_name_text = sanitize_optional_text(road_name, max_length=120)
        main_number = sanitize_optional_text(building_main_number, max_length=20)
        branch_text = sanitize_optional_text(branch_name, max_length=80)
        category_text = sanitize_optional_text(category, max_length=80)
        where_parts: list[str] = []
        params: list[Any] = []

        if normalized_name:
            prefix = normalized_name[:2] if len(normalized_name) >= 2 else normalized_name
            where_parts.append("normalized_merchant_name LIKE ?")
            params.append(f"{prefix}%")
        if road_name_text:
            where_parts.append("(road_name = ? OR road_name LIKE ?)")
            params.extend([road_name_text, f"% {road_name_text}"])
        if main_number:
            where_parts.append("building_main_number = ?")
            params.append(main_number)
        if branch_text:
            where_parts.append("branch_name LIKE ?")
            params.append(f"{branch_text}%")
        if category_text:
            where_parts.append("(category_large LIKE ? OR category_medium LIKE ? OR category_small LIKE ?)")
            params.extend([f"{category_text}%", f"{category_text}%", f"{category_text}%"])
        if not where_parts:
            return []
        safe_limit = max(1, min(int(limit), 100))
        rows = self._query_masters(" AND ".join(where_parts), params, limit=safe_limit)
        if normalized_name:
            return [
                row
                for row in rows
                if row.normalized_name.startswith(normalized_name)
                or normalized_name in row.normalized_name
                or row.normalized_name in normalized_name
            ][:safe_limit]
        return rows

    def log_source_import(
        self,
        *,
        source_name: str,
        source_file_name: str | None,
        source_file_hash: str | None = None,
        source_batch_id: str,
        imported_row_count: int,
        skipped_row_count: int,
        skipped_invalid_row_count: int = 0,
        duplicate_file: bool = False,
        note: str | None = None,
    ) -> None:
        safe_note = note
        if not safe_note and skipped_invalid_row_count:
            safe_note = f"invalid_rows={max(0, int(skipped_invalid_row_count))}"
        with get_connection(config=self.config, db_path=self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO merchant_source_log (
                    id, source_name, source_file_name, source_file_hash, source_batch_id,
                    imported_row_count, skipped_row_count, duplicate_file, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    sanitize_optional_text(source_name, max_length=80) or "unknown",
                    Path(source_file_name).name if source_file_name else None,
                    sanitize_optional_text(source_file_hash, max_length=80),
                    sanitize_optional_text(source_batch_id, max_length=80) or "manual",
                    max(0, int(imported_row_count)),
                    max(0, int(skipped_row_count)),
                    1 if duplicate_file else 0,
                    sanitize_optional_text(safe_note, max_length=160),
                    _now(),
                ),
            )

    def has_source_file_hash(self, source_name: str, source_file_hash: str | None) -> bool:
        if not source_file_hash:
            return False
        with get_connection(config=self.config, db_path=self.db_path) as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM merchant_source_log
                WHERE source_name = ? AND source_file_hash = ? AND duplicate_file = 0
                LIMIT 1
                """,
                (sanitize_optional_text(source_name, max_length=80) or "unknown", source_file_hash),
            ).fetchone()
        return row is not None

    def find_by_business_number(self, business_number: object, *, limit: int = 10) -> list[MerchantSearchRow]:
        normalized = normalize_business_number(business_number)
        if not normalized:
            return []
        alias_rows = self._query_aliases("alias.business_number = ?", [normalized], limit=limit)
        master_rows = self._query_masters("business_number = ?", [normalized], limit=limit)
        return [*alias_rows, *master_rows][:limit]

    def find_by_normalized_name(self, normalized_name: str, *, limit: int = 20) -> list[MerchantSearchRow]:
        if not normalized_name:
            return []
        alias_rows = self._query_aliases("alias.normalized_alias_name = ?", [normalized_name], limit=limit)
        master_rows = self._query_masters("normalized_merchant_name = ?", [normalized_name], limit=limit)
        return [*alias_rows, *master_rows][:limit]

    def list_name_candidates(self, normalized_name: str, *, limit: int = 300) -> list[MerchantSearchRow]:
        if not normalized_name:
            return []
        prefix = normalized_name[:2] if len(normalized_name) >= 2 else normalized_name[:1]
        params: list[Any] = [f"{prefix}%"] if prefix else ["%"]
        alias_rows = self._query_aliases("alias.normalized_alias_name LIKE ?", params, limit=limit)
        master_rows = self._query_masters("normalized_merchant_name LIKE ?", params, limit=limit)
        rows = [*alias_rows, *master_rows]
        if rows:
            return rows[:limit]
        return [*self._query_aliases("1 = 1", [], limit=limit), *self._query_masters("1 = 1", [], limit=limit)][:limit]

    def _query_masters(self, where_sql: str, params: list[Any], *, limit: int) -> list[MerchantSearchRow]:
        with get_connection(config=self.config, db_path=self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT id, merchant_name, normalized_merchant_name, business_number,
                       source, branch_name, area_hint, category_large, category_medium,
                       category_small, road_name, building_main_number,
                       building_sub_number, building_name, road_address, normalized_road_address,
                       source_batch_id
                FROM merchant_master
                WHERE {where_sql}
                ORDER BY merchant_name
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
        return [
            MerchantSearchRow(
                id=str(row["id"]),
                merchant_name=str(row["merchant_name"]),
                normalized_name=str(row["normalized_merchant_name"]),
                business_number=row["business_number"],
                source=str(row["source"]),
                match_source="master",
                branch_name=row["branch_name"],
                area_hint=row["area_hint"],
                category_large=row["category_large"],
                category_medium=row["category_medium"],
                category_small=row["category_small"],
                road_name=row["road_name"],
                building_main_number=row["building_main_number"],
                building_sub_number=row["building_sub_number"],
                building_name=row["building_name"],
                road_address=row["road_address"],
                normalized_road_address=row["normalized_road_address"],
                source_batch_id=row["source_batch_id"],
                address_summary=build_road_address_summary(
                    road_name=row["road_name"],
                    building_main_number=row["building_main_number"],
                    building_sub_number=row["building_sub_number"],
                    road_address=row["road_address"],
                ),
            )
            for row in rows
        ]

    def _query_aliases(self, where_sql: str, params: list[Any], *, limit: int) -> list[MerchantSearchRow]:
        with get_connection(config=self.config, db_path=self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                    alias.id AS alias_id,
                    alias.alias_name,
                    alias.normalized_alias_name,
                    COALESCE(alias.business_number, master.business_number) AS business_number,
                    alias.source AS alias_source,
                    master.id AS master_id,
                    master.merchant_name AS master_name,
                    master.branch_name AS branch_name,
                    master.area_hint AS area_hint,
                    master.category_large AS category_large,
                    master.category_medium AS category_medium,
                    master.category_small AS category_small,
                    master.road_name AS road_name,
                    master.building_main_number AS building_main_number,
                    master.building_sub_number AS building_sub_number,
                    master.building_name AS building_name,
                    master.road_address AS road_address,
                    master.normalized_road_address AS normalized_road_address,
                    master.source_batch_id AS source_batch_id
                FROM merchant_alias AS alias
                LEFT JOIN merchant_master AS master ON master.id = alias.merchant_master_id
                WHERE {where_sql}
                ORDER BY alias.alias_name
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
        return [
            MerchantSearchRow(
                id=str(row["master_id"] or row["alias_id"]),
                merchant_name=str(row["master_name"] or row["alias_name"]),
                normalized_name=str(row["normalized_alias_name"]),
                business_number=row["business_number"],
                source=str(row["alias_source"]),
                match_source="alias",
                branch_name=row["branch_name"],
                area_hint=row["area_hint"],
                category_large=row["category_large"],
                category_medium=row["category_medium"],
                category_small=row["category_small"],
                road_name=row["road_name"],
                building_main_number=row["building_main_number"],
                building_sub_number=row["building_sub_number"],
                building_name=row["building_name"],
                road_address=row["road_address"],
                normalized_road_address=row["normalized_road_address"],
                source_batch_id=row["source_batch_id"],
                address_summary=build_road_address_summary(
                    road_name=row["road_name"],
                    building_main_number=row["building_main_number"],
                    building_sub_number=row["building_sub_number"],
                    road_address=row["road_address"],
                ),
            )
            for row in rows
        ]


def _now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


_INSERT_MASTER_SQL = """
INSERT OR IGNORE INTO merchant_master (
    id, merchant_name, normalized_merchant_name, business_number,
    branch_name, area_hint, category_large, category_medium, category_small,
    road_name, building_main_number, building_sub_number, building_name,
    road_address, normalized_road_address,
    source, source_row_hash, source_batch_id, review_required, created_at, updated_at
) VALUES (
    :id, :merchant_name, :normalized_merchant_name, :business_number,
    :branch_name, :area_hint, :category_large, :category_medium, :category_small,
    :road_name, :building_main_number, :building_sub_number, :building_name,
    :road_address, :normalized_road_address,
    :source, :source_row_hash, :source_batch_id, 1, :created_at, :updated_at
)
"""


def _apply_bulk_import_pragmas(connection: Any) -> None:
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=MEMORY")
