from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from shutil import copy2
from uuid import uuid4

from linguapdf.domain.models import StudyProject, VocabularyCard
from linguapdf.domain.scheduler import schedule_review


class LibraryService:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.pdf_directory = self.database_path.parent / "pdfs"
        self.pdf_directory.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                title TEXT NOT NULL,
                last_opened TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'pdf',
                created_at TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                english TEXT NOT NULL COLLATE NOCASE,
                vietnamese TEXT NOT NULL COLLATE NOCASE,
                created_at TEXT NOT NULL,
                repetitions INTEGER NOT NULL DEFAULT 0,
                interval_days REAL NOT NULL DEFAULT 0,
                ease_factor REAL NOT NULL DEFAULT 2.5,
                due_at TEXT NOT NULL,
                last_reviewed TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                correct INTEGER NOT NULL DEFAULT 0,
                UNIQUE(document_id, english, vietnamese)
            );

            CREATE TABLE IF NOT EXISTS review_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vocabulary_id INTEGER NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
                direction TEXT NOT NULL,
                rating INTEGER NOT NULL,
                reviewed_at TEXT NOT NULL
            );
            """
        )
        columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(documents)").fetchall()
        }
        if "kind" not in columns:
            self.connection.execute(
                "ALTER TABLE documents ADD COLUMN kind TEXT NOT NULL DEFAULT 'pdf'"
            )
        if "created_at" not in columns:
            self.connection.execute(
                "ALTER TABLE documents ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"
            )
        self.connection.execute("UPDATE documents SET created_at=last_opened WHERE created_at=''")
        self.connection.commit()

    def register_document(self, document_id: str, path: str, title: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.connection.execute(
            """
            INSERT INTO documents(id, path, title, last_opened, kind, created_at)
            VALUES (?, ?, ?, ?, 'pdf', ?)
            ON CONFLICT(id) DO UPDATE SET path=excluded.path, title=excluded.title,
                last_opened=excluded.last_opened
            """,
            (document_id, path, title, now, now),
        )
        self.connection.commit()

    def import_pdf(self, source_path: str | Path, title: str = "") -> StudyProject:
        source = Path(source_path).expanduser().resolve()
        digest = sha256()
        with source.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        document_id = digest.hexdigest()
        destination = self.pdf_directory / f"{document_id}.pdf"
        if not destination.exists():
            copy2(source, destination)
        self.register_document(document_id, str(destination), title.strip() or source.stem)
        project = self.project(document_id)
        if project is None:
            raise RuntimeError("Không thể tạo tài liệu trong thư viện.")
        return project

    def create_vocabulary_project(self, title: str) -> StudyProject:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Tên bộ từ vựng không được để trống.")
        now = datetime.now(timezone.utc).isoformat()
        project_id = uuid4().hex
        self.connection.execute(
            """
            INSERT INTO documents(id, path, title, last_opened, kind, created_at)
            VALUES (?, '', ?, ?, 'vocabulary', ?)
            """,
            (project_id, clean_title, now, now),
        )
        self.connection.commit()
        project = self.project(project_id)
        if project is None:
            raise RuntimeError("Không thể tạo bộ từ vựng.")
        return project

    def projects(self) -> list[StudyProject]:
        rows = self.connection.execute(
            """
            SELECT d.*, COUNT(v.id) AS card_count
            FROM documents d LEFT JOIN vocabulary v ON v.document_id=d.id
            GROUP BY d.id ORDER BY d.last_opened DESC, d.title COLLATE NOCASE
            """
        ).fetchall()
        return [_row_to_project(row) for row in rows]

    def project(self, project_id: str) -> StudyProject | None:
        row = self.connection.execute(
            """
            SELECT d.*, COUNT(v.id) AS card_count
            FROM documents d LEFT JOIN vocabulary v ON v.document_id=d.id
            WHERE d.id=? GROUP BY d.id
            """,
            (project_id,),
        ).fetchone()
        return _row_to_project(row) if row else None

    def touch_project(self, project_id: str) -> None:
        self.connection.execute(
            "UPDATE documents SET last_opened=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), project_id),
        )
        self.connection.commit()

    def delete_project(self, project_id: str) -> None:
        project = self.project(project_id)
        if project is None:
            return
        self.connection.execute("DELETE FROM documents WHERE id=?", (project_id,))
        self.connection.commit()
        if project.kind == "pdf" and project.path:
            path = Path(project.path).resolve()
            try:
                path.relative_to(self.pdf_directory.resolve())
            except ValueError:
                return
            path.unlink(missing_ok=True)
            path.with_suffix(path.suffix + ".linguapdf.json").unlink(missing_ok=True)

    def add_cards(self, document_id: str, cards: Iterable[tuple[str, str]]) -> tuple[int, int]:
        now = datetime.now(timezone.utc).isoformat()
        added = 0
        skipped = 0
        for english, vietnamese in cards:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO vocabulary(
                    document_id, english, vietnamese, created_at, due_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (document_id, english.strip(), vietnamese.strip(), now, now),
            )
            if cursor.rowcount:
                added += 1
            else:
                skipped += 1
        self.connection.commit()
        return added, skipped

    def cards_for_document(self, document_id: str, search: str = "") -> list[VocabularyCard]:
        parameters: list[object] = [document_id]
        where = "document_id = ?"
        if search.strip():
            where += " AND (english LIKE ? OR vietnamese LIKE ?)"
            wildcard = f"%{search.strip()}%"
            parameters.extend((wildcard, wildcard))
        rows = self.connection.execute(
            f"SELECT * FROM vocabulary WHERE {where} ORDER BY created_at DESC",
            parameters,
        ).fetchall()
        return [_row_to_card(row) for row in rows]

    def due_cards(self, document_id: str, limit: int = 100) -> list[VocabularyCard]:
        now = datetime.now(timezone.utc).isoformat()
        rows = self.connection.execute(
            """
            SELECT * FROM vocabulary
            WHERE document_id = ? AND due_at <= ?
            ORDER BY due_at ASC, id ASC LIMIT ?
            """,
            (document_id, now, limit),
        ).fetchall()
        return [_row_to_card(row) for row in rows]

    def delete_cards(self, card_ids: Iterable[int]) -> int:
        ids = list(card_ids)
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        cursor = self.connection.execute(
            f"DELETE FROM vocabulary WHERE id IN ({placeholders})", ids
        )
        self.connection.commit()
        return cursor.rowcount

    def record_review(self, card: VocabularyCard, direction: str, rating: int) -> VocabularyCard:
        now = datetime.now(timezone.utc)
        result = schedule_review(
            card.repetitions,
            card.interval_days,
            card.ease_factor,
            rating,
            now=now,
        )
        self.connection.execute(
            """
            UPDATE vocabulary SET repetitions=?, interval_days=?, ease_factor=?, due_at=?,
                last_reviewed=?, attempts=attempts+1, correct=correct+?
            WHERE id=?
            """,
            (
                result.repetitions,
                result.interval_days,
                result.ease_factor,
                result.due_at.isoformat(),
                now.isoformat(),
                1 if rating >= 3 else 0,
                card.id,
            ),
        )
        self.connection.execute(
            "INSERT INTO review_log(vocabulary_id, direction, rating, reviewed_at) VALUES (?, ?, ?, ?)",
            (card.id, direction, rating, now.isoformat()),
        )
        self.connection.commit()
        row = self.connection.execute("SELECT * FROM vocabulary WHERE id=?", (card.id,)).fetchone()
        return _row_to_card(row)

    def stats(self, document_id: str) -> dict[str, int]:
        now = datetime.now(timezone.utc).isoformat()
        row = self.connection.execute(
            """
            SELECT COUNT(*) total,
                SUM(CASE WHEN due_at <= ? THEN 1 ELSE 0 END) due,
                SUM(CASE WHEN repetitions > 0 THEN 1 ELSE 0 END) learning
            FROM vocabulary WHERE document_id=?
            """,
            (now, document_id),
        ).fetchone()
        return {"total": row["total"] or 0, "due": row["due"] or 0, "learning": row["learning"] or 0}

    def close(self) -> None:
        self.connection.close()


def _row_to_card(row: sqlite3.Row) -> VocabularyCard:
    return VocabularyCard(
        id=row["id"],
        document_id=row["document_id"],
        english=row["english"],
        vietnamese=row["vietnamese"],
        repetitions=row["repetitions"],
        interval_days=row["interval_days"],
        ease_factor=row["ease_factor"],
        due_at=row["due_at"],
        last_reviewed=row["last_reviewed"],
        attempts=row["attempts"],
        correct=row["correct"],
    )


def _row_to_project(row: sqlite3.Row) -> StudyProject:
    return StudyProject(
        id=row["id"],
        title=row["title"],
        kind=row["kind"],
        path=row["path"],
        created_at=row["created_at"],
        last_opened=row["last_opened"],
        card_count=row["card_count"],
    )

