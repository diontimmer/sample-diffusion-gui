import PySimpleGUI as sg
import subprocess

options_col = sg.Column([
        [sg.Text('Wandb API key'), sg.InputText(default_text="", key="ext_trainer_wandb_key", password_char="*")],
        [sg.Text('Model name'), sg.InputText(default_text="dd-drums-finetune", key="ext_trainer_NAME")],
        [sg.Text('Training directory'), sg.InputText(default_text="", key="ext_trainer_TRAINING_DIR"), sg.FolderBrowse()],
        [sg.Text('Checkpoint path'), sg.InputText(default_text="/content/drive/MyDrive/AI/models/jmann-small-190k.ckpt", key="ext_trainer_CKPT_PATH"), sg.FileBrowse(file_types=(('Checkpoint file', '*.ckpt'),))],
        [sg.Text('Output directory'), sg.InputText(default_text="", key="ext_trainer_OUTPUT_DIR"), sg.FolderBrowse()],
        [sg.Text('Demo every'), sg.InputText(default_text="250", key="ext_trainer_DEMO_EVERY")],
        [sg.Text('Checkpoint every'), sg.InputText(default_text="500", key="ext_trainer_CHECKPOINT_EVERY")],
        [sg.Text('Sample rate'), sg.InputText(default_text="48000", key="ext_trainer_SAMPLE_RATE")],
        [sg.Text('Sample size'), sg.InputText(default_text="65536", key="ext_trainer_SAMPLE_SIZE")],
        [sg.Checkbox('Random Crop', default=True, key="ext_trainer_RANDOM_CROP")],
        [sg.Text('Batch size'), sg.InputText(default_text="1", key="ext_trainer_BATCH_SIZE")],
        [sg.Text('Accumulate batches'), sg.InputText(default_text="4", key="ext_trainer_ACCUM_BATCHES")],
        [sg.Text('Num Workers'), sg.InputText(default_text="1", key="ext_trainer_NUM_WORKERS")],
        [sg.Text('Num Nodes'), sg.InputText(default_text="1", key="ext_trainer_NUM_NODES")],
        [sg.Text('Num GPUs'), sg.InputText(default_text="1", key="ext_trainer_NUM_GPUS")],
        ], scrollable=True, vertical_scroll_only=True, size=(600, 200), expand_x=True, expand_y=True)

def run_training(values):
    global window
    args = [
            "venv\\Scripts\\python", "extensions\\dd_trainer\\train_uncond.py", 
            "--ckpt-path", values['ext_trainer_CKPT_PATH'],
            "--name", values['ext_trainer_NAME'],
            "--training-dir", values['ext_trainer_TRAINING_DIR'],
            "--sample-size", values['ext_trainer_SAMPLE_SIZE'],
            "--accum-batches", values['ext_trainer_ACCUM_BATCHES'],
            "--sample-rate", values['ext_trainer_SAMPLE_RATE'],
            "--batch-size", values['ext_trainer_BATCH_SIZE'],
            "--demo-every", values['ext_trainer_DEMO_EVERY'],
            "--checkpoint-every", values['ext_trainer_CHECKPOINT_EVERY'],
            "--num-workers", values['ext_trainer_NUM_WORKERS'],
            "--num-nodes", values['ext_trainer_NUM_NODES'],
            "--num-gpus", values['ext_trainer_NUM_GPUS'], 
            "--random-crop", f"True" if values['ext_trainer_RANDOM_CROP'] else "",
            "--save-path", f"{values['ext_trainer_OUTPUT_DIR']}/{values['ext_trainer_NAME']}"
            ]

    window.start_thread(lambda: subprocess.run(args, shell=True), 'ext_trainer_TRAINING_DONE')
    window['ext_trainer_TRAIN'].update(disabled=True)


# ****************************************************************************
# *                                 EXTENSION                                *
# ****************************************************************************


# These functions are mandatory for the extension to work. Replace this with your own magic.

def create_tab_info():
    layout = [
        [sg.Frame('Training Settings', [[options_col]], expand_x=True, expand_y=True)],
        [sg.Button('Start training', key='ext_trainer_TRAIN')]
    ]
    ext_info = {
                'name': 'Trainer', 
                'version': '1.0', 
                'author': 'Dion Timmer, Zach Evans', 
                'description': 'DD Trainer Extension',
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
    if event == 'ext_trainer_TRAIN':
        run_training(values)
    if event == 'ext_trainer_TRAINING_DONE':
        window['ext_trainer_TRAIN'].update(disabled=False)