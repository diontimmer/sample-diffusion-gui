from utility.constants import TOP_FOLDER
from utility.gui import get_themed_icon

import PySimpleGUI as sg

def CustomFileBrowse(image_data=get_themed_icon(TOP_FOLDER), target=(sg.ThisRow, -1), file_types=sg.FILE_TYPES_ALL_FILES, initial_folder=None,
               tooltip=None, size=(None, None), s=(None, None), auto_size_button=None, button_color=sg.theme_element_background_color(), change_submits=False,
               enable_events=False, font=None, disabled=False,
               pad=None, p=None, key=None, k=None, visible=True, metadata=None, border_width=0):

    return sg.Button(image_data=image_data, button_type=sg.BUTTON_TYPE_BROWSE_FILE, target=target, file_types=file_types,
                  initial_folder=initial_folder, tooltip=tooltip, size=size, s=s, auto_size_button=auto_size_button,
                  change_submits=change_submits, enable_events=enable_events, disabled=disabled,
                  button_color=button_color, font=font, pad=pad, p=p, key=key, k=k, visible=visible, metadata=metadata, border_width=0)

def CustomFolderBrowse(image_data=get_themed_icon(TOP_FOLDER), target=(sg.ThisRow, -1), initial_folder=None,
               tooltip=None, size=(None, None), s=(None, None), auto_size_button=None, button_color=sg.theme_element_background_color(), change_submits=False,
               enable_events=False, font=None, disabled=False,
               pad=None, p=None, key=None, k=None, visible=True, metadata=None, border_width=0):

    return sg.Button(image_data=image_data, button_type=sg.BUTTON_TYPE_BROWSE_FOLDER, target=target,
                  initial_folder=initial_folder, tooltip=tooltip, size=size, s=s, auto_size_button=auto_size_button,
                  change_submits=change_submits, enable_events=enable_events, disabled=disabled,
                  button_color=button_color, font=font, pad=pad, p=p, key=key, k=k, visible=visible, metadata=metadata, border_width=0)