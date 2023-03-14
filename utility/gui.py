import os
import glob
import PySimpleGUI as sg
import PySimpleGUIQt as sgqt
from threading import Thread
from utility.scripts.note_detect import detect_notes
from utility.scripts.generate_wave import create_signal
from utility.scripts.merge_models_ratio import ratio_merge
import torch
import torchaudio
import gc
import pickle
import sys
import time
import tkinter as tk
import shutil
from types import SimpleNamespace
from pydub import AudioSegment, effects
import subprocess
from importlib import import_module
import PySide2.QtCore as QtCore
import yaml
from utility.constants import *

sys.path.append('sample_diffusion') 

from sample_diffusion.util.util import load_audio, cropper
from sample_diffusion.util.platform import get_torch_device_type
from sample_diffusion.dance_diffusion.api import RequestHandler, Request, Response, RequestType, SamplerType, SchedulerType, ModelType

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
    
    layout = [[Image(filename='utility/data/drop_arrow.png', size=(128, 128), enable_events=True, key='IMAGE')], [sgqt.Text('Please drop your audio files!')]]
    
    drop_window = sgqt.Window("Drop Window", layout, finalize=True, icon='utility/data/dtico2.ico', resizable=False)
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
        #update_sigma(window, saved_settings['alt_sigma'])
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
    #if values['mode'] in ('Variation', 'Interpolation') and values['alt_sigma']:
    #    warnings.append(create_warning('WARNING: Using alternative sigma func for variation/interp mode will not work!'))

    if values['mode'] == 'Interpolation' and values['sampler'] == 'DDIM':
        warnings.append(create_warning('ERROR: Interpolations currently do not work with the ddim sampler!'))
        disable_confirm = True

    if values['mode'] == 'Inpainting':
        warnings.append(create_warning('ERROR: Inpainting is not yet properly implemented!'))
        disable_confirm = True

    if values['mode'] in ('Extension', 'Inpainting') and values['sampler'] != 'DDPM':
        warnings.append(create_warning('ERROR: Extension/Inpainting only currently works with the DDPM sampler!'))
        disable_confirm = True

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
    popup_window = sg.Window('Confirm', popup_layout, icon='utility/data/dtico.ico', element_justification='center', finalize=True)

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
    args_object = SimpleNamespace()
    args_object.model = 'models/dd/model.ckpt'
    args_object.sample_rate = 48000
    args_object.chunk_size = 65536
    args_object.mode = 'Generation'
    args_object.batch_size = 1
    args_object.audio_source = ''
    args_object.audio_source_folder = ''
    args_object.audio_target = ''
    args_object.noise_level = 0.7
    args_object.interpolations_linear = 3
    args_object.steps = 50
    args_object.sampler = 'IPLMS'
    args_object.output_path = None
    args_object.model_name = None
    args_object.tame = True
    args_object.custom_batch_name = None
    args_object.use_autocrop = True
    args_object.use_autocast = True
    args_object.gen_wave = 'None'
    args_object.gen_keys = 'C4, C5, C6'
    args_object.keep_start = True
    args_object.seed = -1
    args_object.resamples = 5
    args_object.gen_amp = 100
    args_object.schedule = 'CrashSchedule'
    args_object.sampler_args = {'use_tqdm': True}
    args_object.schedule_args = {}
    args_object.mask = ''
    args_object.device_accelerator = 'cuda'
    args_object.device_offload = 'cuda'
    args_object.ddim_eta = 0
    return args_object

def save_audio(audio_out, output_folder: str, sample_rate, id_str:str = None, modelname='Sample'):
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

    args.model = 'models/' + args.model
    model_filename = os.path.basename(args.model).split('.')[0]
    args.model_name = ''.join(model_filename.split('_')[:-2])
    args.chunk_size = int(eval(str(args.chunk_size)))
    args.audio_source = '' if args.audio_source == None else args.audio_source
    if args.audio_source != '':
        args.audio_source = args.audio_source if os.path.exists(args.audio_source) else ''
    args.sampler_args = {'use_tqdm': True, 'eta': args.ddim_eta}

    # check paths
    if args.mode in ('Variation', 'Interpolation'):
        if args.audio_source is None and args.gen_wave == 'None' and args.audio_source_folder is None:
            print('Please select an audio source or wave gen for variation mode.')
            return

    if args.mode == 'Interpolation' and args.audio_target is None:
        print('Please select an audio target for interpolation mode.')
        window['Generate'].update(disabled=False)
        window['-LOADINGGIF-'].update(visible=False)
        return

    device_type_accelerator = args.device_accelerator if(args.device_accelerator != None) else get_torch_device_type()
    device_accelerator = torch.device(device_type_accelerator)
    device_offload = torch.device(args.device_offload)
    autocrop = cropper(args.chunk_size, True) if(args.use_autocrop==True) else lambda audio: audio
    request_handler = RequestHandler(device_accelerator, device_offload, optimize_memory_use=False, use_autocast=args.use_autocast)
    request_type = RequestType[args.mode]
    model_type = ModelType.DD
    sampler_type = SamplerType[args.sampler]
    scheduler_type = SchedulerType[args.schedule]
    batch_name = f"{args.model_name}_{time.strftime('%Y-%m-%d_%H-%M-%S')}" if not args.custom_batch_name else args.custom_batch_name


    clear_tree(window)

    if values['secondary_model'] != 'None':
        print('Merging models..')
        ratio_merge(f'models/{values["model"]}', f'models/{values["secondary_model"]}', alpha=float(values['merge_ratio']), out_file='models/sec_mrg_buffer.ckpt')
        args.model = 'models/sec_mrg_buffer.ckpt'
    

    varlist = [args.audio_source]
    if args.gen_wave != 'None':
        varlist = [create_signal(args.gen_keys.split(', '), args.sample_rate, int(args.chunk_size) * 2, args.gen_amp, args.gen_wave, 'tmp')]
    
    elif args.audio_source_folder is not None and not '' and args.mode =='Variation':
        varlist = [os.path.join(args.audio_source_folder, audio) for audio in os.listdir(args.audio_source_folder) if audio.endswith('.wav')]

    if not args.custom_batch_name:
        output_folder = f"{str(args.output_path)}\\{str(args.mode)}\\{str(args.model_name)}"
    else:
        output_folder = f"{str(args.output_path)}\\{str(args.mode)}\\{str(args.custom_batch_name)}"
        
    for i in range(int(values['batch_loop'])):
        
        gc.collect()
        torch.cuda.empty_cache()
        seed = args.seed if(args.seed!=-1) else torch.randint(0, 4294967294, [1], device=device_type_accelerator).item()
        id_str = seed
        print(f'Processing loop {i+1}/{values["batch_loop"]}, Using accelerator: {device_type_accelerator}, Seed: {seed}.')
        for source in varlist:
            if args.mode == 'Variation':
                save_name = os.path.splitext(os.path.basename(source))[0]
                id_str = f'{save_name}_{seed}'


            source = None if source == '' else source
            request = Request(
                request_type=request_type,
                model_path=args.model,
                model_type=model_type,
                model_chunk_size=args.chunk_size,
                model_sample_rate=args.sample_rate,
                
                seed=seed,
                batch_size=args.batch_size,
                
                audio_source=autocrop(load_audio(device_accelerator,source, args.sample_rate)) if(source != None) else None,
                audio_target=autocrop(load_audio(device_accelerator,args.audio_target, args.sample_rate)) if(args.audio_target != None) else None,
                mask=torch.load(args.mask) if(args.mask != None) else None,
                
                noise_level=args.noise_level,
                interpolation_positions=args.interpolations if(args.interpolations_linear == None) else torch.linspace(0, 1, args.interpolations_linear, device=device_accelerator),
                resamples=args.resamples,
                keep_start=args.keep_start,
                        
                steps=args.steps,
                
                sampler_type=sampler_type,
                sampler_args=args.sampler_args,
                
                scheduler_type=scheduler_type,
                scheduler_args=args.schedule_args
            )
            
            response = request_handler.process_request(request)#, lambda **kwargs: print(f"{kwargs['step'] / kwargs['x']}"))
            results = save_audio(
                (0.5 * response.result).clamp(-1,1) if(args.tame == True) else response.result, 
                output_folder=output_folder, 
                sample_rate=args.sample_rate, 
                id_str=id_str,
                modelname=args.model_name)
    
            insert_results_to_tree(batch_name, results, window)
        

    print('Process Finished!')
    if os.path.exists('models/sec_mrg_buffer.ckpt'):
        os.remove('models/sec_mrg_buffer.ckpt')
    if args.gen_wave != 'None':
        os.remove(varlist[0])
    window['Generate'].update(disabled=False)
    window['-LOADINGGIF-'].update(visible=False)    



default_settings = vars(get_args_object())