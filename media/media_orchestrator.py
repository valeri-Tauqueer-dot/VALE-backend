from __future__ import annotations
import logging
from .models import MediaResult,MediaType
from .validators import validate_upload,MediaValidationError
from .image_processor import ImageProcessor
from .audio_processor import AudioProcessor
from .document_processor import DocumentProcessor
logger=logging.getLogger(__name__)
class MediaOrchestrator:
    def __init__(self): self.image_processor=ImageProcessor(); self.audio_processor=AudioProcessor(); self.document_processor=DocumentProcessor()
    async def process(self,data,filename,content_type,user_message=''):
        safe,typ,kind=validate_upload(data,filename,content_type)
        logger.info('VALE media: type=%s filename=%s bytes=%s',kind.value,safe,len(data))
        if kind is MediaType.IMAGE: return await self.image_processor.process(data,safe,typ,user_message)
        if kind is MediaType.AUDIO: return await self.audio_processor.process(data,safe,typ,user_message)
        if kind is MediaType.DOCUMENT: return await self.document_processor.process(data,safe,typ,user_message)
        raise MediaValidationError('VALE could not determine how to process this media.')
    def supported_media(self):
        return {'images':['image/jpeg','image/png','image/webp'],'audio':['audio/webm','audio/wav','audio/mpeg','audio/mp3','audio/mp4','audio/ogg','audio/aac'],'documents':['application/pdf','text/plain','application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
