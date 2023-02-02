import torch

# fp_list = ['FP16', 'FP32'] Float Precision


def ratio_merge(model_a, model_b, out_file=None, fp_precision='FP16', alpha=0.5, device='cuda'):
    # Load Models
    model_0 = torch.load(model_a, map_location=torch.device('cuda'))
    model_1 = torch.load(model_b, map_location=torch.device('cuda'))
    theta_0 = model_0['state_dict']
    theta_1 = model_1['state_dict']

    # Merging Common Weights
    for key in theta_0.keys():
        if 'main' in key and key in theta_1:
            theta_0[key] = (1 - alpha) * theta_0[key] + alpha * theta_1[key]

    # Merging Distinct Weights
    for key in theta_1.keys():
        if 'main' in key and key not in theta_0:
            theta_0[key] = theta_1[key]

    if fp_precision[-6:] == 'FP16':
        # Converting to FP16
        for key in theta_0.keys():
            if 'main' in key and key not in theta_0:
                theta_0[key] = theta_0[key].to(torch.float16)
    if out_file is not None:
        torch.save(model_0, f'{out_file}')

    return model_0
