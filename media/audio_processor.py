from __future__ import annotations
import asyncio, logging, os
from .models import MediaResult,MediaType
logger=logging.getLogger(__name__)
class AudioProcessor:
    def __init__(self):
        self.enable_transcription=os.getenv('VALE_ENABLE_AUDIO_TRANSCRIPTION','false').lower() in {'1','true','yes','on'}
        self.engine=os.getenv('VALE_AUDIO_ENGINE','none').lower().strip()
    async def process(self,data,filename,content_type,user_message=''):
        return await asyncio.to_thread(self._process_sync,data,filename,content_type,user_message)
    def _process_sync(self,data,filename,content_type,user_message):
        r=MediaResult(MediaType.AUDIO,filename,content_type)
        r.metadata.update(size_bytes=len(data))
        r.structured_data['user_question']=user_message or None
        r.structured_data['audio_received']=True
        # Receiving/forwarding browser audio must never depend on Whisper/ffmpeg.
        if not self.enable_transcription or self.engine in {'','none','off','disabled'}:
            r.description='Audio successfully received and validated. Speech transcription is not enabled on this deployment.'
            r.add_warning('Speech transcription is disabled; audio upload itself is working.')
            return r
        try:
            result=self._transcribe(data,filename)
            text=(result.get('text') or '').strip()
            if text: r.extracted_text=text
            r.structured_data.update({'transcript':text,'language':result.get('language'),'engine':self.engine})
            r.description='Speech was transcribed from the uploaded audio.' if text else 'Audio received, but no recognizable speech was detected.'
            if not text: r.add_warning('No recognizable speech was found in the audio.')
        except Exception as exc:
            # Transcription failure is partial, not an upload failure.
            logger.warning('Transcription unavailable: %s',exc)
            r.description='Audio successfully received. Transcription was unavailable, but the media upload completed.'
            r.add_warning(f'Transcription unavailable: {exc}')
        return r
    def _transcribe(self,data,filename):
        if self.engine!='faster-whisper': raise RuntimeError('Unsupported audio engine.')
        from faster_whisper import WhisperModel
        model=WhisperModel(os.getenv('VALE_WHISPER_MODEL','tiny'),device=os.getenv('VALE_WHISPER_DEVICE','cpu'),compute_type=os.getenv('VALE_WHISPER_COMPUTE_TYPE','int8'))
        # faster-whisper can consume the saved path; use a temp file with the original extension.
        import tempfile
        suffix=os.path.splitext(filename)[1] or '.webm'
        with tempfile.NamedTemporaryFile(suffix=suffix,delete=False) as f: f.write(data); path=f.name
        try:
            segments,info=model.transcribe(path,vad_filter=True); text=' '.join((s.text or '').strip() for s in segments).strip(); return {'text':text,'language':getattr(info,'language',None)}
        finally:
            try: os.remove(path)
            except OSError: pass
