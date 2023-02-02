# sample-diffusion-gui

GUI fork of the Dance Diffusion/Sample Generator cli library for Windows. Run/Install using start_windows.bat.<br>
This will create a venv and install the requirements.

FFMpeg is required. start_windows.bat will automatically check for ffmpeg and download icedterminals MSI package. <br>
https://github.com/icedterminal/ffmpeg-installer.

Requires Python 3.10

Includes additional features such as:<br>
- Model merging
- Instant input load for variation
- Batch looping


![alt text](https://www.dropbox.com/s/p409s4n4w1jkf4b/vextrasamplediffusion.png?raw=1 "Sample Diffusion")



Please place your model .ckpt files in the /models folder.

Various libs and snippets taken from:<br>
https://github.com/Harmonai-org/sample-generator<br>
https://github.com/sudosilico/sample-diffusion<br>
