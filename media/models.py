from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

class MediaType(str, Enum):
    IMAGE='image'; AUDIO='audio'; DOCUMENT='document'; TEXT='text'; UNKNOWN='unknown'
class ProcessingStatus(str, Enum):
    SUCCESS='success'; PARTIAL='partial'; FAILED='failed'
class MediaError(Exception): pass

@dataclass
class MediaResult:
    media_type: MediaType
    filename: str
    content_type: str
    status: ProcessingStatus = ProcessingStatus.SUCCESS
    description: str = ''
    extracted_text: str = ''
    structured_data: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def add_warning(self, message: str) -> None:
        if message and message not in self.warnings: self.warnings.append(message)
        if self.status == ProcessingStatus.SUCCESS: self.status = ProcessingStatus.PARTIAL
    def add_error(self, message: str) -> None:
        if message and message not in self.errors: self.errors.append(message)
        self.status = ProcessingStatus.FAILED
    def build_brain_context(self, max_text_chars: int = 50000) -> str:
        parts=['=== VALE MEDIA CONTEXT ===',f'Media type: {self.media_type.value}',f'Filename: {self.filename}']
        if self.description: parts += ['', 'MEDIA UNDERSTANDING:', self.description]
        if self.extracted_text:
            text=self.extracted_text.strip(); text=text if len(text)<=max_text_chars else text[:max_text_chars]+'\n\n[Media text truncated for context size.]'
            parts += ['', 'EXTRACTED CONTENT:', text]
        if self.structured_data:
            parts += ['', 'STRUCTURED INFORMATION:']
            parts += [f'{k}: {v}' for k,v in self.structured_data.items() if v is not None]
        if self.metadata:
            parts += ['', 'MEDIA METADATA:']
            parts += [f'{k}: {v}' for k,v in self.metadata.items() if v is not None]
        if self.warnings: parts += ['', 'PROCESSING WARNINGS:'] + [f'- {x}' for x in self.warnings]
        if self.errors: parts += ['', 'PROCESSING ERRORS:'] + [f'- {x}' for x in self.errors]
        parts += ['', '=== END VALE MEDIA CONTEXT ===']
        return '\n'.join(parts)
    def to_dict(self, include_full_text: bool=True) -> Dict[str, Any]:
        data=asdict(self); data['media_type']=self.media_type.value; data['status']=self.status.value
        if not include_full_text: data.pop('extracted_text',None)
        return data
