import os, sys
import torch
import time
from audio_diffusion.autoencoders import AudioAutoencoder
from audio_diffusion.models import LatentAudioDiffusion
#from trainers.trainers import LatentAudioDiffusionTrainer
from torch.nn.parameter import Parameter

# original code by @Twobob

def start_trim(model_path, output_path):

    if not os.path.isfile(model_path):
        print("No file was found at the given path.")
        return

    print(f"Trimming model at '{model_path}'...\n")

    start_time = time.process_time()

    untrimmed_size = os.path.getsize(model_path)
    untrimmed = torch.load(model_path, map_location="cpu")

    trimmed = trim_model(untrimmed)

    torch.save(trimmed, output_path)

    end_time = time.process_time()
    elapsed = end_time - start_time

    trimmed_size = os.path.getsize(output_path)

    bytes = untrimmed_size - trimmed_size
    megabytes = bytes / 1024.0 / 1024.0

    print(f"Untrimmed: {untrimmed_size} B, {untrimmed_size / 1024.0 / 1024.0} MB")
    print(f"Trimmed: {trimmed_size} B, {trimmed_size / 1024.0 / 1024.0} MB")

    print(
        f"\nDone! Trimmed {untrimmed_size - trimmed_size} B, or {megabytes} MB, in {elapsed} seconds."
    )


def trim_model(untrimmed):
    trimmed = dict()

    for k in untrimmed.keys():
        if k != "optimizer_states":
            trimmed[k] = untrimmed[k]

    if "global_step" in untrimmed:
        print(f"Global step: {untrimmed['global_step']}.")

    temp = trimmed["state_dict"].copy()

    trimmed_model = dict()

    for k in temp:
        trimmed_model[k] = temp[k].half()
        
    trimmed["state_dict"] = trimmed_model

    return trimmed

def prune_ckpt_weights(trainer_state_dict):
  new_state_dict = {}
  for name, param in trainer_state_dict.items():
      if name.startswith("diffusion_ema.ema_model."):
          new_name = name.replace("diffusion_ema.ema_model.", "diffusion.")
          if isinstance(param, Parameter):
              # backwards compatibility for serialized parameters
              param = param.data
          new_state_dict[new_name] = param
          
  return new_state_dict

def prune_latent_uncond(model_path, output_path, sample_rate, ld_sample_size):
    print("Creating the model...")

    ae_config = {"channels": 64, "c_mults": [2, 4, 8, 16, 32], "strides": [2, 2, 2, 2, 2], "latent_dim": 32}

    autoencoder = AudioAutoencoder( 
        **ae_config
    ).eval()

    latent_diffusion_config = {"io_channels": 32, "n_attn_layers": 4, "channels": [512]*6 + [1024]*4, "depth": 10}

    #Create the diffusion model itself
    latent_diffusion_model = LatentAudioDiffusion(autoencoder, **latent_diffusion_config)

    #Create the trainer
    #ld_trainer = LatentAudioDiffusionTrainer(latent_diffusion_model)

    trainer_state_dict = torch.load(model_path)["state_dict"]

    new_ckpt = {}

    new_ckpt["ld_state_dict"] = prune_ckpt_weights(trainer_state_dict)
    new_ckpt["ld_config"] = latent_diffusion_config
    new_ckpt["sample_rate"] = sample_rate
    new_ckpt["ld_sample_size"] = ld_sample_size

    latent_diffusion_model.load_state_dict(new_ckpt["ld_state_dict"])

    torch.save(new_ckpt, f'output_path')