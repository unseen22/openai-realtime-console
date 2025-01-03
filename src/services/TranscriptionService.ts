export class TranscriptionService {
  private static readonly API_URL = 'https://api.openai.com/v1/audio/transcriptions';
  private apiKey: string;

  constructor() {
    this.apiKey = ''}

  async transcribeAudio(audioData: Float32Array): Promise<string> {
    console.time('convertToWav');
    const wavBlob = this.convertToWav(audioData);
    console.timeEnd('convertToWav');

    console.time('apiCall');
    // Create form data
    const formData = new FormData();
    formData.append('file', wavBlob, 'audio.wav');
    formData.append('model', 'whisper-1');

    // Make API request
    const response = await fetch(TranscriptionService.API_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
      },
      body: formData
    });
    console.timeEnd('apiCall');

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
  }

  private convertToWav(audioData: Float32Array): Blob {
    const sampleRate = 16000; // Use a lower sample rate if supported
    const channels = 1; // Mono audio
    const bytesPerSample = 2; // 16-bit PCM

    // Convert Float32 to 16-bit PCM
    const int16Data = new Int16Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) {
      int16Data[i] = Math.min(Math.max(Math.round(audioData[i] * 32767), -32767), 32767);
    }

    // Create WAV header
    const buffer = new ArrayBuffer(44 + int16Data.byteLength);
    const view = new DataView(buffer);

    const writeString = (view: DataView, offset: number, string: string): void => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    // RIFF chunk descriptor
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + int16Data.byteLength, true); // Big Endian false
    writeString(view, 8, 'WAVE');
    // FMT subchunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // Subchunk size
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, channels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * channels * bytesPerSample, true);
    view.setUint16(32, channels * bytesPerSample, true);
    view.setUint16(34, 16, true); // Bits per sample
    // Data subchunk
    writeString(view, 36, 'data');
    view.setUint32(40, int16Data.byteLength, true);

    // Copy the audio data
    const audioBuffer = new Uint8Array(buffer, 44);
    audioBuffer.set(new Uint8Array(int16Data.buffer));

    return new Blob([buffer], { type: 'audio/wav' });
  }
}