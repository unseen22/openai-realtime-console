import json
import os
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# Set the path to your Vosk model directory
MODEL_PATH = "models/vosk-model-small-en-us-0.15"  # Update this to your model path

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Please download and unzip a Vosk model first.")

# Load the model
model = Model(MODEL_PATH)

# Define audio properties
sample_rate = 16000
device = None  # use default input device, or set your device index

# Create a Vosk recognizer
recognizer = KaldiRecognizer(model, sample_rate)

# A thread-safe queue for passing audio data between the callback and main thread
audio_queue = queue.Queue()

# Callback function for audio input
def audio_callback(indata, frames, time, status):
    if status:
        print(f"Audio status: {status}", flush=True)
    # Convert to byte data
    audio_queue.put(bytes(indata))

def main():
    # Start the audio stream
    with sd.RawInputStream(samplerate=sample_rate,
                           blocksize=8000,
                           dtype='int16',
                           channels=1,
                           callback=audio_callback,
                           device=device):
        print("Listening... press Ctrl+C to stop.")
        
        # Continuously read audio data from the queue and process
        while True:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                # If a full utterance is recognized, print it
                result = json.loads(recognizer.Result())
                if 'text' in result:
                    print("You said:", result['text'])
            else:
                # Partial results can also be obtained by:
                # partial_result = json.loads(recognizer.PartialResult())
                # print("Partial:", partial_result.get('partial', ''))
                pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopping transcription.")
