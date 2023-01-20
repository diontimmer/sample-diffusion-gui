import os
import glob
import sys
import subprocess
from cli import parse_cli_args
import PySimpleGUI as sg
from threading import Thread
import re


def refresh_models(window):
    models = get_models()
    window['model'].update(values=models, value=models[0])


def importmodel_cmd(values):
    v = values
    model_name = v['model_name'] if v['model_name'] != '' else os.path.basename(v['model_path']).split('.')[0]
    model_path = v['model_path']
    sample_rate = v['sample_rate']
    model_size = v['model_size']
    cmd = [sys.executable, 'scripts/trim_model.py', f'{model_path}', f'models/{model_name}_{sample_rate}_{model_size}.ckpt']
    p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, universal_newlines=True)
    while True:
        line = p.stdout.readline()
        if not line:
            break
        print(line, end="")
    p.wait()


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
    popup_window = sg.Window('Select File and Input Parameters', popup_layout)
    
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


def generate(window, values):
    window['Generate'].update(disabled=True)
    args = parse_cli_args()
    args_keys = list(vars(args).keys())
    for key in args_keys:
        if key in values:
            setattr(args, key, values[key])
    arg_items = vars(args)
    # remove entry from arg items if the value is the same as in default_settings_items
    stripped_args = {}
    for key, value in arg_items.items():
        if value != str(default_settings.get(key)) and value != default_settings.get(key) and value != '':
            stripped_args[key] = value
    if 'model' not in stripped_args.keys():
        stripped_args['model'] = values['model']
    stripped_args['model'] = 'models/' + stripped_args['model']
    model_filename = os.path.basename(stripped_args['model']).split('.')[0]
    stripped_args['model_name'] = ''.join(model_filename.split('_')[:-2])
    cmd_args = ' '.join([f'--{key} {value}' for key, value in stripped_args.items()])
    cmd = f"{sys.executable} cli.py {cmd_args}"
    print(cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
    while True:
        line = p.stdout.readline()
        if not line:
            break
        print(line, end="")
    p.wait()
    print('Process Finished!')
    window['Generate'].update(disabled=False)


default_settings = get_args_object()