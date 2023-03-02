import os
import glob
import PySimpleGUI as sg
import PySimpleGUIQt as sgqt
from threading import Thread
from util.scripts.note_detect import detect_notes
from util.scripts.generate_wave import create_signal
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
import library.dance_diffusion as dd
from library.dance_diffusion import Object
from pydub import AudioSegment, effects
import subprocess
from importlib import import_module
import PySide2.QtCore as QtCore
import yaml
from util.constants import *

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

def load_theme(qt=False):
    interface = sg if qt == False else sgqt
    with open('config/guiconfig.yaml', 'r') as f:
        config = yaml.safe_load(f)
        if config['theme'] == 'Custom':
            interface.LOOK_AND_FEEL_TABLE['Custom'] = {
                'BACKGROUND': get_config_value('BACKGROUND'),
                'TEXT': get_config_value('TEXT'),
                'INPUT': get_config_value('INPUT'),
                'TEXT_INPUT': get_config_value('TEXT_INPUT'),
                'SCROLL': get_config_value('SCROLL'),
                'BUTTON': (get_config_value('BUTTON')[0], get_config_value('BUTTON')[1]),
                'PROGRESS': (get_config_value('PROGRESS')[0], get_config_value('PROGRESS')[1]),
                'BORDER': get_config_value('BORDER'), 
                'SLIDER_DEPTH': get_config_value('SLIDER_DEPTH'), 
                'PROGRESS_DEPTH': get_config_value('PROGRESS_DEPTH'), 
                }
            return 'Custom'
        else:
            return config['theme']





def get_config_value(key):
    with open('config/guiconfig.yaml', 'r') as f:
        config = yaml.safe_load(f)
        return config[key]

def save_config_value(key, value):
    with open('config/guiconfig.yaml', 'r') as f:
        config = yaml.safe_load(f)
        config[key] = value
    with open('config/guiconfig.yaml', 'w') as f:
        yaml.dump(config, f)



def show_drop_window(window, target):
    sgqt.theme(load_theme(qt=True))
    dropped = None
    class Image(sgqt.Image):
    
        def dragEnterEvent(self, e):
            e.accept()
    
        def dragMoveEvent(self, e):
            e.accept()
    
        def dropEvent(self, e):
            items = [str(v) for v in e.mimeData().text().strip().split('\n')]
            dropped = items[0].replace('file:///', '')
            if dropped.endswith(('.wav', '.mp3', '.ogg', '.flac')):
                window[target].update(value=dropped)
                drop_window.close()
    
        def enable_drop(self):
            # Called after window finalized
            self.Widget.setAcceptDrops(True)
            self.Widget.dragEnterEvent = self.dragEnterEvent
            self.Widget.dragMoveEvent = self.dragMoveEvent
            self.Widget.dropEvent = self.dropEvent
    
    layout = [[Image(filename='util/data/drop_arrow.png', size=(128, 128), enable_events=True, key='IMAGE')], [sgqt.Text('Please drop your audio files!')]]
    
    drop_window = sgqt.Window("Drop Window", layout, finalize=True, icon='util/data/dtico2.ico', resizable=False)
    drop_window['IMAGE'].enable_drop()
    drop_window.QT_QMainWindow.setWindowFlags(drop_window.QT_QMainWindow.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
    drop_window.QT_QMainWindow.show()

    while True:
        event, values = drop_window.read()
        if event == sgqt.WINDOW_CLOSED:
            break
    
    drop_window.close()
    return dropped if dropped is not None else None

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
    global treedata
    treedata = sg.TreeData()
    window['file_tree'].update(values=treedata)

def insert_results_to_tree(batchname, results, window):
    global treedata
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
    not_load = ['log', 'tab_group']
    if os.path.exists('saved.sdsettings'):
        with open('saved.sdsettings', 'rb') as f:
            saved_settings = pickle.load(f)
        update_sigma(window, saved_settings['alt_sigma'])
        update_input_path(window, saved_settings['gen_wave'] != 'None')
        for key in saved_settings:
            if key not in not_load:
                try:
                    if not isinstance(window[key], sg.Button):
                        window[key].update(value=saved_settings[key])
                except (TypeError, KeyError) as e:
                    print(e)
                    pass

def load_extensions(window):
    exts = []
    for folder in os.listdir('extensions'):
        for file in os.listdir('extensions\\' + folder):
            if file.endswith('.py') and file.startswith('ext_'):
                extfile = f'extensions.{folder}.{file.split(".")[0]}'
                ext = import_module(extfile, package=None)
                exts.append(ext)
                ext_info = ext.on_activate(window)
                ext_tab = sg.Tab(ext_info['name'], ext_info['layout'], key=ext_info['name'])
                window['tab_group'].add_tab(ext_tab)
    return exts



def save_settings(values):
    with open('saved.sdsettings', 'wb') as f:
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

def update_sigma(window, alt_sigma_on):
    # get current theme text color
    text_color = sg.theme_text_color()
    window['sigma_min'].update(disabled=alt_sigma_on)
    window['sigma_max'].update(disabled=alt_sigma_on)
    window['smintext'].update(text_color=text_color if not alt_sigma_on else 'grey')
    window['smaxtext'].update(text_color=text_color if not alt_sigma_on else 'grey')

def update_input_path(window, gen_wave_on):
    text_color = sg.theme_text_color()
    window['audio_source'].update(disabled=gen_wave_on)
    window['audio_source_folder'].update(disabled=gen_wave_on)
    window['ipathtext'].update(text_color=text_color if not gen_wave_on else 'grey')
    window['fpathtext'].update(text_color=text_color if not gen_wave_on else 'grey')

def create_warning(text, color='red'):
    return [[sg.Text(text, text_color=color)]]

def show_save_window(window, values):
    # create the layout
    modelname = ''.join(values["model"].split('_')[:-2])
    custom_batch_name = values["custom_batch_name"]
    if custom_batch_name:
        modelname = custom_batch_name
    else: 
        custom_batch_name = 'Untitled'

    # WARNINGS
    disable_confirm = False
    warnings = [[]]
    if values['mode'] in ('Variation', 'Interpolation') and values['alt_sigma']:
        warnings.append(create_warning('WARNING: Using alternative sigma func for variation/interp mode will not work!'))
    if values['mode'] == 'Interpolation' and values['sampler'] != 'v-iplms':
        warnings.append(create_warning('WARNING: Interpolations currently only work properly with the v-iplms sampler!'))
    if values['sample_rate'] not in ['44100', '48000', '16000', '22050', '24000', '32000', '8000']:
        warnings.append(create_warning(f'WARNING: Unusual sample rate detected: {values["sample_rate"]}!'))
    if values['gen_wave'] != 'None' and values['mode'] in ('Variation', 'Interpolation'):
        warnings.append(create_warning(f'Wave gen variation enabled: {values["gen_wave"]}', color='orange'))
    if values['gen_wave'] == 'None' and values['mode'] == 'Variation' and values['audio_source_folder'] != '':
        warnings.append(create_warning(f'Batch folder variation enabled: {values["audio_source_folder"]}', color='orange'))
    if values['secondary_model'] != 'None' :
        warnings.append(create_warning(f'Secondary model merge enabled: {values["secondary_model"]} * {values["merge_ratio"]}', color='orange'))
    try:
        total = int(window['batch_size'].get()) * int(window['batch_loop'].get())
    except ValueError:
        total = 0
        warnings.append(create_warning('ERROR: Batches should be integers!'))
        disable_confirm = True

    stree_data = sg.TreeData()
    def mk_tree_setting(treedata, key, value): return treedata.insert('', key=key, text=key, values=[value])

    mk_tree_setting(stree_data, 'Batch Name', custom_batch_name)
    mk_tree_setting(stree_data, 'Model Name', values["model"])
    mk_tree_setting(stree_data, 'Mode', values["mode"])
    mk_tree_setting(stree_data, 'Total Output', total)
    mk_tree_setting(stree_data, 'Sampler', values["sampler"])
    mk_tree_setting(stree_data, 'Steps', values["steps"])
    mk_tree_setting(stree_data, 'Output Path', f'{values["output_path"]}/{values["mode"]}/{modelname}/')
    mk_tree_setting(stree_data, 'Sample Rate', values["sample_rate"])
    mk_tree_setting(stree_data, 'Chunk Size', values["chunk_size"])

    #stree_data.insert('', key='testkey', text='test', values=['test', 'test'])

    popup_layout = [
        [sg.Text(f'Some processes can be lengthy, please ensure your settings are correct!', font='Arial 12', text_color='yellow')],
        [sg.Tree(stree_data, headings=[''], key='-stree-', show_expanded=True, enable_events=True, expand_y=True, expand_x=True)],
        # [sg.Text(f'Batch Name: {custom_batch_name}')],
        # [sg.Text(f'Model Name: {values["model"]}')],
        # [sg.Text(f'Mode: {values["mode"]}')],
        # [sg.Text(f'Total Output: {total}')],
        # [sg.Text(f'Sampler: {values["sampler"]}')],
        # [sg.Text(f'Output Path: {values["output_path"]}/{values["mode"]}/{modelname}/')],
        [sg.Button('Confirm'), sg.Button('Cancel')]
    ]

    popup_layout = popup_layout + warnings
    
    # create the window
    popup_window = sg.Window('Confirm', popup_layout, icon='util/data/dtico.ico', element_justification='center', finalize=True)

    if disable_confirm:
        popup_window['Confirm'].update(disabled=True)
        

    thread = None
    # event loop to process user inputs
    while True:
        event, v = popup_window.read()
        if event in (None, 'Cancel', sg.WIN_CLOSED):
            break
        elif event == 'Confirm':
            thread = Thread(target=generate, args=(window, values), daemon=True)
            thread.start()
            break
    popup_window.close()

def get_models():
    models = glob.glob('models/*.ckpt')
    models = [os.path.basename(model) for model in models]
    if models == []:
        models = ['No models found, please load ckpt with tool.']
    return models

def out_file_exists(output_folder, modelname, id_str, ix):
    for f in os.listdir(output_folder):
        if f.startswith(f"{modelname}_{id_str}_{ix}"):
            return True
    return False

def get_args_object():
    args_object = Object()
    args_object.model = 'models/dd/model.ckpt'
    args_object.sample_rate = 48000
    args_object.chunk_size = 65536
    args_object.mode = 'Generation'
    args_object.batch_size = 1
    args_object.audio_source = None
    args_object.audio_source_folder = None
    args_object.audio_target = None
    args_object.noise_level = 0.7
    args_object.interpolations_linear = 3
    args_object.steps = 50
    args_object.sampler = 'v-iplms'
    args_object.output_path = None
    args_object.model_name = None
    args_object.custom_batch_name = None
    args_object.gen_wave = 'None'
    args_object.gen_keys = 'C4, C5, C6'
    args_object.gen_amp = 100
    return args_object

def save_audio(audio_out, output_folder: str, sample_rate, id_str:str = None, modelname='Sample', custom_batch_name=None):
    saved_paths = []
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for ix, sample in enumerate(audio_out, start=1):
        output_file = os.path.join(output_folder, f"{modelname}_{id_str}_{ix}.wav")
        while out_file_exists(output_folder, modelname, id_str, ix):
            ix += 1
            output_file = os.path.join(output_folder, f"{modelname}_{id_str}_{ix}.wav")

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
    args.chunk_size = int(eval(str(args.chunk_size)))
    if values['audio_source'] == '' or not os.path.exists(values['audio_source']):
        args.audio_source = None
    else: 
        args.audio_source = values['audio_source']
    return args

def preview_keys(window, values):
    if values['gen_wave'] != 'None':
        try:
            window['-LOADINGGIF-'].update(visible=True)
            window['Preview Keys'].update(disabled=True)
            preview = create_signal(values['gen_keys'].split(', '), int(values['sample_rate']), int(eval(str(values['chunk_size']))), float(values['gen_amp']), values['gen_wave'], 'tmp')
            play_audio(preview)
            window['-LOADINGGIF-'].update(visible=False)
            window['Preview Keys'].update(disabled=False)
            os.remove(preview)
        except ValueError:
            pass

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
    varlist = [args.audio_source]

    # check paths
    if args.mode in ('Variation', 'Interpolation'):
        if args.audio_source is None and args.gen_wave == 'None' and args.audio_source_folder is None:
            print('Please select an audio source or wave gen for variation mode.')
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
        alt_sigma=bool(values['alt_sigma']), 
        sigma_min=float(values['sigma_min']), 
        sigma_max=float(values['sigma_max']), 
        rho=float(values['rho']), 
        rtol=float(values['rtol']),
        atol=float(values['atol'])
        )

    model_fn = dd.create_model(model_args)
    if args.gen_wave != 'None':
        varlist = [create_signal(args.gen_keys.split(', '), model_args.sample_rate, int(model_args.sample_size) * 2, args.gen_amp, args.gen_wave, 'tmp')]

    elif args.audio_source_folder is not None:
        varlist = [os.path.join(args.audio_source_folder, audio) for audio in os.listdir(args.audio_source_folder) if audio.endswith('.wav')]

    seed = torch.randint(0, 4294967294, [1], device='cuda').item()

    if not args.custom_batch_name:
        output_folder = f"{str(args.output_path)}\\{str(args.mode)}\\{str(args.model_name)}"
    else:
        output_folder = f"{str(args.output_path)}\\{str(args.mode)}\\{str(args.custom_batch_name)}"





    for i in range(int(values['batch_loop'])):
        print(f'Processing loop {i+1}/{values["batch_loop"]}')

        if args.mode == 'Generation':
            window['progbar'].update_bar(0)
            data = dd.generate_func(
                args.batch_size, 
                args.steps, 
                model_fn, 
                sampler_args, 
                model_args,
                )
            results = save_audio(
                data, 
                output_folder=output_folder, 
                sample_rate=model_args.sample_rate, 
                id_str=seed, 
                modelname=model_args.model_name, 
                custom_batch_name=args.custom_batch_name)
            insert_results_to_tree(batch_name, results, window)



        elif args.mode == 'Variation':
            results = []
            for var_job in varlist:
                window['progbar'].update_bar(0)
                print('Processing variation job on: ' + var_job)
                data = dd.variation_func(
                    args.batch_size, 
                    args.steps, 
                    model_fn, 
                    sampler_args, 
                    model_args, 
                    args.noise_level, 
                    var_job,
                    )
                save_name = os.path.splitext(os.path.basename(var_job))[0]
                result = save_audio(
                    data, 
                    output_folder=output_folder, 
                    sample_rate=model_args.sample_rate, 
                    id_str=save_name, 
                    modelname=model_args.model_name, 
                    custom_batch_name=args.custom_batch_name)
                results += result
                insert_results_to_tree(batch_name, result, window)



        elif args.mode == 'Interpolation':
            window['progbar'].update_bar(0)
            data = dd.interpolation_func(
                args.batch_size, 
                args.steps, 
                model_fn, 
                sampler_args, 
                model_args, 
                args.audio_source, 
                args.audio_target, 
                args.interpolations_linear,
                args.noise_level,
                )
            results = save_audio(
                data, 
                output_folder=output_folder, 
                sample_rate=model_args.sample_rate, 
                id_str=seed, 
                modelname=model_args.model_name, 
                custom_batch_name=args.custom_batch_name)
            insert_results_to_tree(batch_name, results, window)
        empty_cache()
        gc.collect()

    print('Process Finished!')
    if os.path.exists('models/sec_mrg_buffer.ckpt'):
        os.remove('models/sec_mrg_buffer.ckpt')
    if args.gen_wave != 'None':
        os.remove(varlist[0])
    window['Generate'].update(disabled=False)
    window['-LOADINGGIF-'].update(visible=False)






default_settings = vars(get_args_object())