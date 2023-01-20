from util.gui import *
from threading import Thread

sg.theme('DarkGrey7')   # Add a touch of color

loaded_models = get_models()


settings_header = [
                    [sg.T('Model File'), sg.Combo(loaded_models, key='model', default_value=loaded_models[0])],
                    [sg.T('Mode'), sg.Combo(['Generation', 'Interpolation', 'Extrapolation', 'Inpainting', 'Extension'], default_value=default_settings['mode'], key='mode')],
                    [sg.T('Output Path'), sg.InputText('output', key='output_path'), sg.FolderBrowse()],
                    [sg.T('Batch Size'), sg.InputText(default_settings['batch_size'], key='batch_size')]]
settings_row_1 = [
                    [sg.Checkbox('use_autocast', default=default_settings['use_autocast'], key='use_autocast')],
                    [sg.Checkbox('use_autocrop', default=default_settings['use_autocrop'], key='use_autocrop')],
                    [sg.T('Device Offload'), sg.Combo(['cpu', 'gpu'], default_value=default_settings['device_offload'], key='device_offload')],
                    [sg.T('Sample Rate'), sg.InputText(default_settings['sample_rate'], key='sample_rate')],
                    [sg.T('Chunk Size'), sg.InputText(default_settings['chunk_size'], key='chunk_size')],
                    [sg.T('Seed'), sg.InputText(default_settings['seed'], key='seed')],
                    [sg.T('Noise Level'), sg.InputText(default_settings['noise_level'], key='noise_level')]]

settings_row_2 = [
                    [sg.T('Interp Audio Source Path'), sg.InputText(default_settings['audio_source'], key='audio_source'), sg.FileBrowse(file_types=(('Audio Files', '*.wav'),))],
                    [sg.T('Interp Audio Target Path'), sg.InputText(default_settings['audio_target'], key='audio_target'), sg.FileBrowse(file_types=(('Audio Files', '*.wav'),))],
                    [sg.T('Resamples'), sg.InputText(default_settings['resamples'], key='resamples')],
                    [sg.Checkbox('Keep Start', default=default_settings['keep_start'], key='keep_start')],
                    [sg.Checkbox('Tame', default=default_settings['tame'], key='tame')],
                    [sg.T('Steps'), sg.InputText(default_settings['steps'], key='steps')],
                    [sg.T('Sampler'), sg.Combo(['IPLMS', 'MPL', 'BP'], default_value=default_settings['sampler'], key='sampler')],
                    [sg.T('Setting'), sg.Combo(['CrashSchedule', 'LinearSchedule', 'DDPMSchedule', 'SplicedDDPMCosineSchedule', 'LogSchedule'], default_value=default_settings['schedule'], key='schedule')]]

buttons = [          
          [sg.Button('Generate')],
          [sg.Button('Import Model')]]



window = sg.Window('Dion Timmer Diffusion GUI', [settings_header, [sg.Frame('Settings', [[sg.Column(settings_row_1), sg.Column(settings_row_2)]])], buttons], finalize=True)


if loaded_models[0]:
    loaded_model_samplerate = loaded_models[0].split('.')[-2].split('_')[-2]
    loaded_model_size = loaded_models[0].split('.')[-2].split('_')[-1]
    window['sample_rate'].update(value=loaded_model_samplerate)

while True:
    event, values = window.read()
    if event in (sg.WIN_CLOSED, 'Exit'):
        break
    if event == 'Generate':
        thread = Thread(target=generate, args=(window, values,))
        thread.start()
    if event == 'Import Model':
        load_model(window)

window.close()