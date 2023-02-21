import struct
import numpy as np
from scipy import signal as sig
import librosa
import wave
import os


def create_signal(keys, sample_rate, sample_length, amplitude=100, waveform='sine', output_folder='output'):
    awaves = []
    for key in keys:
        key = key.replace(key[-1], str(int(key[-1]) - 2))
        freq = librosa.note_to_hz(key)  # Frequency in Hz
        x = np.arange(sample_length)

        if waveform == 'Sine':
            awave = 100*np.sin(2 * np.pi * freq * x / sample_rate)
        elif waveform == 'Square':
            awave = 100*sig.square(2 * np.pi * freq * x / sample_rate)
        elif waveform == 'Saw':
            awave = 100*sig.sawtooth(2 * np.pi * freq * x / sample_rate)
        awaves.append(awave)

    awave = np.sum(awaves, axis=0)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    filename = f'{output_folder}/{waveform}_{"_".join(keys)}_{sample_rate}hz_n{sample_length}.wav'
    wav_file=wave.open(filename, 'w')
    wav_file.setparams((2, 2, int(sample_rate), sample_length, "NONE", "not compressed"))

    for s in awave:
        wav_file.writeframes(struct.pack('h', int(s*amplitude)))
    return filename