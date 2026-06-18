from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ParsedDocument:
    source_path: Path
    original_path: Path
    paragraphs: List[str] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    conversion: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class DocParser(ABC):
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)

    @abstractmethod
    def parse(self) -> ParsedDocument:
        """Read a document and return paragraphs plus structured tables."""
