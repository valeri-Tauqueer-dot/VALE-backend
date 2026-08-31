from __future__ import annotations
import asyncio, io, logging, os
from .models import MediaResult, MediaType
from .validators import validate_image_bytes
logger=logging.getLogger(__name__)
class ImageProcessor:
    def __init__(self):
        self.enable_ocr=os.getenv('VALE_ENABLE_OCR','true').lower() in {'1','true','yes','on'}
        self.max_ocr_chars=int(os.getenv('VALE_MAX_OCR_CHARS','50000'))
    async def process(self,data,filename,content_type,user_message=''):
        return await asyncio.to_thread(self._process_sync,data,filename,content_type,user_message)
    def _process_sync(self,data,filename,content_type,user_message):
        validate_image_bytes(data); r=MediaResult(MediaType.IMAGE,filename,content_type)
        try:
            from PIL import Image,ImageOps
            with Image.open(io.BytesIO(data)) as im:
                im=ImageOps.exif_transpose(im)
                r.metadata.update(width=im.width,height=im.height,format=im.format,mode=im.mode)
        except Exception as exc:
            r.add_error(f'Image metadata processing failed: {exc}'); return r
        if self.enable_ocr:
            try:
                text=self._ocr(data)
                if text: r.extracted_text=text; r.structured_data['ocr_detected']=True
                else: r.structured_data['ocr_detected']=False
            except Exception as exc:
                r.add_warning('OCR was unavailable. Install/configure Tesseract to enable OCR.')
                logger.info('OCR unavailable: %s',exc)
        r.description=f"Image successfully received and validated. Resolution: {r.metadata.get('width','?')} × {r.metadata.get('height','?')}."
        if r.extracted_text: r.description += ' Visible text was detected and extracted.'
        r.structured_data['user_question']=user_message or None
        return r
    def _ocr(self,data):
        import pytesseract
        from PIL import Image,ImageOps
        with Image.open(io.BytesIO(data)) as im:
            im=ImageOps.exif_transpose(im).convert('RGB')
            text=pytesseract.image_to_string(im).strip()
        return text[:self.max_ocr_chars]
