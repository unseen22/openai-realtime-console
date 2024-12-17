import { WavRecorder, WavStreamPlayer } from '../lib/wavtools/index.js';
import { RealtimeClient } from '@openai/realtime-api-beta';
import { transcribeLocal } from './conversationService';

export class AudioHandler {
  private wavRecorder: WavRecorder;
  private wavStreamPlayer: WavStreamPlayer;

  constructor() {
    this.wavRecorder = new WavRecorder({ sampleRate: 24000 });
    this.wavStreamPlayer = new WavStreamPlayer({ sampleRate: 24000 });
  }

  async initialize() {
    await this.wavRecorder.begin();
    await this.wavStreamPlayer.connect();
  }

  async cleanup() {
    await this.wavRecorder.end();
    await this.wavStreamPlayer.interrupt();
  }

  async startRecording(onAudioData: (data: Int16Array | Float32Array) => void) {
    await this.wavRecorder.record((data) => {
      onAudioData(data.mono);
    });
  }

  async stopRecording() {
    await this.wavRecorder.pause();
    const audioData = await this.wavRecorder.save();
    
    // Reset the recorder after saving
    await this.wavRecorder.end();  // End current session
    await this.wavRecorder.begin(); // Start fresh session
    
    const arrayBuffer = await audioData.blob.arrayBuffer();
    return new Int16Array(arrayBuffer);
  }

  async playAudio(audioData: Uint8Array, trackId: string) {
    this.wavStreamPlayer.add16BitPCM(audioData, trackId);
  }

  async interruptPlayback() {
    return await this.wavStreamPlayer.interrupt();
  }

  getRecorderStatus() {
    return this.wavRecorder.getStatus();
  }

  getRecorderFrequencies() {
    return this.wavRecorder.recording
      ? this.wavRecorder.getFrequencies('voice')
      : { values: new Float32Array([0]) };
  }

  getPlayerFrequencies() {
    return this.wavStreamPlayer.analyser
      ? this.wavStreamPlayer.getFrequencies('voice')
      : { values: new Float32Array([0]) };
  }

  static async decodeAudio(audio: Uint8Array) {
    return await WavRecorder.decode(audio, 24000, 24000);
  }

  async transcribeAudio(): Promise<string | null> {
    const audioData = await this.stopRecording();
    const transcription = await transcribeLocal(audioData);
    return transcription?.text || null;
  }
} 