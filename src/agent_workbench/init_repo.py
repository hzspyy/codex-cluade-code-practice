"""Repository bootstrap helpers."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .templates import TEMPLATES


@dataclass(frozen=True)
class InitResult:
    root: str
    created: tuple[str, ...]
    skipped: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "created": list(self.created),
            "skipped": list(self.skipped),
        }


def init_repository(root: Path, *, force: bool = False) -> InitResult:
    root = root.resolve()
    created: list[str] = []
    skipped: list[str] = []

    for rel, content in TEMPLATES.items():
        target = root / rel
        if target.exists() and not force:
            skipped.append(rel)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        created.append(rel)
        if rel.endswith(".sh") or rel.startswith(".githooks/"):
            _make_executable(target)

    return InitResult(root=str(root), created=tuple(created), skipped=tuple(skipped))


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
