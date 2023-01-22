from util.gui import *
from threading import Thread

sg.theme('DarkGrey7')   # Add a touch of color

loaded_models = get_models()


settings_header = [
                    [sg.T('Model File', tooltip='Path to the model checkpoint file to be used.'), sg.Combo(loaded_models, key='model', default_value=loaded_models[0], enable_events=True,)],
                    [sg.T('Mode', tooltip='The mode of operation'), sg.Combo(['Generation', 'Interpolation', 'Variation'], default_value=default_settings['mode'], key='mode')],
                    [sg.T('Output Path', tooltip='Path for output renders.'), sg.InputText('output', key='output_path'), sg.FolderBrowse()],
                    [sg.T('Batch Loop', tooltip='The number of times the internal batch size will loop.'), sg.InputText('1', key='batch_loop', enable_events=True)],
                    [sg.T('Internal Batch Size', tooltip='The maximal number of samples to be produced per batch.'), sg.InputText(default_settings['batch_size'], key='batch_size', enable_events=True)],
                    [sg.T('Total output files: 1', tooltip='Batch Loop * Internal Batch Size', key='batch_viewer')]]
settings_row_1 = [
                    [sg.Checkbox('Use Autocast', default=default_settings['use_autocast'], key='use_autocast')],
                    [sg.Checkbox('Use Autocrop', default=default_settings['use_autocrop'], key='use_autocrop', tooltip='Use autocrop (automatically crops audio provided to chunk size).')],
                    [sg.T('Device Offload', tooltip='Device to store models when not in use.'), sg.Combo(['cpu', 'gpu'], default_value=default_settings['device_offload'], key='device_offload')],
                    [sg.T('Sample Rate', tooltip='  The samplerate the model was trained on.'), sg.InputText(default_settings['sample_rate'], key='sample_rate')],
                    [sg.T('Chunk Size', tooltip='The native chunk size of the model.'), sg.InputText(default_settings['chunk_size'], key='chunk_size')],
                    [sg.T('Seed', tooltip='The seed used for reproducable outputs. -1 for random seed.'), sg.InputText(default_settings['seed'], key='seed')],
                    [sg.T('Noise Level', tooltip='The noise level (used for variations & interpolations).'), sg.InputText(default_settings['noise_level'], key='noise_level')]]

settings_row_2 = [
                    [sg.T('Input Audio Path', tooltip='Path to audio (used for variations & interpolations).'), sg.InputText(default_settings['audio_source'], key='audio_source'), sg.FileBrowse(file_types=(('Audio Files', '*.wav'),))],
                    [sg.T('Interp Audio Target Path', tooltip='Path to the audio target (used for interpolations).'), sg.InputText(default_settings['audio_target'], key='audio_target'), sg.FileBrowse(file_types=(('Audio Files', '*.wav'),))],
                    [sg.T('Interp Steps', tooltip='The number of interpolations.'), sg.InputText(default_settings['interpolations_linear'], key='interpolations_linear')],
                    [sg.Checkbox('Tame', default=default_settings['tame'], key='tame', tooltip='Decrease output by 3db, then clip.')],
                    [sg.T('Steps', tooltip='The number of steps for the sampler.'), sg.InputText(default_settings['steps'], key='steps')],
                    [sg.T('Sampler', tooltip='The sampler used for the diffusion model.'), sg.Combo(['IPLMS', 'DDPM', 'DDIM'], default_value=default_settings['sampler'], key='sampler')],
                    [sg.T('Schedule Setting', tooltip='The schedule used for the diffusion model.'), sg.Combo(['CrashSchedule', 'LinearSchedule', 'DDPMSchedule', 'SplicedDDPMCosineSchedule', 'LogSchedule'], default_value=default_settings['schedule'], key='schedule')]]

buttons = [          
          [sg.Button('Generate')],
          [sg.Button('Import Model')]]



window = sg.Window('Vextra Sample Diffusion', [settings_header, [sg.Frame('Settings', [[sg.Column(settings_row_1), sg.Column(settings_row_2)]])], buttons], finalize=True, icon='util/data/dtico.ico', enable_close_attempted_event=True)

load_settings(window)

while True:
    event, values = window.read()
    if event in (sg.WINDOW_CLOSE_ATTEMPTED_EVENT, 'Exit'):
        save_settings(values)
        break
    if event == 'Generate':
        thread = Thread(target=generate, args=(window, values,))
        thread.start()
    if event == 'Import Model':
        load_model(window)
    if event == 'model':
        apply_model_params(window, values['model'])
    if event in ('batch_loop', 'batch_size'):
        set_total_output(window, values)


window.close()