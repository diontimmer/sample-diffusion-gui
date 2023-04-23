# sample-diffusion-gui/Vextra Diffusion Toolkit

GUI toolkit for various audio diffusion operations. Run/Install using start_windows.bat or start_unix.sh.<br>
This will create a venv and install the requirements.<br>
This is mainly tested on Windows. OSX, Linux and WSL SHOULD work but there could be uncaught errors.<br>
WSL/Linux users might need to ```sudo apt install nvidia-cudnn```

### GIT & FFMPEG is required. <br>
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
- Input Wave Generation
- Model Trimming

Features are made accessible through an extension API; look in the extensions folder for examples!

## Note:
- Local Model Training is not recommended for systems with less than 8GB of VRAM.
- Please import your models through the included model importer. This ensures the models are trimmed and have the correct format for the filenames for use in     auto-complete.
- ```launch_script.py``` can be ran directly from your python interpreter if you do not want to use a venv.

![alt text](https://www.dropbox.com/s/p409s4n4w1jkf4b/vextrasamplediffusion.png?raw=1 "Sample Diffusion")<br>



## Citation

Various libs and snippets taken from:<br>
https://github.com/Harmonai-org/sample-generator<br>
https://github.com/sudosilico/sample-diffusion<br>

Special Thanks to:<br>
https://github.com/twobob<br>
https://github.com/zqevans<br>
https://github.com/drscotthawley<br>



