import os
import glob
import sys
import subprocess
from util.cli import parse_cli_args, start_diffuse
import PySimpleGUI as sg
from threading import Thread
import re
from util.trim_model import start_trim
import pickle


def load_settings(window):
    if os.path.exists('saved_settings.pickle'):
        with open('saved_settings.pickle', 'rb') as f:
            saved_settings = pickle.load(f)
        for key in saved_settings:
            try:
                window[key].update(value=saved_settings[key])
            except TypeError:
                pass


def save_settings(values):
    with open('saved_settings.pickle', 'wb') as f:
        pickle.dump(values, f)


def refresh_models(window):
    models = get_models()
    window['model'].update(values=models, value=models[0])


def importmodel_cmd(values):
    v = values
    model_name = v['model_name'] if v['model_name'] != '' else os.path.basename(v['model_path']).split('.')[0]
    model_path = v['model_path']
    sample_rate = v['sample_rate']
    model_size = v['model_size']
    start_trim(model_path, f'models/{model_name}_{sample_rate}_{model_size}.ckpt')


def apply_model_params(window, model_path):
    loaded_model_samplerate = model_path.split('.')[-2].split('_')[-2]
    loaded_model_size = model_path.split('.')[-2].split('_')[-1]
    window['sample_rate'].update(value=loaded_model_samplerate)
    window['chunk_size'].update(value=loaded_model_size)


def load_model(window):
    # create the layout
    popup_layout = [
        [sg.Text('Select a .ckpt file'), sg.Input('path/to/model.ckpt', key='model_path'), sg.FileBrowse(file_types=(("Checkpoint files", "*.ckpt"),))],
        [sg.Text('Model Name'), sg.InputText(default_text='', key='model_name')],
        [sg.Text('Sample Rate'), sg.InputText(default_text='44100', key='sample_rate')],
        [sg.Text('Size'), sg.InputText(default_text='65536', key='model_size')],
        [sg.Button('Confirm'), sg.Button('Cancel')]
    ]
    
    # create the window
    popup_window = sg.Window('Select File and Input Parameters', popup_layout, icon='util/data/dtico.ico')
    
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
    thread.join()
    popup_window.close()
    refresh_models(window)


def get_models():
    models = glob.glob('models/*.ckpt')
    models = [os.path.basename(model) for model in models]
    if models == []:
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


def set_total_output(window, values):
    try:
        total = int(values['batch_size']) * int(values['batch_loop'])
        window['batch_viewer'].update(value=f'Total output files: {total}')
    except:
        window['batch_viewer'].update(value='x')


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
    return args


def generate(window, values):
    window['Generate'].update(disabled=True)
    args = get_args_from_window(values)
    for i in range(int(values['batch_loop'])):
        print(f'Processing loop {i+1}/{values["batch_loop"]}')
        start_diffuse(args)
    print('Process Finished!')
    window['Generate'].update(disabled=False)


default_settings = get_args_object()