import os
import glob
import PySimpleGUI as sg
from threading import Thread
import re
from util.scripts.trim_model import start_trim, prune_latent_uncond
from util.scripts.note_detect import detect_notes
from util.scripts.merge_models_ratio import ratio_merge
import torch
import torchaudio
import gc
import pickle
import sys
import time
import tkinter as tk
import shutil
from torch.cuda import empty_cache
import dance_diffusion as dd
import argparse
import json
from pydub import AudioSegment, effects
import subprocess

# block pygame welcome message

sys.stdout = open(os.devnull, "w")
from pygame import mixer  # noqa: E402
import pygame   # noqa: E402

# reroute stdout back
sys.stdout = sys.__stdout__

pygame.init()
mixer.init()
current_sound_channel = mixer.Channel(2)

file_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACUUlEQVR42o3SXUhTcRgG8Gc7+9ANXVpizCyQoTCiYNMEMYKCoiNGZjYQL6SPG6uLgsjM6qIsqAvBuii6qMi6qJmFHksrp/Zhajnxo5Ezp5tzbHO6Td3Wds75ZzfepEcfeO8efi+8vCKsEtUz/4GT+vh3SgqoHwyfHy/eULtST7QakPk+QN/UKZmwgoI/yKGuI1htNSTXrBtIezFLn9mVwExSEsgkPJQ8wd0n7usLVWlX1wVsfjpDn81LZJxxEiwu1SgRD8fkH3Q+clySEO5O6KGWEwRS7nvoc3Qy88YSgdPiRw6dCqmcgrnNC8+Qf2+gLsskCGysnaYrDqcwTcNhDFT2XFOXZ13ceTRd4f01D+dAwOmqTN8iCCTdmKCPG9TM2+9BjDbYtaxRZ9nREiBEKobfGppyVKSmCwKqy+N0WZmaae0JwPZyQscxuWbNcy8RK+Tw9c1M+Woy1gCujB0sOqZu+dg1B5dxTMea9pgz2mIkZJ2Dv93mizTkbhIEkPNh/5EHu1u7TR64jUN6vpvuTzjRS6LOBQuJktvR9n2P/wcKv1rzs1Wa+BiHUJRF5qnteFU/hfnm4QL+x6GWlfYsA0kln0cu3MvTukQieGcJIhEOdl8MP5sdYL+MFrC9hcJASZOHkG1JMHYFIQUBlj6PUsggMjsQ7Rws4oZLXwsC+UYPccvi4LJHIBETsLGlUSoRY4Z+c415mtVOtQxsPf1tRF6o19rGFyHlObASOXjbDLjGjmqMltesCfyLwvCpLyxWZiOeCpJpdyI881XoL74FgfwFFS8KIG5s1eQAAAAASUVORK5CYII='
folder_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAC9ElEQVR42nVTXUhTURw/d5vb3ea2ltt0kuicVK6CSmllyShhy2z4YlC+ZC9GGgRiD0b5SRihRqBivuST+eBDoWiKWKJpK8RA/IDcXBqbc1P3vTv3cTq73js/oHPPueec/8fv/D8xcGTUzhJatOkwCPIABrLhHnkJrWm0Rhpz8NGD8hh9qJslMtD2WIJjpapjDHGmkMFJxhkk30ZEockdDS46ozsOAvYiUntDDm6OA9QYfDHlpvNJrOJ8OUsgxSlcDAMQUkLIJHsAgklr2PNrK/wJUV40q/lmklc15Wq5IEkoL8rgCHAmFlcEAFLK5DE2wW4EgkFz0DNnD3W35YuqsUfjDq2My+opPc2Ty3isA97FNCjNGCb6IIkFgc0fBb3LXutmIFqG3R+ythak8yu0Cj5Oq7qDUfDdEiB+bgS8MRsupeCJl1O5uJDDiMOPmn3E+B9fJ3bn49pMxUWJWiHm0E+AEaOLGDN7B5DbHZR8ZYEiUa9TCnHSKsQwbQdh15zDgBV9WHE2FaSJeGzmnpPoV/9l3eHejZYM3c2aiFGK+lY0Ajazv/56moSOhz8cAc/H1l2Y5v2Cs/mmUsRNYNI8UDtqcniCkZKvD1QkAJLRCDms/kZtpoTOuz8UATWfTS4st2tu5sk1hTpLyqNzBwYXbcTIsn0AXTpiGUEpqdSdkupvn5HF47Ri98O3k6sGLPvNj9ZClaxCfy4Vp11wBUJgwrhFTJu2vDFKniIpUZOVhIu4bJIPEejgvJUYXrJ1YumvprQpQrznYb5SLhfxwP8HFWE0rc4AeDdptG64/WWk2dKG8ZYrSln5PbVCwE1gAaqK9osdUiWFJhEKgz6D2TNttHXb625UkwCCZ6MZSKbp6snk4sKzaQK5mIcytf8i3KtkYHH5wfD8mufb702ylL0vteZ4M7GfDpHNhJRLcxUysSpVzDlxnE/y/2774IJlJzi7urljcfp7EbF99/Wt/WY6NKoGtOhJHeLkoVs2ONLOoE1/qJ3/AZHFNTXP3Z4kAAAAAElFTkSuQmCC'
LOADING_GIF_B64 = b'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'

def set_total_seconds(window):
    try:
        samplerate = int(window['sample_rate'].get())
        chunk_size = float(eval(window['chunk_size'].get()))
        total_seconds = round(chunk_size/samplerate, 1)
        window['total_seconds'].update(value=f'Seconds: {total_seconds}')
    except (SyntaxError, ValueError):
        window['total_seconds'].update(value='Seconds:  ')


def set_total_output(window):
    try:
        total = int(window['batch_size'].get()) * int(window['batch_loop'].get())
        window['batch_viewer'].update(value=f'Total output files: {total}')
    except (SyntaxError, ValueError):
        window['batch_viewer'].update(value='Total output files:  ')


def set_volume(volume):
    global current_sound_channel
    volume = volume/100
    current_sound_channel.set_volume(volume)

def clear_tree(window):
    treedata = sg.TreeData()
    window['file_tree'].update(values=treedata)

def insert_results_to_tree(batchname, results, window):
    treedata = sg.TreeData()
    for result in results:
        try:
            treedata.Insert(batchname, result, result, values=[], icon=file_icon)
        except KeyError:
            treedata.Insert('', batchname, f' {batchname}', values=[], icon=folder_icon)
            treedata.Insert(batchname, result, result, values=[], icon=file_icon)
    window['file_tree'].update(values=treedata)


def play_audio(path):
    global current_sound_channel
    if '_X' in path:
        return
    try:
        song = mixer.Sound(path)
        current_sound_channel.play(song)
    except FileNotFoundError:
        pass

def load_settings(window):
    not_load = ['log']
    if os.path.exists('saved_settings.pickle'):
        with open('saved_settings.pickle', 'rb') as f:
            saved_settings = pickle.load(f)
        for key in saved_settings:
            if key not in not_load:
                try:
                    window[key].update(value=saved_settings[key])
                except TypeError:
                    pass


def save_settings(values):
    with open('saved_settings.pickle', 'wb') as f:
        pickle.dump(values, f)


def refresh_models(window):
    models = get_models()
    if models:
        if window['model'].get():
            current_model = window['model'].get()
        else:
            current_model = models[0]
        window['model'].update(values=models, value=current_model)
        models.append('None')
        window['secondary_model'].update(values=models, value=window['secondary_model'].get())


def importmodel_cmd(v):
    if not os.path.exists('models'):
        os.mkdir('models')
    model_name = v['model_name'] if v['model_name'] != '' else os.path.basename(v['model_path']).split('.')[0]
    model_path = v['model_path']
    sample_rate = v['sample_rate']
    model_size = v['model_size']
    out_name = f'models/{model_name}_{sample_rate}_{model_size}.ckpt'
    if v['trim']:
        if not v['latent']:
            start_trim(model_path, out_name)
        else:
            prune_latent_uncond(model_path, out_name, sample_rate, model_size)


def apply_model_params(window, model_path):
    try:
        loaded_model_samplerate = model_path.split('.')[-2].split('_')[-2]
        loaded_model_size = model_path.split('.')[-2].split('_')[-1]

        if loaded_model_samplerate in ['44100', '48000', '16000', '22050', '24000', '32000', '8000']:
            window['sample_rate'].update(value=loaded_model_samplerate)
        if loaded_model_size.isdigit():
            window['chunk_size'].update(value=loaded_model_size)
    except:
        pass


def show_save_window(window, values):
    # create the layout
    modelname = ''.join(values["model"].split('_')[:-2])
    custom_batch_name = values["custom_batch_name"]
    if custom_batch_name:
        modelname = custom_batch_name
    else: 
        custom_batch_name = 'Untitled'

    popup_layout = [
        [sg.Text(f'Some processes can be lengthy, please ensure your settings are correct!', font='Arial 12', text_color='yellow')],
        [sg.Text(f'Batch Name: {custom_batch_name}')],
        [sg.Text(f'Output Path: {values["output_path"]}/{values["mode"]}/{modelname}/')],
        [sg.Button('Confirm'), sg.Button('Cancel')]
    ]
    
    # create the window
    popup_window = sg.Window('Confirm', popup_layout, icon='util/data/dtico.ico', element_justification='center')
    thread = None
    # event loop to process user inputs
    while True:
        event, v = popup_window.read()
        if event in (None, 'Cancel', sg.WIN_CLOSED):
            break
        elif event == 'Confirm':
            thread = Thread(target=generate, args=(window, values))
            thread.start()
            break
    popup_window.close()


def load_model(window):
    # create the layout
    popup_layout = [
        [sg.Text('The importer will move the selected model to the models folder and rename it for use in autocomplete.\nThis tool can also trim the model to remove data for training.')],
        [sg.Text('Select a .ckpt file'), sg.Input('path/to/model.ckpt', key='model_path'), sg.FileBrowse(file_types=(("Checkpoint files", "*.ckpt"),))],
        [sg.Text('Model Name'), sg.InputText(default_text='', key='model_name')],
        [sg.Text('Sample Rate'), sg.InputText(default_text='44100', key='sample_rate')],
        [sg.Text('Size'), sg.InputText(default_text='65536', key='model_size')],
        # checkbox for Latent?
        [sg.Checkbox('Latent?', key='latent')],
        [sg.Checkbox('Trim?', key='trim', default=True)],
        [sg.Button('Confirm'), sg.Button('Cancel')]
    ]
    
    # create the window
    popup_window = sg.Window('Select File and Input Parameters', popup_layout, icon='util/data/dtico.ico', element_justification='center')
    thread = None
    # event loop to process user inputs
    while True:
        event, v = popup_window.read()
        if event in (None, 'Cancel', sg.WIN_CLOSED):
            break
        elif event == 'Confirm':
            popup_window['Confirm'].update(disabled=True)
            thread = Thread(target=importmodel_cmd, args=(v,))
            thread.start()
            break
    if thread:
        thread.join()
        refresh_models(window)
    popup_window.close()


def get_models():
    models = glob.glob('models/*.ckpt')
    models = [os.path.basename(model) for model in models]
    if models == []:
        models = ['No models found, please load ckpt with tool.']
    return models

def str2bool(value):
    if value.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif value.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def get_args_object():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        type=str,
        default="models/dd/model.ckpt",
        help="Path to the model checkpoint file to be used (default: models/dd/model.ckpt)."
    )
    parser.add_argument(
        "--sample_rate",
        type=int,
        default=48000,
        help="The samplerate the model was trained on."
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=65536,
        help="The native chunk size of the model."
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=['Generation', 'Variation', 'Interpolation'],
        default='Generation',
        help="The mode of operation (Generation, Variation, Interpolation)."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=-1,
        help="The seed used for reproducable outputs. Leave empty for random seed."
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=1,
        help="The maximal number of samples to be produced per batch."
    )
    parser.add_argument(
        "--audio_source",
        type=str,
        default=None,
        help="Path to the audio source."
    )   
    parser.add_argument(
        "--audio_target",
        type=str,
        default=None,
        help="Path to the audio target (used for interpolations)."
    ) 
    parser.add_argument(
        "--noise_level",
        type=float,
        default=0.7,
        help="The noise level used for variations & interpolations."
    )
    parser.add_argument(
        "--interpolations_linear",
        type=int,
        default=3,
        help="The number of interpolations, even spacing."
    )
    parser.add_argument(
        "--interpolations",
        nargs='+',
        type=float,
        default=None,
        help="The interpolation positions."
    )
    parser.add_argument(
        "--resamples",
        type=int,
        default=4,
        help="Number of resampling steps in conventional samplers for inpainting."
    )
    parser.add_argument(
        "--keep_start",
        type=str2bool,
        default=True,
        help="Keep beginning of audio provided(only applies to mode Extension)."
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=50,
        help="The number of steps for the sampler."
    )
    parser.add_argument(
        "--sampler",
        type=str,
        choices=['v-ddim', 'v-iplms', 'k-heun', 'k-lms', 'k-dpmpp_2s_ancestral', 'k-dpm-2', 'k-dpm-fast', 'k-dpm-adaptive'],
        default='v-iplms',
        help="The sampler used for the diffusion model."
    )
    parser.add_argument(
        "--sampler_args",
        type=json.loads,
        default={
                'use_tqdm': False,
                'eta': 0,
                                    },
        help="Additional arguments of the DD sampler."
    )
    parser.add_argument(
        "--schedule",
        type=str,
        choices=['CrashSchedule'],
        default='CrashSchedule',
        help="The schedule used for the diffusion model."
    )
    parser.add_argument(
        "--schedule_args",
        type=json.loads,
        default={},
        help="Additional arguments of the DD schedule."
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default=None,
        help="Output path."
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default=None,
        help="Model name for path."
    )
    parser.add_argument(
        "--custom_batch_name",
        type=str,
        default=None,
        help="Custom Batch Name for batch."
    )
    args = parser.parse_args()
    return args


def extract_percentage(output):
    if output:
        last_percentage = None
        for match in re.finditer(r'\d+%', output):
            last_percentage = int(match.group(0).strip('%'))
        return last_percentage
    else:
        return None

def save_audio(audio_out, output_path: str, sample_rate, id_str:str = None, modelname='Sample', custom_batch_name=None):
    saved_paths = []
    if custom_batch_name:
        output_folder = os.path.join(output_path, custom_batch_name)
    else:
        output_folder = os.path.join(output_path, modelname)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for ix, sample in enumerate(audio_out, start=1):
        output_file = os.path.join(output_folder, f"{modelname}_{id_str}_{ix}.wav")
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
        except Exception as e:
            print(e)
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

def copysave(values):
    if values['file_tree'][0]:
        currentfile = os.path.basename(values['file_tree'][0])
        if sg.running_mac():
            filename = tk.filedialog.asksaveasfilename(initialdir=None, initialfile='None', defaultextension='wav')  # show the 'get file' dialog box
        else:
            filename = tk.filedialog.asksaveasfilename(filetypes=[("WAV files", "*.wav")], initialdir=None, initialfile=currentfile, defaultextension='wav')  # show the 'get file' dialog box
        # copy path from values['file_tree'][0] to filename
        if filename:
            shutil.copy(values['file_tree'][0], filename)


def get_args_from_window(values):
    args = get_args_object()
    args_keys = list(vars(args).keys())
    for key in args_keys:
        if key in values:
            setattr(args, key, values[key])
        if isinstance(getattr(args, key), str):
            if getattr(args, key) == '':
                setattr(args, key, None)
            elif getattr(args, key).isdigit():
                setattr(args, key, int(getattr(args, key)))
            else:
                try:
                    setattr(args, key, float(getattr(args, key)))
                except ValueError:
                    pass

    args.model = 'models/' + args.model
    model_filename = os.path.basename(args.model).split('.')[0]
    args.model_name = ''.join(model_filename.split('_')[:-2])
    args.seed = int(args.seed)
    args.chunk_size = int(eval(str(args.chunk_size)))
    if values['audio_source'] == 'None' or not os.path.exists(values['audio_source']):
        args.audio_source = None
    else: 
        args.audio_source = values['audio_source']
    return args

def open_in_finder(path):
    if sys.platform.startswith('win'):
        subprocess.Popen(['explorer', '/select,', os.path.abspath(path)])
    elif sys.platform.startswith('darwin'):
        # Use subprocess to open Finder and select the file
        subprocess.Popen(['open', '-R', path])
    elif sys.platform.startswith('linux'):
        # Use subprocess to open the file manager and select the file
        subprocess.Popen(['xdg-open', '--select', path])
    else:
        print(f"Unsupported platform: {sys.platform}")

def generate(window, values):
    window['Generate'].update(disabled=True)
    window['-LOADINGGIF-'].update(visible=True)
    args = get_args_from_window(values)

    # check paths
    if args.mode in ('Variation', 'Interpolation') and args.audio_source is None:
        print('Please select an audio source for variation mode.')
        window['Generate'].update(disabled=False)
        window['-LOADINGGIF-'].update(visible=False)
        return

    if args.mode == 'Interpolation' and args.audio_target is None:
        print('Please select an audio target for interpolation mode.')
        window['Generate'].update(disabled=False)
        window['-LOADINGGIF-'].update(visible=False)
        return

    # start batch
    clear_tree(window)
    if values['secondary_model'] != 'None':
        print('Merging models..')
        ratio_merge(f'models/{values["model"]}', f'models/{values["secondary_model"]}', alpha=float(values['merge_ratio']), out_file='models/sec_mrg_buffer.ckpt')
        args.model = 'models/sec_mrg_buffer.ckpt'
    batch_name = f"{args.model_name}_{time.strftime('%Y-%m-%d_%H-%M-%S')}" if not args.custom_batch_name else args.custom_batch_name
    
    model_args = dd.create_model_args(
        model_name=args.model_name,
        sample_size=args.chunk_size, 
        sample_rate=args.sample_rate, 
        latent_dim=0, 
        ckpt_path=args.model
        )
    sampler_args = dd.create_sampler_args(
        sampler_type=values['sampler'],
        eta=float(values['ddim_eta']), 
        beta_d=float(values['beta_d']), 
        beta_min=float(values['beta_min']), 
        rho=float(values['rho']), 
        rtol=float(values['rtol']),
        atol=float(values['atol'])
        )

    model_fn = dd.create_model(model_args)

    seed = args.seed if(args.seed!=-1) else torch.randint(0, 4294967294, [1], device='cuda').item()

    if not args.custom_batch_name:
        save_name = seed
    else:
        save_name = f"{args.custom_batch_name}_{seed}"

    for i in range(int(values['batch_loop'])):
        print(f'Processing loop {i+1}/{values["batch_loop"]}')
        window['progbar'].update_bar(0)

        if args.mode == 'Generation':
            audio = dd.generate_func(
                args.batch_size, 
                args.steps, 
                model_fn, 
                sampler_args, 
                model_args
                )

        elif args.mode == 'Variation':
            audio = dd.variation_func(
                args.batch_size, 
                args.steps, 
                model_fn, 
                sampler_args, 
                model_args, 
                args.noise_level, 
                args.audio_source
                )

        elif args.mode == 'Interpolation':
            audio = dd.interpolation_func(
                args.batch_size, 
                args.steps, model_fn, 
                sampler_args, model_args, 
                args.audio_source, 
                args.audio_target, 
                args.interpolations_linear
                )

        results = save_audio(
            audio, 
            output_path=f"{str(args.output_path)}\\{str(args.mode)}", 
            sample_rate=model_args.sample_rate, 
            id_str=save_name, 
            modelname=model_args.model_name, 
            custom_batch_name=args.custom_batch_name)
        insert_results_to_tree(batch_name, results, window)
        empty_cache()
        gc.collect()

    print('Process Finished!')
    if os.path.exists('models/sec_mrg_buffer.ckpt'):
        os.remove('models/sec_mrg_buffer.ckpt')
    window['Generate'].update(disabled=False)
    window['-LOADINGGIF-'].update(visible=False)






default_settings = vars(get_args_object())