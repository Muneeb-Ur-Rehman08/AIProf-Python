class AudioProcessor extends AudioWorkletProcessor {
  process(inputs, outputs) {
    const input = inputs[0];
    if (input.length > 0) {
      const audioData = input[0];
      this.port.postMessage({
        type: 'audio',
        buffer: audioData.slice()
      });
    }
    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor); 