# this scripts installs necessary requirements and launches main program
import subprocess
import os
import sys
import importlib.util
import urllib.request
from shutil import which

python = sys.executable
git = os.environ.get('GIT', "git")
index_url = os.environ.get('INDEX_URL', "")
platform = sys.platform

def prRed(skk): print(f"\033[91m{skk}\033[00m") 
def prGreen(skk): print(f"\033[92m{skk}\033[00m")
def prYellow(skk): print(f"\033[93m{skk}\033[00m")

prGreen('Starting launch script...')

def run(command, desc=None, errdesc=None, custom_env=None, live=False):
    if desc is not None:
        print(desc)

    if live:
        result = subprocess.run(command, shell=True, env=os.environ if custom_env is None else custom_env)
        if result.returncode != 0:
            raise RuntimeError(f"""{errdesc or 'Error running command'}.
Command: {command}
Error code: {result.returncode}""")

        return ""

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ if custom_env is None else custom_env)

    if result.returncode != 0:

        message = f"""{errdesc or 'Error running command'}.
Command: {command}
Error code: {result.returncode}
stdout: {result.stdout.decode(encoding="utf8", errors="ignore") if len(result.stdout)>0 else '<empty>'}
stderr: {result.stderr.decode(encoding="utf8", errors="ignore") if len(result.stderr)>0 else '<empty>'}
"""
        raise RuntimeError(message)

    return result.stdout.decode(encoding="utf8", errors="ignore")

def is_installed(package):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return False

    return spec is not None


def run_pip(args, desc=None):
    index_url_line = f' --index-url {index_url}' if index_url != '' else ''
    return run(f'"{python}" -m pip {args} --prefer-binary{index_url_line}', desc=f"Installing {desc}", errdesc=f"Couldn't install {desc}")




if __name__ == "__main__":
    # env setup check
    if not is_installed("torch"):
        torch_command = os.environ.get('TORCH_COMMAND', "pip install torch==1.13.1+cu117 --extra-index-url https://download.pytorch.org/whl/cu117")
        run(f'"{python}" -m {torch_command}', "Installing torch.", "Couldn't install torch", live=True)
        run_pip(f"install .", "requirements")


    if which('ffmpeg') is None:
        if platform == 'win32':
            prYellow('No FFMPEG detected! Opening installer..')
            urllib.request.urlretrieve("https://github.com/icedterminal/ffmpeg-installer/releases/download/5.1.0.20220727/FFmpeg_Essentials.msi", "ffmpeg_installer.msi")
            subprocess.run("ffmpeg_installer.msi", shell=True)
            os.remove("ffmpeg_installer.msi")

        elif platform == 'linux':
            prRed('No FFMPEG detected! Please update pkgs and run "sudo apt install ffmpeg" to install before using the GUI!')
            exit()

        elif platform == 'darwin':
            prRed('No FFMPEG detected! Please use homebrew "brew install ffmpeg" to install before using the GUI!')
            exit()

    import main_gui
