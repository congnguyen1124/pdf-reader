from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pymupdf

from linguapdf.domain.models import Annotation


class PdfDocumentSession:
    SIDECAR_VERSION = 1

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.document = pymupdf.open(self.path)
        if self.document.needs_pass:
            self.document.close()
            raise ValueError("PDF được bảo vệ bằng mật khẩu và chưa được hỗ trợ.")
        if self.document.page_count == 0:
            self.document.close()
            raise ValueError("PDF không có trang nào để hiển thị.")
        self.document_id = self._fingerprint()
        self.annotations: list[Annotation] = []
        self.dirty = False
        self.load_annotations()

    @property
    def page_count(self) -> int:
        return self.document.page_count

    @property
    def title(self) -> str:
        metadata_title = (self.document.metadata or {}).get("title", "").strip()
        return metadata_title or self.path.stem

    @property
    def sidecar_path(self) -> Path:
        return self.path.with_suffix(self.path.suffix + ".linguapdf.json")

    def _fingerprint(self) -> str:
        digest = hashlib.sha256()
        with self.path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def annotations_for_page(self, page: int) -> list[Annotation]:
        return [annotation for annotation in self.annotations if annotation.page == page]

    def add_annotation(self, annotation: Annotation) -> None:
        if not 0 <= annotation.page < self.page_count:
            raise ValueError("Trang ghi chú không hợp lệ")
        self.annotations.append(annotation)
        self.dirty = True

    def remove_annotations(self, annotation_ids: set[str]) -> int:
        original_size = len(self.annotations)
        self.annotations = [item for item in self.annotations if item.id not in annotation_ids]
        removed = original_size - len(self.annotations)
        self.dirty = self.dirty or removed > 0
        return removed

    def update_annotation(
        self,
        annotation_id: str,
        *,
        rect: tuple[float, float, float, float] | None = None,
        text: str | None = None,
    ) -> Annotation | None:
        for annotation in self.annotations:
            if annotation.id != annotation_id:
                continue
            if rect is not None:
                annotation.rect = rect
            if text is not None:
                annotation.text = text
            self.dirty = True
            return annotation
        return None

    def undo_last(self) -> Annotation | None:
        if not self.annotations:
            return None
        self.dirty = True
        return self.annotations.pop()

    def load_annotations(self) -> None:
        if not self.sidecar_path.exists():
            return
        try:
            payload = json.loads(self.sidecar_path.read_text(encoding="utf-8"))
            self.annotations = [Annotation.from_dict(item) for item in payload.get("annotations", [])]
            self.dirty = False
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            self.annotations = []

    def save_annotations(self) -> Path:
        payload = {
            "version": self.SIDECAR_VERSION,
            "source_pdf": self.path.name,
            "document_id": self.document_id,
            "annotations": [item.to_dict() for item in self.annotations],
        }
        temporary = self.sidecar_path.with_suffix(self.sidecar_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.sidecar_path)
        self.dirty = False
        return self.sidecar_path

    def export_annotated_pdf(self, destination: str | Path) -> Path:
        destination_path = Path(destination).expanduser().resolve()
        if destination_path == self.path:
            raise ValueError("Hãy chọn tên khác để giữ an toàn cho PDF gốc.")

        shutil.copy2(self.path, destination_path)
        output = pymupdf.open(destination_path)
        try:
            for item in self.annotations:
                page = output[item.page]
                rect = pymupdf.Rect(*item.rect)
                color = _hex_to_rgb(item.color)
                if item.kind == "highlight":
                    annotation = page.add_highlight_annot(rect)
                    annotation.set_colors(stroke=color)
                    annotation.set_opacity(0.35)
                elif item.kind == "underline":
                    annotation = page.add_underline_annot(rect)
                    annotation.set_colors(stroke=color)
                elif item.kind == "strike":
                    annotation = page.add_strikeout_annot(rect)
                    annotation.set_colors(stroke=color)
                elif item.kind == "text":
                    annotation = page.add_freetext_annot(
                        rect,
                        item.text,
                        fontsize=10,
                        text_color=(0.10, 0.15, 0.25),
                        fill_color=color,
                    )
                    annotation.set_opacity(0.82)
                else:
                    continue
                annotation.set_info(content=item.text, title="LinguaPDF")
                annotation.update()
            output.saveIncr()
        finally:
            output.close()
        return destination_path

    def close(self) -> None:
        self.document.close()


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    cleaned = value.lstrip("#")
    if len(cleaned) != 6:
        return (0.98, 0.80, 0.08)
    return tuple(int(cleaned[index : index + 2], 16) / 255 for index in (0, 2, 4))  # type: ignore[return-value]

