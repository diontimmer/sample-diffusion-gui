import os
import glob
from util.cli import parse_cli_args, start_diffuse
import PySimpleGUI as sg
from threading import Thread
import re
from util.scripts.trim_model import start_trim, prune_latent_uncond
from util.scripts.merge_models_ratio import ratio_merge
import gc
import pickle
import sys
import time
import tkinter as tk
import shutil
from torch.cuda import empty_cache

# block pygame welcome message

sys.stdout = open(os.devnull, "w")
from pygame import mixer  # noqa: E402
import pygame   # noqa: E402

# reroute stdout back
sys.stdout = sys.__stdout__

pygame.init()
mixer.init()
current_sound_channel = mixer.Channel(2)

treedata = sg.TreeData()

file_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACUUlEQVR42o3SXUhTcRgG8Gc7+9ANXVpizCyQoTCiYNMEMYKCoiNGZjYQL6SPG6uLgsjM6qIsqAvBuii6qMi6qJmFHksrp/Zhajnxo5Ezp5tzbHO6Td3Wds75ZzfepEcfeO8efi+8vCKsEtUz/4GT+vh3SgqoHwyfHy/eULtST7QakPk+QN/UKZmwgoI/yKGuI1htNSTXrBtIezFLn9mVwExSEsgkPJQ8wd0n7usLVWlX1wVsfjpDn81LZJxxEiwu1SgRD8fkH3Q+clySEO5O6KGWEwRS7nvoc3Qy88YSgdPiRw6dCqmcgrnNC8+Qf2+gLsskCGysnaYrDqcwTcNhDFT2XFOXZ13ceTRd4f01D+dAwOmqTN8iCCTdmKCPG9TM2+9BjDbYtaxRZ9nREiBEKobfGppyVKSmCwKqy+N0WZmaae0JwPZyQscxuWbNcy8RK+Tw9c1M+Woy1gCujB0sOqZu+dg1B5dxTMea9pgz2mIkZJ2Dv93mizTkbhIEkPNh/5EHu1u7TR64jUN6vpvuTzjRS6LOBQuJktvR9n2P/wcKv1rzs1Wa+BiHUJRF5qnteFU/hfnm4QL+x6GWlfYsA0kln0cu3MvTukQieGcJIhEOdl8MP5sdYL+MFrC9hcJASZOHkG1JMHYFIQUBlj6PUsggMjsQ7Rws4oZLXwsC+UYPccvi4LJHIBETsLGlUSoRY4Z+c415mtVOtQxsPf1tRF6o19rGFyHlObASOXjbDLjGjmqMltesCfyLwvCpLyxWZiOeCpJpdyI881XoL74FgfwFFS8KIG5s1eQAAAAASUVORK5CYII='
folder_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAC9ElEQVR42nVTXUhTURw/d5vb3ea2ltt0kuicVK6CSmllyShhy2z4YlC+ZC9GGgRiD0b5SRihRqBivuST+eBDoWiKWKJpK8RA/IDcXBqbc1P3vTv3cTq73js/oHPPueec/8fv/D8xcGTUzhJatOkwCPIABrLhHnkJrWm0Rhpz8NGD8hh9qJslMtD2WIJjpapjDHGmkMFJxhkk30ZEockdDS46ozsOAvYiUntDDm6OA9QYfDHlpvNJrOJ8OUsgxSlcDAMQUkLIJHsAgklr2PNrK/wJUV40q/lmklc15Wq5IEkoL8rgCHAmFlcEAFLK5DE2wW4EgkFz0DNnD3W35YuqsUfjDq2My+opPc2Ty3isA97FNCjNGCb6IIkFgc0fBb3LXutmIFqG3R+ythak8yu0Cj5Oq7qDUfDdEiB+bgS8MRsupeCJl1O5uJDDiMOPmn3E+B9fJ3bn49pMxUWJWiHm0E+AEaOLGDN7B5DbHZR8ZYEiUa9TCnHSKsQwbQdh15zDgBV9WHE2FaSJeGzmnpPoV/9l3eHejZYM3c2aiFGK+lY0Ajazv/56moSOhz8cAc/H1l2Y5v2Cs/mmUsRNYNI8UDtqcniCkZKvD1QkAJLRCDms/kZtpoTOuz8UATWfTS4st2tu5sk1hTpLyqNzBwYXbcTIsn0AXTpiGUEpqdSdkupvn5HF47Ri98O3k6sGLPvNj9ZClaxCfy4Vp11wBUJgwrhFTJu2vDFKniIpUZOVhIu4bJIPEejgvJUYXrJ1YumvprQpQrznYb5SLhfxwP8HFWE0rc4AeDdptG64/WWk2dKG8ZYrSln5PbVCwE1gAaqK9osdUiWFJhEKgz6D2TNttHXb625UkwCCZ6MZSKbp6snk4sKzaQK5mIcytf8i3KtkYHH5wfD8mufb702ylL0vteZ4M7GfDpHNhJRLcxUysSpVzDlxnE/y/2774IJlJzi7urljcfp7EbF99/Wt/WY6NKoGtOhJHeLkoVs2ONLOoE1/qJ3/AZHFNTXP3Z4kAAAAAElFTkSuQmCC'

batchnames = []

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


def insert_results_to_tree(batchname, results, window):
    for result in results:
        try:
            treedata.Insert(batchname, result, result, values=[], icon=file_icon)
        except KeyError:
            treedata.Insert('', batchname, f' {batchname}', values=[], icon=folder_icon)
            treedata.Insert(batchname, result, result, values=[], icon=file_icon)
    window['file_tree'].update(values=treedata)


def play_audio(path):
    global current_sound_channel
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
    window['model'].update(values=models, value=window['model'].get())
    window['secondary_model'].update(values=models, value=window['secondary_model'].get())


def importmodel_cmd(values):
    v = values
    model_name = v['model_name'] if v['model_name'] != '' else os.path.basename(v['model_path']).split('.')[0]
    model_path = v['model_path']
    sample_rate = v['sample_rate']
    model_size = v['model_size']
    out_name = f'models/{model_name}_{sample_rate}_{model_size}.ckpt'
    if not v['latent']:
        start_trim(model_path, out_name)
    else:
        prune_latent_uncond(model_path, out_name, sample_rate, model_size)


def apply_model_params(window, model_path):
    loaded_model_samplerate = model_path.split('.')[-2].split('_')[-2]
    loaded_model_size = model_path.split('.')[-2].split('_')[-1]
    window['sample_rate'].update(value=loaded_model_samplerate)
    window['chunk_size'].update(value=loaded_model_size)


def show_save_window(window, values):
    # create the layout
    modelname = ''.join(values["model"].split('_')[:-2])
    popup_layout = [
        [sg.Text('Batch Name'), sg.InputText(default_text=values["custom_batch_name"], readonly=True, disabled_readonly_text_color='black')],
        [sg.Text('Output Path:'), sg.Input(f'{values["output_path"]}/{values["mode"]}/{modelname}/', readonly=True, disabled_readonly_text_color='black')],
        [sg.Button('Confirm'), sg.Button('Cancel')]
    ]
    
    # create the window
    popup_window = sg.Window('Confirm', popup_layout, icon='util/data/dtico.ico')
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
        [sg.Text('Select a .ckpt file'), sg.Input('path/to/model.ckpt', key='model_path'), sg.FileBrowse(file_types=(("Checkpoint files", "*.ckpt"),))],
        [sg.Text('Model Name'), sg.InputText(default_text='', key='model_name')],
        [sg.Text('Sample Rate'), sg.InputText(default_text='44100', key='sample_rate')],
        [sg.Text('Size'), sg.InputText(default_text='65536', key='model_size')],
        # checkbox for Latent?
        [sg.Checkbox('Latent?', key='latent')],
        [sg.Button('Confirm'), sg.Button('Cancel')]
    ]
    
    # create the window
    popup_window = sg.Window('Select File and Input Parameters', popup_layout, icon='util/data/dtico.ico')
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
    models.append('')
    if models == ['']:
        models = ['No models found, please load ckpt with tool.']
    return models


def get_args_object():
    args = parse_cli_args()
    settings = vars(args)
    return settings


def extract_percentage(output):
    if output:
        last_percentage = None
        for match in re.finditer(r'\d+%', output):
            last_percentage = int(match.group(0).strip('%'))
        return last_percentage
    else:
        return None



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
    args = parse_cli_args()
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
    return args


def generate(window, values):
    global batchnames
    window['Generate'].update(disabled=True)
    args = get_args_from_window(values)
    if values['secondary_model'] != '':
        print('Merging models..')
        ratio_merge(f'models/{values["model"]}', f'models/{values["secondary_model"]}', alpha=float(values['merge_ratio']), out_file='models/sec_mrg_buffer.ckpt')
        args.model = 'models/sec_mrg_buffer.ckpt'
    batch_name = f"{args.model_name}_{time.strftime('%Y-%m-%d_%H-%M-%S')}" if not args.custom_batch_name else args.custom_batch_name
    if batch_name in batchnames:
        if batch_name[-1].isdigit():
            batch_name = batch_name.replace(batch_name[-1], int(batch_name[-1]) + 1)
        else:
            batch_name = batch_name + '_1'
    batchnames.append(batch_name)
    for i in range(int(values['batch_loop'])):
        print(f'Processing loop {i+1}/{values["batch_loop"]}')
        results = start_diffuse(args)
        #check if batch name already in tree
        insert_results_to_tree(batch_name, results, window)
        empty_cache()
        gc.collect()

    print('Process Finished!')
    if os.path.exists('models/sec_mrg_buffer.ckpt'):
        os.remove('models/sec_mrg_buffer.ckpt')
    window['progbar'].update(current_count=100, max=100)
    window['Generate'].update(disabled=False)


default_settings = get_args_object()