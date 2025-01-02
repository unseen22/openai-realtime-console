import os
from pathlib import Path
import torch
import whisper
import numpy as np
import soundfile as sf

def test_whisper_setup():
    # Set up paths
    BASE_DIR = Path(__file__).parent.parent
    AUDIO_DIR = BASE_DIR / "audio_cache"
    MODEL_DIR = BASE_DIR / "models"
    
    # Create directories
    AUDIO_DIR.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(exist_ok=True)
    
    # Set Whisper cache directory
    os.environ["WHISPER_MODEL_DIR"] = str(MODEL_DIR)
    
    print("\n=== Testing Whisper Setup ===")
    
    # 1. Test CUDA availability
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n1. Using device: {device}")
    
    # 2. Test model loading
    print("\n2. Loading Whisper model...")
    try:
        model = whisper.load_model("base", download_root=MODEL_DIR).to(device)
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        return
    
    # 3. Create test audio
    print("\n3. Creating test audio...")
    try:
        # Create a simple sine wave
        sample_rate = 16000
        duration = 2  # seconds
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
        
        test_file = AUDIO_DIR / "test.wav"
        sf.write(test_file, audio, sample_rate)
        print(f"✓ Test audio created at {test_file}")
    except Exception as e:
        print(f"✗ Failed to create test audio: {e}")
        return
    
    # 4. Test audio loading
    print("\n4. Testing Whisper audio loading...")
    try:
        audio = whisper.load_audio(str(test_file))
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(device)
        print("✓ Audio loaded and processed successfully")
    except Exception as e:
        print(f"✗ Failed to load audio: {e}")
        return
    
    # 5. Test transcription
    print("\n5. Testing transcription...")
    try:
        options = whisper.DecodingOptions(language="en", fp16=False)
        result = model.decode(mel, options)
        print("✓ Transcription completed")
        print(f"Transcription result: {result.text}")
    except Exception as e:
        print(f"✗ Failed to transcribe: {e}")
        return
    
    # Clean up
    try:
        test_file.unlink()
        print("\n✓ Test file cleaned up")
    except Exception as e:
        print(f"\n✗ Failed to clean up test file: {e}")
    
    print("\n=== All tests completed successfully ===")

if __name__ == "__main__":
    test_whisper_setup() 