import os
from openai import OpenAI
from fastapi import UploadFile
import tempfile

class TranscriptionHandler:
    def __init__(self):
        """Initialize OpenAI client"""
        self.client = OpenAI(
            api_key="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"
        )
        self._temp_files = []

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio data using OpenAI's Whisper API"""
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                self._temp_files.append(temp_file.name)
                temp_file_path = temp_file.name

            # Open the temporary file and transcribe
            with open(temp_file_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )

            return transcript.text

        except Exception as e:
            print(f"Error in transcribe_audio: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {str(e)}"
            )
        finally:
            # Cleanup temp file
            try:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    self._temp_files.remove(temp_file_path)
            except Exception as e:
                print(f"Warning: Failed to cleanup temp file: {str(e)}")

    async def close(self):
        """Cleanup resources"""
        # Cleanup any remaining temporary files
        for temp_file in self._temp_files[:]:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                self._temp_files.remove(temp_file)
            except Exception as e:
                print(f"Warning: Failed to cleanup temp file on close: {str(e)}")

transcription_handler = TranscriptionHandler() 