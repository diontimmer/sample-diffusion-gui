from setuptools import setup, find_packages

setup(
  name="sample-diffusion",
  version="0.0.1",
  description="",
  packages=find_packages(),
  install_requires=[
    "black",
    "diffusers",
    "tqdm",
    "PySimpleGUI",
    "torchaudio",
    "pydub",
    "ema_pytorch",
    "pytorch_lightning",
    "pygame",
    "soundfile",
    "imageio-ffmpeg",
    "prefigure",
    "wandb",
    "einops",
    "matplotlib",
    "pandas",
    "librosa"
  ]
)
