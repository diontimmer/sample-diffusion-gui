import os, sys
import torch
import time

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