const fs = require('fs');

function validateWavFile(filePath) {
    const buffer = fs.readFileSync(filePath);
    
    // Check file size
    console.log('File size:', buffer.length, 'bytes');
    
    // Check RIFF header
    const riff = buffer.slice(0, 4).toString('ascii');
    console.log('RIFF header:', riff);
    
    // Check WAVE format
    const wave = buffer.slice(8, 12).toString('ascii');
    console.log('WAVE format:', wave);
    
    // Check fmt chunk
    const fmt = buffer.slice(12, 16).toString('ascii');
    console.log('FMT chunk:', fmt);
    
    // Audio format (PCM = 1)
    const audioFormat = buffer.readUInt16LE(20);
    console.log('Audio format:', audioFormat);
    
    // Number of channels
    const numChannels = buffer.readUInt16LE(22);
    console.log('Number of channels:', numChannels);
    
    // Sample rate
    const sampleRate = buffer.readUInt32LE(24);
    console.log('Sample rate:', sampleRate);
    
    // Bits per sample
    const bitsPerSample = buffer.readUInt16LE(34);
    console.log('Bits per sample:', bitsPerSample);
}

validateWavFile('audio_instruct/test_instruct.wav'); 