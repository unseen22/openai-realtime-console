export type VoiceOptions = "alloy" | "ash" | "ballad" | "coral" | "echo" | "sage" | "shimmer" | "verse";

export interface SessionConfig {
    voice?: VoiceOptions;
    temperature?: number;
    instructions?: string;
    input_audio_transcription?: {
        model: string;
    };
    turn_detection?: any;
} 