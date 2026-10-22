from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections.abc import Iterable
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from shutil import copy2
from uuid import uuid4

from linguapdf.domain.models import StudyFolder, StudyProject, VocabularyCard
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
                created_at TEXT NOT NULL DEFAULT '',
                folder_id TEXT
            );

            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE,
                parent_id TEXT REFERENCES folders(id) ON DELETE RESTRICT,
                created_at TEXT NOT NULL,
                UNIQUE(parent_id, name)
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
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(documents)").fetchall()
        }
        if "kind" not in columns:
            self.connection.execute(
                "ALTER TABLE documents ADD COLUMN kind TEXT NOT NULL DEFAULT 'pdf'"
            )
        if "created_at" not in columns:
            self.connection.execute(
                "ALTER TABLE documents ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"
            )
        if "folder_id" not in columns:
            self.connection.execute("ALTER TABLE documents ADD COLUMN folder_id TEXT")
        self.connection.execute("UPDATE documents SET created_at=last_opened WHERE created_at=''")
        self.connection.commit()

    def register_document(
        self,
        document_id: str,
        path: str,
        title: str,
        folder_id: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.connection.execute(
            """
            INSERT INTO documents(id, path, title, last_opened, kind, created_at, folder_id)
            VALUES (?, ?, ?, ?, 'pdf', ?, ?)
            ON CONFLICT(id) DO UPDATE SET path=excluded.path, title=excluded.title,
                last_opened=excluded.last_opened,
                folder_id=COALESCE(excluded.folder_id, documents.folder_id)
            """,
            (document_id, path, title, now, now, folder_id),
        )
        self.connection.commit()

    def import_pdf(
        self,
        source_path: str | Path,
        title: str = "",
        folder_id: str | None = None,
    ) -> StudyProject:
        source = Path(source_path).expanduser().resolve()
        digest = sha256()
        with source.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        document_id = digest.hexdigest()
        existing = self.project(document_id)
        if existing:
            if folder_id is not None and existing.folder_id != folder_id:
                self.move_project(document_id, folder_id)
            self.touch_project(document_id)
            refreshed = self.project(document_id)
            if refreshed is None:
                raise RuntimeError("Could not reopen the imported PDF.")
            return refreshed
        destination = self.pdf_directory / f"{document_id}.pdf"
        if not destination.exists():
            copy2(source, destination)
        project_title = self.unique_project_name(title.strip() or source.stem, folder_id)
        self.register_document(document_id, str(destination), project_title, folder_id)
        project = self.project(document_id)
        if project is None:
            raise RuntimeError("Could not create the PDF workspace.")
        return project

    def create_vocabulary_project(self, title: str, folder_id: str | None = None) -> StudyProject:
        clean_title = self.unique_project_name(title, folder_id)
        now = datetime.now(timezone.utc).isoformat()
        project_id = uuid4().hex
        self.connection.execute(
            """
            INSERT INTO documents(id, path, title, last_opened, kind, created_at, folder_id)
            VALUES (?, '', ?, ?, 'vocabulary', ?, ?)
            """,
            (project_id, clean_title, now, now, folder_id),
        )
        self.connection.commit()
        project = self.project(project_id)
        if project is None:
            raise RuntimeError("Could not create the workspace.")
        return project

    def folders(self) -> list[StudyFolder]:
        rows = self.connection.execute(
            "SELECT * FROM folders ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [
            StudyFolder(
                id=row["id"],
                name=row["name"],
                parent_id=row["parent_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def create_folder(self, name: str, parent_id: str | None = None) -> StudyFolder:
        clean_name = self.unique_folder_name(name, parent_id)
        folder = StudyFolder(
            id=uuid4().hex,
            name=clean_name,
            parent_id=parent_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.connection.execute(
            "INSERT INTO folders(id, name, parent_id, created_at) VALUES (?, ?, ?, ?)",
            (folder.id, folder.name, folder.parent_id, folder.created_at),
        )
        self.connection.commit()
        return folder

    def folder_is_empty(self, folder_id: str) -> bool:
        child = self.connection.execute(
            "SELECT 1 FROM folders WHERE parent_id=? LIMIT 1", (folder_id,)
        ).fetchone()
        project = self.connection.execute(
            "SELECT 1 FROM documents WHERE folder_id=? LIMIT 1", (folder_id,)
        ).fetchone()
        return not child and not project

    def delete_folder(self, folder_id: str) -> bool:
        if not self.folder_is_empty(folder_id):
            return False
        cursor = self.connection.execute("DELETE FROM folders WHERE id=?", (folder_id,))
        self.connection.commit()
        return bool(cursor.rowcount)

    def move_project(self, project_id: str, folder_id: str | None) -> None:
        self.connection.execute(
            "UPDATE documents SET folder_id=? WHERE id=?", (folder_id, project_id)
        )
        self.connection.commit()

    def attach_pdf(self, project_id: str, source_path: str | Path) -> StudyProject:
        source = Path(source_path).expanduser().resolve()
        destination = self.generated_pdf_path(project_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source != destination.resolve():
            copy2(source, destination)
        return self.attach_generated_pdf(project_id, destination)

    def attach_generated_pdf(self, project_id: str, path: str | Path) -> StudyProject:
        pdf_path = Path(path).expanduser().resolve()
        self.connection.execute(
            "UPDATE documents SET path=?, kind='pdf', last_opened=? WHERE id=?",
            (str(pdf_path), datetime.now(timezone.utc).isoformat(), project_id),
        )
        self.connection.commit()
        project = self.project(project_id)
        if project is None:
            raise RuntimeError("Could not attach the PDF to this workspace.")
        return project

    def generated_pdf_path(self, project_id: str) -> Path:
        project = self.project(project_id)
        if project is None:
            raise ValueError("Workspace not found.")
        return self.pdf_directory / project.id / f"{project.title}.pdf"

    def unique_project_name(self, name: str, folder_id: str | None) -> str:
        return self._unique_name("documents", "title", name, folder_id)

    def unique_folder_name(self, name: str, parent_id: str | None) -> str:
        return self._unique_name("folders", "name", name, parent_id)

    def _unique_name(self, table: str, column: str, name: str, parent_id: str | None) -> str:
        base = snake_case_name(name)
        if not base:
            raise ValueError("The name cannot be empty.")
        parent_column = "folder_id" if table == "documents" else "parent_id"
        if parent_id is None:
            rows = self.connection.execute(
                f"SELECT {column} FROM {table} WHERE {parent_column} IS NULL"
            ).fetchall()
        else:
            rows = self.connection.execute(
                f"SELECT {column} FROM {table} WHERE {parent_column}=?", (parent_id,)
            ).fetchall()
        existing = {str(row[column]).casefold() for row in rows}
        candidate = base
        suffix = 2
        while candidate.casefold() in existing:
            candidate = f"{base}_{suffix}"
            suffix += 1
        return candidate

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
            if path.parent != self.pdf_directory.resolve():
                try:
                    path.parent.rmdir()
                except OSError:
                    pass

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
        return {
            "total": row["total"] or 0,
            "due": row["due"] or 0,
            "learning": row["learning"] or 0,
        }

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
        folder_id=row["folder_id"],
    )


def snake_case_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.replace("đ", "d").replace("Đ", "D"))
    ascii_value = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"_+", "_", re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value)).strip("_").lower()
