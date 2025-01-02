import { WavPacker } from '../lib/wavtools';

export class TranscriptionService {
  private static readonly API_URL = 'https://api.openai.com/v1/audio/transcriptions';
  private apiKey: string;

  constructor() {
    this.apiKey = ''; // Replace with your actual API key
  }

  async transcribeAudio(audioData: Float32Array): Promise<string> {
    try {
      // Convert Float32Array to WAV file
      const wavBlob = await this.convertToWav(audioData);
      
      // Create form data
      const formData = new FormData();
      formData.append('file', wavBlob, 'audio.wav');
      formData.append('model', 'whisper-1');

      // Debug log the API key format (first few chars)
      console.log('Using API key format:', `Bearer ${this.apiKey.substring(0, 5)}...`);

      // Make API request
      const response = await fetch(TranscriptionService.API_URL, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
        },
        body: formData
      });

      if (!response.ok) {
        const errorBody = await response.text();
        console.error('Transcription API error details:', {
          status: response.status,
          statusText: response.statusText,
          body: errorBody
        });
        throw new Error(`Transcription failed: ${response.status} ${response.statusText} - ${errorBody}`);
      }

      const result = await response.json();
      return result.text;
    } catch (error) {
      console.error('Transcription error:', error);
      throw error;
    }
  }

  private async convertToWav(audioData: Float32Array): Promise<Blob> {
    const packer = new WavPacker();
    const sampleRate = 24000; // Match the sample rate used in WavRecorder
    
    // Pack the audio data into WAV format
    const packedAudio = packer.pack(sampleRate, {
      bitsPerSample: 16,
      channels: [audioData], // Mono audio
      data: new Int16Array(WavPacker.floatTo16BitPCM(audioData))
    });
    
    return packedAudio.blob;
  }
}