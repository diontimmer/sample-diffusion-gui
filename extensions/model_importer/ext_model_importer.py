import os
import sys
script_folder = os.path.dirname(os.path.realpath(__file__))
sys.path.append(script_folder)
import PySimpleGUI as sg
from trim_model import start_trim
from utility.gui import refresh_models

# get script folder

options_col = sg.Column([
    [sg.Text('The importer will move the selected model to the models folder and rename it for use in autocomplete.\nThis tool can also trim the model to remove data for training.')],
    [sg.Text('Select a .ckpt file'), sg.Input('path/to/model.ckpt', key='ext_model_importer_MODEL_PATH'), sg.FileBrowse(file_types=(("Checkpoint files", "*.ckpt"),))],
    [sg.Text('Model Name'), sg.InputText(default_text='', key='ext_model_importer_MODEL_NAME')],
    [sg.Text('Sample Rate'), sg.InputText(default_text='44100', key='ext_model_importer_SAMPLE_RATE')],
    [sg.Text('Size'), sg.InputText(default_text='65536', key='ext_model_importer_MODEL_SIZE')],
    # checkbox for Latent?
    #[sg.Checkbox('Latent?', key='ext_model_importer_LATENT')],
    [sg.Checkbox('Import & Trim?', key='ext_model_importer_TRIM', default=True)],
], scrollable=True, vertical_scroll_only=True, size=(600, 200), expand_x=True, expand_y=True)


def importmodel_cmd(v):
    global window
    if not os.path.exists('models'):
        os.mkdir('models')
    model_name = v['ext_model_importer_MODEL_NAME'] if v['ext_model_importer_MODEL_NAME'] != '' else os.path.basename(v['ext_model_importer_MODEL_PATH']).split('.')[0]
    model_path = v['ext_model_importer_MODEL_PATH']
    sample_rate = v['ext_model_importer_SAMPLE_RATE']
    model_size = v['ext_model_importer_MODEL_SIZE']
    out_name = f'models/{model_name}_{sample_rate}_{model_size}.ckpt'
    window['ext_model_importer_IMPORT'].update(disabled=True)
    window['ext_model_importer_TRIMONLY'].update(disabled=True)
    if v['ext_model_importer_TRIM']:
        #prune_latent_uncond(model_path, out_name, sample_rate, model_size)
        #if not v['ext_model_importer_LATENT']:
        window.start_thread(lambda: start_trim(model_path, out_name), 'ext_model_importer_FINISH_IMPORT')
        #else:
        #    prune_latent_uncond(model_path, out_name, sample_rate, model_size)

# ****************************************************************************
# *                                 EXTENSION                                *
# ****************************************************************************


# These functions are mandatory for the extension to work. Replace this with your own magic.

def create_tab_info():
    layout = [
        [sg.Frame('Import Settings', [[options_col]], expand_x=True, expand_y=True)],
        [sg.Button('Import', key='ext_model_importer_IMPORT'), sg.Button('Trim Only', key='ext_model_importer_TRIMONLY')]
    ]
    ext_info = {
                'name': 'Importer', 
                'version': '1.0', 
                'author': 'Dion Timmer', 
                'description': 'DD Import Extension',
                'layout': layout
                }
    return ext_info


# Called when the extension is activated.
def on_activate(loaded_window):
    global window
    global ext_info
    window = loaded_window
    ext_info=create_tab_info()
    print(f'Loaded Extension: {ext_info["name"]}!')
    return ext_info


# Called from the main window loop, use this to catch values and do stuff.
def handle_event_values(event, values):
    global window
    if event == 'ext_model_importer_IMPORT':
        importmodel_cmd(values)
    if event == 'ext_model_importer_TRIMONLY':
        original_dir = os.path.dirname(values['ext_model_importer_MODEL_PATH'])
        out_name = f'{original_dir}/{values["ext_model_importer_MODEL_NAME"]}_trimmed.ckpt'
        window['ext_model_importer_IMPORT'].update(disabled=True)
        window['ext_model_importer_TRIMONLY'].update(disabled=True)
        window.start_thread(lambda: start_trim(values['ext_model_importer_MODEL_PATH'], out_name), 'ext_model_importer_FINISH_TRIM')
    if event in ('ext_model_importer_FINISH_IMPORT', 'ext_model_importer_FINISH_TRIM'):
        window['ext_model_importer_IMPORT'].update(disabled=False)
        window['ext_model_importer_TRIMONLY'].update(disabled=False)
        refresh_models(window)
