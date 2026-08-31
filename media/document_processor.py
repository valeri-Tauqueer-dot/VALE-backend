from __future__ import annotations
import asyncio,io,logging,os
from .models import MediaResult,MediaType
from .validators import DEFAULT_LIMITS,MediaValidationError
logger=logging.getLogger(__name__)
class DocumentProcessor:
    def __init__(self): self.max_pages=DEFAULT_LIMITS.max_pdf_pages; self.max_text_chars=DEFAULT_LIMITS.max_extracted_text_chars
    async def process(self,data,filename,content_type,user_message=''):
        return await asyncio.to_thread(self._process_sync,data,filename,content_type,user_message)
    def _process_sync(self,data,filename,content_type,user_message):
        r=MediaResult(MediaType.DOCUMENT,filename,content_type)
        try:
            if content_type=='application/pdf': text,meta=self._pdf(data)
            elif content_type=='text/plain': text,meta=self._text(data)
            elif content_type.startswith('application/vnd.openxmlformats-officedocument.wordprocessingml.document'): text,meta=self._docx(data)
            else: raise MediaValidationError(f'Unsupported document type: {content_type}')
            text=text[:self.max_text_chars]; r.extracted_text=text; r.metadata.update(meta); r.structured_data.update(characters_extracted=len(text),user_question=user_message or None); r.description='Document content was extracted successfully.'
            if not text.strip(): r.add_warning('No readable text was extracted from the document.')
        except Exception as exc: r.add_error(f'Document processing failed: {exc}')
        return r
    def _pdf(self,data):
        import pypdf; reader=pypdf.PdfReader(io.BytesIO(data))
        if reader.is_encrypted: raise MediaValidationError('Password-protected PDFs are not supported.')
        if len(reader.pages)>self.max_pages: raise MediaValidationError(f'PDF exceeds the {self.max_pages}-page limit.')
        out=[]
        for i,p in enumerate(reader.pages,1): out.append(f'\n\n--- PAGE {i} ---\n{p.extract_text() or ""}')
        return ''.join(out),{'page_count':len(reader.pages),'document_format':'pdf'}
    def _text(self,data): return data.decode('utf-8',errors='replace'),{'document_format':'txt'}
    def _docx(self,data):
        from docx import Document; doc=Document(io.BytesIO(data)); return '\n'.join(p.text for p in doc.paragraphs),{'document_format':'docx'}
