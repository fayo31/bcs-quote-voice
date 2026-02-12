"""
BIEN CHEZ SOI - Transcription vocale avec OpenAI Whisper
Supporte français et anglais
"""

from openai import OpenAI
from config import Config
import tempfile
import os

client = OpenAI(api_key=Config.OPENAI_API_KEY)


def transcribe_audio(audio_file, language="fr"):
    """
    Transcrit un fichier audio en texte

    Args:
        audio_file: Fichier audio (wav, mp3, m4a, webm) ou stream
        language: Langue de transcription ('fr' ou 'en')

    Returns:
        dict: {'success': bool, 'text': str, 'language': str}
    """
    try:
        # Si c'est un stream (upload Flask), sauvegarder temporairement
        if hasattr(audio_file, 'read'):
            # Détecter l'extension depuis le nom du fichier
            fname = getattr(audio_file, 'filename', 'audio.webm') or 'audio.webm'
            ext = os.path.splitext(fname)[1] or '.webm'
            if ext not in ('.webm', '.mp4', '.m4a', '.wav', '.mp3', '.ogg'):
                ext = '.webm'
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(audio_file.read())
                tmp_path = tmp.name

            with open(tmp_path, 'rb') as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language=language
                )
            os.unlink(tmp_path)
        else:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language
            )

        return {
            'success': True,
            'text': transcript.text,
            'language': language
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
