from util.gui import *
import subprocess


def save_train_settings(values):
    with open('train_gui_settings.pickle', 'wb') as f:
        pickle.dump(values, f)

def load_train_settings(window):
    try:
        with open('train_gui_settings.pickle', 'rb') as f:
            values = pickle.load(f)
            window['NAME'].update(value=values['NAME'])
            window['TRAINING_DIR'].update(value=values['TRAINING_DIR'])
            window['CKPT_PATH'].update(value=values['CKPT_PATH'])
            window['OUTPUT_DIR'].update(value=values['OUTPUT_DIR'])
            window['DEMO_EVERY'].update(value=values['DEMO_EVERY'])
            window['CHECKPOINT_EVERY'].update(value=values['CHECKPOINT_EVERY'])
            window['SAMPLE_RATE'].update(value=values['SAMPLE_RATE'])
            window['SAMPLE_SIZE'].update(value=values['SAMPLE_SIZE'])
            window['RANDOM_CROP'].update(value=values['RANDOM_CROP'])
            window['BATCH_SIZE'].update(value=values['BATCH_SIZE'])
            window['ACCUM_BATCHES'].update(value=values['ACCUM_BATCHES'])
            window['wandb_key'].update(value=values['wandb_key'])
    except:
        pass

def show_trainer():
    # Define the PySimpleGUI layout
    layout = [
        [sg.Text('Wandb API key'), sg.InputText(default_text="", key="wandb_key", password_char="*")],
        [sg.Text('Model name'), sg.InputText(default_text="dd-drums-finetune", key="NAME")],
        [sg.Text('Training directory'), sg.InputText(default_text="", key="TRAINING_DIR"), sg.FolderBrowse()],
        [sg.Text('Checkpoint path'), sg.InputText(default_text="/content/drive/MyDrive/AI/models/jmann-small-190k.ckpt", key="CKPT_PATH"), sg.FileBrowse(file_types=(('Checkpoint file', '*.ckpt'),))],
        [sg.Text('Output directory'), sg.InputText(default_text="", key="OUTPUT_DIR"), sg.FolderBrowse()],
        [sg.Text('Demo every'), sg.InputText(default_text="250", key="DEMO_EVERY")],
        [sg.Text('Checkpoint every'), sg.InputText(default_text="500", key="CHECKPOINT_EVERY")],
        [sg.Text('Sample rate'), sg.InputText(default_text="48000", key="SAMPLE_RATE")],
        [sg.Text('Sample size'), sg.InputText(default_text="65536", key="SAMPLE_SIZE")],
        [sg.Checkbox('Random Crop', default=True, key="RANDOM_CROP")],
        [sg.Text('Batch size'), sg.InputText(default_text="1", key="BATCH_SIZE")],
        [sg.Text('Accumulate batches'), sg.InputText(default_text="4", key="ACCUM_BATCHES")],
        [sg.Button('Train', bind_return_key=True)]
    ]

    # Create the PySimpleGUI window
    window = sg.Window('Train Model', layout, finalize=True, enable_close_attempted_event=True)
    load_train_settings(window)
    # Event loop to process user input
    while True:
        event, values = window.read()

        # If the user closes the window, exit the program
        if event in (sg.WINDOW_CLOSE_ATTEMPTED_EVENT, 'Exit'):
            save_train_settings(values)
            break
        # If the user clicks the "Train" button, run the command with the user's input values
        if event == 'Train':
            name = values['NAME']
            training_dir = values['TRAINING_DIR']
            ckpt_path = values['CKPT_PATH']
            output_dir = f"{values['OUTPUT_DIR']}/{name}"
            demo_every = int(values['DEMO_EVERY'])
            checkpoint_every = int(values['CHECKPOINT_EVERY'])
            sample_rate = int(values['SAMPLE_RATE'])
            sample_size = int(values['SAMPLE_SIZE'])
            random_crop = values['RANDOM_CROP']
            batch_size = int(values['BATCH_SIZE'])
            accum_batches = int(values['ACCUM_BATCHES'])
            random_crop_str = f"--random-crop True" if random_crop else ""
            ckpt_path_str = f"--ckpt-path {ckpt_path}" if ckpt_path else ""
        
            save_train_settings(values)

            if values['wandb_key'] == "":
                print("Please enter your wandb API key")
                continue

            subprocess.run(['venv\\Scripts\\wandb', 'login', values['wandb_key']], shell=True)

            print(["python3",
                            "train_uncond.py", ckpt_path_str,
                            "--name", name,
                            "--training-dir", training_dir,
                            "--sample-size", sample_size,
                            "--accum-batches", accum_batches,
                            "--sample-rate", sample_rate,
                            "--batch-size", batch_size,
                            "--demo-every", demo_every,
                            "--checkpoint-every", checkpoint_every,
                            "--num-workers", "2",
                            "--num-gpus", "1", random_crop_str,
                            "--save-path", output_dir])

            breakpoint()
            subprocess.run(["python3",
                            "train_uncond.py", ckpt_path_str,
                            "--name", name,
                            "--training-dir", training_dir,
                            "--sample-size", sample_size,
                            "--accum-batches", accum_batches,
                            "--sample-rate", sample_rate,
                            "--batch-size", batch_size,
                            "--demo-every", demo_every,
                            "--checkpoint-every", checkpoint_every,
                            "--num-workers", "2",
                            "--num-gpus", "1", random_crop_str,
                            "--save-path", output_dir])

    # Close the PySimpleGUI window
    window.close()

if __name__ == "__main__":
    show_trainer()