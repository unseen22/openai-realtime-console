import os
from openai import OpenAI
from fastapi import UploadFile
import tempfile

class TranscriptionHandler:
    def __init__(self):
        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=""
        )

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio data using OpenAI's Whisper API
        """
        temp_file_path = None
        try:
            # Create a temporary WAV file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
                temp_file_path = temp_audio.name
                # Write the audio data to the temporary file
                temp_audio.write(audio_data)
                temp_audio.flush()
                # Close the file explicitly
                temp_audio.close()

            # Open and transcribe in a separate context
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )

            print(f"Transcription: {transcript.text}")
            return transcript.text

        except Exception as e:
            print(f"Error in transcription: {str(e)}")
            raise e
        finally:
            # Clean up in finally block to ensure it runs
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    print(f"Warning: Could not delete temporary file: {str(e)}")
        

transcription_handler = TranscriptionHandler() 