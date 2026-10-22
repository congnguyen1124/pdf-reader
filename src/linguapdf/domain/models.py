from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Annotation:
    page: int
    kind: str
    rect: tuple[float, float, float, float]
    text: str = ""
    color: str = "#FACC15"
    font_size: float = 14.0
    text_color: str = "#2563EB"
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["rect"] = list(self.rect)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Annotation:
        return cls(
            id=str(data.get("id") or uuid4().hex),
            page=int(data["page"]),
            kind=str(data["kind"]),
            rect=tuple(float(value) for value in data["rect"]),
            text=str(data.get("text", "")),
            color=str(data.get("color", "#FACC15")),
            font_size=float(data.get("font_size", 14.0)),
            text_color=str(data.get("text_color", "#2563EB")),
            created_at=str(data.get("created_at") or utc_now_iso()),
        )


@dataclass(slots=True)
class VocabularyCard:
    id: int
    document_id: str
    english: str
    vietnamese: str
    repetitions: int
    interval_days: float
    ease_factor: float
    due_at: str
    last_reviewed: str | None
    attempts: int
    correct: int


@dataclass(frozen=True, slots=True)
class StudyProject:
    id: str
    title: str
    kind: str
    path: str
    created_at: str
    last_opened: str
    card_count: int = 0
    folder_id: str | None = None


@dataclass(frozen=True, slots=True)
class StudyFolder:
    id: str
    name: str
    parent_id: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class ScheduleResult:
    repetitions: int
    interval_days: float
    ease_factor: float
    due_at: datetime
