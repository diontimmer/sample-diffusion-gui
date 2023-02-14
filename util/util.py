import os
import torch
import torchaudio
from pydub import AudioSegment, effects
from util.scripts.note_detect import detect_notes


def tensor_slerp_2D(a: torch.Tensor, b: torch.Tensor, t: float):
    slerped = torch.empty_like(a)
    
    for channel in range(a.size(0)):
        slerped[channel] = tensor_slerp(a[channel], b[channel], t)
    
    return slerped


def tensor_slerp(a: torch.Tensor, b: torch.Tensor, t: float):
    omega = torch.arccos(torch.dot(a / torch.linalg.norm(a), b / torch.linalg.norm(b)))
    so = torch.sin(omega)
    return torch.sin((1.0-t) * omega) / so * a + torch.sin(t * omega) / so * b


def load_audio(device, audio_path: str, sample_rate):
    
    if not os.path.exists(audio_path):
        print(f"Audio file not found: {audio_path}")

    audio, file_sample_rate = torchaudio.load(audio_path)

    if file_sample_rate != sample_rate:
        resample = torchaudio.transforms.Resample(file_sample_rate, sample_rate)
        audio = resample(audio)

    return audio.to(device)


def save_audio(audio_out, output_path: str, sample_rate, id_str:str = None, modelname='Sample'):
    saved_paths = []
    if not os.path.exists(os.path.join(output_path, modelname)):
        os.makedirs(os.path.join(output_path, modelname))

    for ix, sample in enumerate(audio_out, start=1):
        output_file = os.path.join(output_path, modelname, f"{modelname}_{id_str}_{ix}.wav")
        if os.path.exists(output_file):
            os.remove(output_file)

        open(output_file, "a").close()
        
        output = sample.cpu()

        torchaudio.save(output_file, output, sample_rate, encoding='PCM_S', bits_per_sample=16)

        # silence trim
        sound = AudioSegment.from_file(output_file)
        start_trim = detect_leading_silence(sound)
        end_trim = detect_leading_silence(sound.reverse())
        duration = len(sound)
        trimmed_sound = sound[start_trim:duration - end_trim]

        # normalize
        normalized_sound = effects.normalize(trimmed_sound, headroom=1.0)
        normalized_sound.export(output_file, format="wav")
        try:
            note = detect_notes(output_file)
        except:
            note = 'X'
        # rename output_file with note before extension
        keyed_output_file = os.path.splitext(output_file)[0] + "_" + note + os.path.splitext(output_file)[1]
        if os.path.exists(keyed_output_file):
            os.remove(keyed_output_file)
        os.rename(output_file, keyed_output_file)
        saved_paths.append(keyed_output_file)
    return saved_paths


def detect_leading_silence(sound, silence_threshold=-50.0, chunk_size=1):
    trim_ms = 0
    assert chunk_size > 0
    while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold and trim_ms < len(sound):
        trim_ms += chunk_size

    return trim_ms


def cropper(samples: int, randomize: bool = True):

    def crop(source: torch.Tensor, offset_in: int = None) -> torch.Tensor:
        n_channels, n_samples = source.shape
        
        offset = 0
        if (offset_in):
            offset = min(offset_in, n_samples - samples)
        elif (randomize):
            offset = torch.randint(0, max(0, n_samples - samples) + 1, []).item()
        
        chunk = source.new_zeros([n_channels, samples])
        chunk [:, :min(n_samples, samples)] = source[:, offset:offset + samples]
        
        return chunk

    return crop