#!/bin/bash
####################################################################
#                          macOS defaults                          #
# Please modify start_unix.sh to change these instead of this file #
####################################################################

if [[ -x "$(command -v python3.10)" ]]
then
    python_cmd="python3.10"
fi

export install_dir="$HOME"
export PYTORCH_ENABLE_MPS_FALLBACK=1

####################################################################
