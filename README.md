# sample-diffusion-gui

GUI fork of the Dance Diffusion/Sample Generator cli library. Run/Install using start_windows.bat or start_unix.sh.<br>
This will create a venv and install the requirements.<br>
This is mainly tested on Windows. OSX, Linux and WSL SHOULD work but there could be uncaught errors.<br>
WSL/Linux users might need to ```sudo apt install nvidia-cudnn```



### FFMPEG is required. <br>
Linux users can install ffmpeg by updating packages and running ```sudo apt install ffmpeg```<br>
OSX users can install by using homebrew: ```brew install ffmpeg```<br>

for windows: start_windows.bat will automatically check for ffmpeg and download icedterminals MSI package. <br>
https://github.com/icedterminal/ffmpeg-installer.

Requires Python 3.10

Includes additional features such as:<br>
- Model merging
- Instant input load for variation
- Batch looping
- Local model training

Note: Local Model Training is not recommended for systems with less than 8GB of VRAM.


![alt text](https://www.dropbox.com/s/p409s4n4w1jkf4b/vextrasamplediffusion.png?raw=1 "Sample Diffusion")



Please import your models through the included model importer. This ensures the models are trimmed and have the correct format for the filenames for use in auto-complete.

Various libs and snippets taken from:<br>
https://github.com/Harmonai-org/sample-generator<br>
https://github.com/sudosilico/sample-diffusion<br>
