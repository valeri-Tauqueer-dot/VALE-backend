from __future__ import annotations
import io, os, re
from dataclasses import dataclass
from typing import Dict, Optional, Set
from .models import MediaError, MediaType
class MediaValidationError(MediaError): pass
@dataclass(frozen=True)
class MediaLimits:
    max_image_bytes:int; max_audio_bytes:int; max_document_bytes:int; max_pdf_pages:int; max_extracted_text_chars:int
def _env_int(name, default):
    try: return int(os.getenv(name, str(default)))
    except (TypeError,ValueError): return default
DEFAULT_LIMITS=MediaLimits(_env_int('VALE_MAX_IMAGE_BYTES',10*1024*1024),_env_int('VALE_MAX_AUDIO_BYTES',30*1024*1024),_env_int('VALE_MAX_DOCUMENT_BYTES',30*1024*1024),_env_int('VALE_MAX_PDF_PAGES',200),_env_int('VALE_MAX_EXTRACTED_TEXT_CHARS',1_000_000))
IMAGE_TYPES={'image/jpeg','image/png','image/webp'}
AUDIO_TYPES={'audio/webm','audio/wav','audio/x-wav','audio/mpeg','audio/mp3','audio/mp4','audio/x-m4a','audio/ogg','audio/aac'}
DOCUMENT_TYPES={'application/pdf','text/plain','application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
EXTENSION_TO_CONTENT_TYPE={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp','.webm':'audio/webm','.wav':'audio/wav','.mp3':'audio/mpeg','.ogg':'audio/ogg','.m4a':'audio/mp4','.aac':'audio/aac','.pdf':'application/pdf','.txt':'text/plain','.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
def sanitize_filename(filename:Optional[str])->str:
    name=os.path.basename(filename or 'unnamed_file').replace('\x00',''); name=re.sub(r'[^a-zA-Z0-9._()\- ]','_',name).strip(); return (name or 'unnamed_file')[:255]
def normalize_content_type(content_type:Optional[str],filename:str)->str:
    if content_type:
        value=content_type.split(';',1)[0].strip().lower()
        if value: return value
    return EXTENSION_TO_CONTENT_TYPE.get(os.path.splitext(filename.lower())[1],'application/octet-stream')
def detect_media_type(content_type:str)->MediaType:
    if content_type in IMAGE_TYPES or content_type.startswith('image/'): return MediaType.IMAGE
    if content_type in AUDIO_TYPES or content_type.startswith('audio/'): return MediaType.AUDIO
    if content_type in DOCUMENT_TYPES: return MediaType.DOCUMENT
    return MediaType.UNKNOWN
def get_max_size(media_type,limits=DEFAULT_LIMITS):
    return {MediaType.IMAGE:limits.max_image_bytes,MediaType.AUDIO:limits.max_audio_bytes,MediaType.DOCUMENT:limits.max_document_bytes}.get(media_type,0)
def validate_upload(data:bytes,filename:Optional[str],content_type:Optional[str],limits=DEFAULT_LIMITS):
    safe=sanitize_filename(filename); typ=normalize_content_type(content_type,safe); kind=detect_media_type(typ)
    if kind is MediaType.UNKNOWN: raise MediaValidationError('Unsupported media type. Supported types are images, audio, PDF, TXT and DOCX.')
    if not data: raise MediaValidationError('The uploaded file is empty.')
    limit=get_max_size(kind,limits)
    if len(data)>limit: raise MediaValidationError(f'File is too large. Maximum size for {kind.value} is {limit/(1024*1024):.0f} MB.')
    return safe,typ,kind
def validate_image_bytes(data:bytes)->None:
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im: im.verify()
    except Exception as exc: raise MediaValidationError('The uploaded image is corrupted or invalid.') from exc
