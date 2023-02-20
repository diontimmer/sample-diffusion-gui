from util.gui import *
from gui_train import show_trainer

sg.theme('DarkGrey7')   # Add a touch of color

loaded_models = get_models()

tree_layout = [
                [sg.Button('Play'), sg.Button('Save'), sg.Button('Locate'), sg.Button('Load As Input'), sg.T('Preview Volume: '), sg.Slider(range=(0, 100), orientation='h', size=(50, 20), enable_events=True, key="-VOLUME-", default_value=100)],
                [sg.Tree(data=sg.TreeData(), key='file_tree', headings=[], auto_size_columns=True, enable_events=True, show_expanded=True, expand_x=True, row_height=30)]
                ]

settings_header = [
                    [sg.T('Model File', tooltip='Path to the model checkpoint file to be used.'), sg.Combo(loaded_models, key='model', default_value='', enable_events=True,)],
                    [sg.T('Mode', tooltip='The mode of operation'), sg.Combo(['Generation', 'Interpolation', 'Variation'], default_value=default_settings['mode'], key='mode')],
                    [sg.T('Output Path', tooltip='Path for output renders.'), sg.InputText('output', key='output_path'), sg.FolderBrowse()],
                    [sg.T('Batch Loop', tooltip='The number of times the internal batch size will loop.'), sg.InputText('1', key='batch_loop', size=(15,0), enable_events=True)],
                    [sg.T('Internal Batch Size', tooltip='The maximal number of samples to be produced per batch.'), sg.InputText(default_settings['batch_size'], key='batch_size', size=(15,0), enable_events=True)],
                    [sg.T('Total output files: 1', tooltip='Batch Loop * Internal Batch Size', key='batch_viewer')]]
settings_row_1 = [
                    [sg.T('Custom Batch Name', tooltip='Custom batch name for filenames.'), sg.InputText('', key='custom_batch_name', enable_events=True)],
                    [sg.T('Sample Rate', tooltip='  The samplerate the model was trained on.'), sg.InputText(default_settings['sample_rate'], key='sample_rate', size=(15,0), enable_events=True)],
                    [sg.T('Chunk Size', tooltip='The native chunk size of the model.'), sg.InputText(default_settings['chunk_size'], key='chunk_size', size=(15,0), enable_events=True), sg.T('', key='total_seconds')],
                    [sg.T('Seed', tooltip='The seed used for reproducable outputs. -1 for random seed.'), sg.InputText(default_settings['seed'], key='seed', size=(15,0))],
                    [sg.T('Noise Level', tooltip='The noise level (used for variations & interpolations).'), sg.InputText(default_settings['noise_level'], key='noise_level', size=(15,0))],
                    [sg.T('Steps', tooltip='The number of steps for the sampler.'), sg.InputText(default_settings['steps'], key='steps', size=(15,0))],
                    [sg.T('Secondary Model File', tooltip='Secondary model file used for merging.'), sg.Combo(loaded_models, key='secondary_model', default_value='', enable_events=True,)],
                    [sg.T('Secondary Merge Ratio', tooltip='Merge ratio for model merging [A-B] -> [0-1]'), sg.InputText('0.5', key='merge_ratio', size=(15,0), enable_events=True)],
                    [sg.T('Input Audio Path', tooltip='Path to audio (used for variations & interpolations).'), sg.InputText(default_settings['audio_source'], key='audio_source'), sg.FileBrowse(file_types=(('Audio Files', '*.wav'),))],
                    [sg.T('Interp Audio Target Path', tooltip='Path to the audio target (used for interpolations).'), sg.InputText(default_settings['audio_target'], key='audio_target'), sg.FileBrowse(file_types=(('Audio Files', '*.wav'),))],
                    [sg.T('Interp Steps', tooltip='The number of interpolations.'), sg.InputText(default_settings['interpolations_linear'], key='interpolations_linear', size=(5,0))],
                    ]

settings_row_2 = [
                    [sg.T('Sampler', tooltip='The sampler used for the diffusion model.'), sg.Combo(['v-ddim', 'v-iplms', 'k-heun', 'k-lms', 'k-dpmpp_2s_ancestral', 'k-dpm-2', 'k-dpm-fast', 'k-dpm-adaptive'], default_value='v-iplms', key='sampler')],
                    [sg.T('V-ETA'), sg.InputText('0', key='ddim_eta', size=(5,0))],
                    [sg.T('K-Beta D'), sg.InputText('19.9', key='beta_d', size=(7,0))],
                    [sg.T('K-Beta Min'), sg.InputText('0.1', key='beta_min', size=(7,0))],
                    [sg.T('K-RHO'), sg.InputText('7', key='rho', size=(5,0))],
                    [sg.T('K-adaptive-RTOL'), sg.InputText('0.01', key='rtol', size=(5,0))],
                    [sg.T('K-adaptive-ATOL'), sg.InputText('0.01', key='atol', size=(5,0))],
                    ]

loading_gif_img = sg.Image(background_color=sg.theme_background_color(), key='-LOADINGGIF-')

buttons =           [sg.Button('Generate'), sg.Button('Import Model'), sg.Button('Train'), loading_gif_img]



window = sg.Window('Vextra Sample Diffusion', [
    [sg.Frame('Preview', tree_layout)],
    [sg.Sizer(0, 10)], 
    [sg.Frame('Main Settings', settings_header)],
    [sg.Sizer(0, 10)],  
    [sg.Frame('Additional Settings', [[sg.Column(settings_row_1)]], vertical_alignment='top'), sg.Frame('Sampler Settings', [[sg.Column(settings_row_2)]], vertical_alignment='top')],
    buttons,
    ], finalize=True, icon='util/data/dtico.ico', enable_close_attempted_event=True, resizable=False)
window['file_tree'].bind('<Double-Button-1>', '_double_clicked')
window['-LOADINGGIF-'].update(visible=False)


# init
load_settings(window)
refresh_models(window)
set_total_output(window)
set_total_seconds(window)

while True:
    event, values = window.read(timeout=10)
    loading_gif_img.update_animation(LOADING_GIF_B64, time_between_frames=50)
    if event in (sg.WINDOW_CLOSE_ATTEMPTED_EVENT, 'Exit'):
        save_settings(values)
        break

    if event == 'Generate':
        show_save_window(window, values)

    if event == 'Train':
        show_trainer()

    if event == 'Import Model':
        load_model(window)

    if event == 'model':
        apply_model_params(window, values['model'])

    if event in ('batch_loop', 'batch_size'):
        set_total_output(window)
    if event in ['sample_rate', 'model', 'chunk_size']:
        set_total_seconds(window)
    if event == '-VOLUME-':
        set_volume(values['-VOLUME-'])

    if len(values['file_tree']) > 0:
        if event in ('file_tree_double_clicked', 'Play'):
            play_audio(values['file_tree'][0])

        if event == 'Save':
            Thread(target=copysave, args=(values, )).start()

        if event == 'Locate':
            open_in_finder(values['file_tree'][0])

        if event == 'Load As Input':
            try:
                window['audio_source'].update(value=values['file_tree'][0])
                window['mode'].update(value='Variation')
            except (IndexError, TypeError):
                pass        


window.close()
