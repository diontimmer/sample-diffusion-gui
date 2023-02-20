from copy import deepcopy
import math
from pathlib import Path
import os
import gc
from diffusion import sampling
import k_diffusion as K
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils import data
from tqdm import trange
from einops import rearrange
import torchaudio
from audio_diffusion.models import DiffusionAttnUnet1D
import numpy as np
from audio_diffusion.utils import Stereo, PadCrop

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


#@title Model code
class DiffusionUncond(nn.Module):
    def __init__(self, global_args):
        super().__init__()

        self.diffusion = DiffusionAttnUnet1D(global_args, n_attn_layers = 4)
        self.diffusion_ema = deepcopy(self.diffusion)
        self.rng = torch.quasirandom.SobolEngine(1, scramble=True)

def compute_interpolation_in_latent(latent1, latent2, lambd):
    '''
    Implementation of Spherical Linear Interpolation: https://en.wikipedia.org/wiki/Slerp
    latent1: tensor of shape (2, n)
    latent2: tensor of shape (2, n)
    lambd: list of floats between 0 and 1 representing the parameter t of the Slerp
    '''
    device = latent1.device
    lambd = torch.tensor(lambd)

    assert(latent1.shape[0] == latent2.shape[0])

    # get the number of channels
    nc = latent1.shape[0]
    interps = []
    for channel in range(nc):
    
      cos_omega = latent1[channel]@latent2[channel] / \
          (torch.linalg.norm(latent1[channel])*torch.linalg.norm(latent2[channel]))
      omega = torch.arccos(cos_omega).item()

      a = torch.sin((1-lambd)*omega) / np.sin(omega)
      b = torch.sin(lambd*omega) / np.sin(omega)
      a = a.unsqueeze(1).to(device)
      b = b.unsqueeze(1).to(device)
      interps.append(a * latent1[channel] + b * latent2[channel])
    return rearrange(torch.cat(interps), "(c b) n -> b c n", c=nc) 

def get_sigmas_vp(n, beta_d=19.9, beta_min=0.1, eps_s=1e-3, device='cpu'):
    """Constructs a continuous VP noise schedule."""
    t = torch.linspace(1, eps_s, n, device=device)
    sigmas = torch.sqrt(torch.exp(beta_d * t ** 2 / 2 + beta_min * t) - 1)
    return K.sampling.append_zero(sigmas)
  
def load_to_device(path, sr):
    audio, file_sr = torchaudio.load(path)
    if sr != file_sr:
      audio = torchaudio.transforms.Resample(file_sr, sr)(audio)
    audio = audio.to(device)
    return audio

def get_alphas_sigmas(t):
    """Returns the scaling factors for the clean image (alpha) and for the
    noise (sigma), given a timestep."""
    return torch.cos(t * math.pi / 2), torch.sin(t * math.pi / 2)

def get_crash_schedule(t):
    sigma = torch.sin(t * math.pi / 2) ** 2
    alpha = (1 - sigma ** 2) ** 0.5
    return alpha_sigma_to_t(alpha, sigma)

def t_to_alpha_sigma(t):
    """Returns the scaling factors for the clean image and for the noise, given
    a timestep."""
    return torch.cos(t * math.pi / 2), torch.sin(t * math.pi / 2)

def alpha_sigma_to_t(alpha, sigma):
    """Returns a timestep, given the scaling factors for the clean image and for
    the noise."""
    return torch.atan2(sigma, alpha) / math.pi * 2
 
class Object(object):
    pass           

def create_model_args(model_name, sample_size, sample_rate, latent_dim, ckpt_path):
    args = Object()
    args.model_name = model_name
    args.sample_size = sample_size
    args.sample_rate = sample_rate
    args.latent_dim = latent_dim
    args.ckpt_path = ckpt_path
    return args


def create_model(args):
    global device
    model = DiffusionUncond(args)
    model.load_state_dict(torch.load(args.ckpt_path)["state_dict"])
    model = model.requires_grad_(False).to(device)
    del model.diffusion
    model_fn = model.diffusion_ema
    return model_fn


def create_sampler_args(sampler_type, eta, beta_d, beta_min, rho, rtol, atol):
    args = Object()
    args.sampler_type = sampler_type
    args.eta = eta
    args.beta_d = beta_d
    args.beta_min = beta_min
    args.rho = rho
    args.rtol = rtol
    args.atol = atol
    return args

def sample(model_fn, sampler_args, noise, steps=100, noise_level = 1.0):
  #Check for k-diffusion
  if sampler_args.sampler_type.startswith('k-'):
    denoiser = K.external.VDenoiser(model_fn)
    sigmas = get_sigmas_vp(steps, sampler_args.beta_d, sampler_args.beta_min, eps_s=1e-3, device=device).half()

  elif sampler_args.sampler_type.startswith("v-"):
    t = torch.linspace(1, 0, steps + 1, device=device)[:-1]
    step_list = get_crash_schedule(t)

  if sampler_args.sampler_type == "v-ddim":
    return sampling.sample(model_fn, noise, step_list, sampler_args.eta, {})
  elif sampler_args.sampler_type == "v-iplms":
    return sampling.iplms_sample(model_fn, noise, step_list, {})

  elif sampler_args.sampler_type == "k-heun":
    return K.sampling.sample_heun(denoiser, noise, sigmas, disable=False)
  elif sampler_args.sampler_type == "k-lms":
    return K.sampling.sample_lms(denoiser, noise, sigmas, disable=False)
  elif sampler_args.sampler_type == "k-dpmpp_2s_ancestral":
    return K.sampling.sample_dpmpp_2s_ancestral(denoiser, noise, sigmas, disable=False)
  elif sampler_args.sampler_type == "k-dpm-2":
    return K.sampling.sample_dpm_2(denoiser, noise, sigmas, disable=False)
  elif sampler_args.sampler_type == "k-dpm-fast":
    return K.sampling.sample_dpm_fast(denoiser, noise, sampler_args.sigma_min, sampler_args.sigma_max, steps, disable=False)
  elif sampler_args.sampler_type == "k-dpm-adaptive":
    return K.sampling.sample_dpm_adaptive(denoiser, noise, sampler_args.sigma_min, sampler_args.sigma_max, rtol=sampler_args.rtol, atol=sampler_args.atol, disable=False)

def resample(model_fn, sampler_args, audio, chunk_size, steps=100, noise_level = 1.0, batch_size=1):
  global device
  if sampler_args.sampler_type.startswith("v-"):
    t = torch.linspace(0, 1, steps + 1, device=device)
    step_list = get_crash_schedule(t)
    step_list = step_list[step_list < noise_level]

    alpha, sigma = t_to_alpha_sigma(step_list[-1])
    noised = torch.randn([batch_size, 2, chunk_size], device='cuda')
    noised = audio * alpha + noised * sigma
    noise = noised

  elif sampler_args.sampler_type.startswith("k-"):
    denoiser = K.external.VDenoiser(model_fn)
    noised = audio + torch.randn_like(audio) * noise_level
    sigmas = K.sampling.get_sigmas_karras(steps, sampler_args.sigma_min, noise_level, sampler_args.rho, device=device)

  # Denoise
  if sampler_args.sampler_type == "v-iplms":
    return sampling.iplms_sample(model_fn, noised, step_list.flip(0)[:-1], {})

  if sampler_args.sampler_type == "v-ddim":
    return sampling.sample(model_fn, noise, step_list, sampler_args.eta, {})

  elif sampler_args.sampler_type == "k-heun":
    return K.sampling.sample_heun(denoiser, noised, sigmas, disable=False)

  elif sampler_args.sampler_type == "k-dpmpp_2s_ancestral":
    return K.sampling.sample_dpmpp_2s_ancestral(denoiser, noised, sigmas, disable=False)

  elif sampler_args.sampler_type == "k-lms":
    return K.sampling.sample_lms(denoiser, noised, sigmas, disable=False)

  elif sampler_args.sampler_type == "k-dpm-2":
    return K.sampling.sample_dpm_2(denoiser, noised, sigmas, s_noise=0., disable=False)

  elif sampler_args.sampler_type == "k-dpm-fast":
    return K.sampling.sample_dpm_fast(denoiser, noised, sampler_args.sigma_min, noise_level, steps, disable=False)

  elif sampler_args.sampler_type == "k-dpm-adaptive":
    return K.sampling.sample_dpm_adaptive(denoiser, noised, sampler_args.sigma_min, noise_level, rtol=sampler_args.rtol, atol=sampler_args.atol, disable=False)

def reverse_sample(model_fn, model_args, sampler_args, audio_samples, steps=100, noise_level = 1.0, batch_size=1):
  global device
  if sampler_args.sampler_type.startswith("v-"):
    t = torch.linspace(0, 1, steps + 1, device=device)
    step_list = get_crash_schedule(t)
    alpha, sigma = t_to_alpha_sigma(step_list[-1])
    noised = torch.randn([batch_size, 2, model_args.sample_size], device=device)
    noised = audio_samples * alpha + noised * sigma
    noise = noised

    if sampler_args.sampler_type == "v-iplms":
      return sampling.iplms_sample(model_fn, audio_samples, step_list, {}, is_reverse=True)

    if sampler_args.sampler_type == "v-ddim":
      return sampling.sample(model_fn, noise, step_list, sampler_args.eta, {}, is_reverse=True)

  elif sampler_args.sampler_type.startswith("k-"):
    denoiser = K.external.VDenoiser(model_fn)
    sigmas = K.sampling.get_sigmas_karras(steps, sampler_args.sigma_min, noise_level, sampler_args.rho, device=device)

  # Denoise
  if sampler_args.sampler_type == "k-heun":
    return K.sampling.sample_heun(denoiser, audio_samples, sigmas.flip(0)[:-1], disable=False)
  elif sampler_args.sampler_type == "k-lms":
    return K.sampling.sample_lms(denoiser, audio_samples, sigmas.flip(0)[:-1], disable=False)
  elif sampler_args.sampler_type == "k-dpmpp_2s_ancestral":
    return K.sampling.sample_dpmpp_2s_ancestral(denoiser, audio_samples, sigmas.flip(0)[:-1], disable=False)
  elif sampler_args.sampler_type == "k-dpm-2":
    return K.sampling.sample_dpm_2(denoiser, audio_samples, sigmas.flip(0)[:-1], s_noise=0., disable=False)
  elif sampler_args.sampler_type == "k-dpm-fast":
    return K.sampling.sample_dpm_fast(denoiser, audio_samples, noise_level, sampler_args.sigma_min, steps, disable=False)

  elif sampler_args.sampler_type == "k-dpm-adaptive":
    return K.sampling.sample_dpm_adaptive(denoiser, audio_samples, noise_level, sampler_args.sigma_min, rtol=sampler_args.rtol, atol=sampler_args.atol, disable=False)



def generate_func(batch_size, steps, model_fn, sampler_args, model_args):
    global device
    torch.cuda.empty_cache()
    gc.collect()
    noise = torch.randn([batch_size, 2, model_args.sample_size]).to(device)
    generated = sample(model_fn, sampler_args, noise, steps)
    generated = generated.clamp(-1, 1)
    return generated

def variation_func(batch_size, steps, model_fn, sampler_args, model_args, noise_level, file_path):
    global device
    torch.cuda.empty_cache()
    gc.collect()    
    augs = torch.nn.Sequential(
      PadCrop(model_args.sample_size, randomize=True),
      Stereo()
    )
    audio_sample = load_to_device(file_path, model_args.sample_rate)
    audio_sample = augs(audio_sample).unsqueeze(0).repeat([batch_size, 1, 1])
    generated = resample(model_fn, sampler_args, audio_sample, model_args.sample_size, steps, noise_level, batch_size)
    return generated

def interp_func(batch_size, steps, model_fn, sampler_args, model_args, source_audio, target_audio, n_interps, noise_level):
    global device
    torch.cuda.empty_cache()
    gc.collect()
    augs = torch.nn.Sequential(
      PadCrop(model_args.sample_size, randomize=True),
      Stereo()
    )    
    audio_sample_1 = load_to_device(source_audio, model_args.sample_rate)
    audio_sample_2 = load_to_device(target_audio, model_args.sample_rate)
    audio_samples = augs(audio_sample_1).unsqueeze(0).repeat([2, 1, 1])
    audio_samples[1] = augs(audio_sample_2)    
    reversed = reverse_sample(model_fn, model_args, sampler_args, audio_samples, steps, noise_level, batch_size)    
    latent_series = compute_interpolation_in_latent(reversed[0], reversed[1], [k/n_interps for k in range(n_interps + 2)])  
    generated = sample(model_fn, sampler_args, latent_series, steps)
    return generated