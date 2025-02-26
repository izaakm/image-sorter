#!/usr/bin/env python3

"""
Main script for sorting images in a folder into subfolders. This script
launches a GUI which displays one image after the other and lets the user vote
for different given labels from a list given as input to the script.

USAGE:

    python sort_folder.py --folder <INPUT-FOLDER> --labels <INPUT-LABEL1> <INPUT-LABEL2> ...

Author: Christian Baumgartner (c.baumgartner@imperial.ac.uk)
Date: 31. Jan 2016
"""

import argparse
# import Tkinter as tk
import tkinter as tk
import os
import glob
import sys
import shutil
import json

# from shutil import copyfile, move
from PIL import ImageTk, Image
from collections import defaultdict

IMAGE_EXTENSIONS = set(['.jpg', '.jpeg', '.gif', '.tif', '.tiff', '.psd', '.bmp'])

class ImageGui:
    """
    GUI for iFind1 image sorting. This draws the GUI and handles all the events.
    Useful, for sorting views into sub views or for removing outliers from the data.
    """

    def __init__(self, master, labels, records, destination):
        """
        Initialise GUI
        :param master: The parent window
        :param labels: A list of labels that are associated with the images
        :param paths: A list of file paths to images
        :return:
        """

        # So we can quit the window from within the functions
        self.master = master

        # Extract the frame so we can draw stuff on it
        frame = tk.Frame(master)

        # Initialise grid
        frame.grid()

        # Start at the first file name
        self.index = 0
        self.labels = labels
        # self.paths = paths
        self.records = records
        self.destination = destination
        self.data_path = os.path.join(destination, 'data.json')

        # Number of labels and paths
        self.n_labels = len(labels)
        # self.n_paths = len(paths)
        self.n_records = len(records)
        # print(self.n_records)
        # print(self.records)

        # Set empty image container
        self.image_raw = None
        self.image = None
        self.image_panel = tk.Label(frame)

        # set image container to first image
        # self.set_image(paths[self.index])
        self.set_image(records[self.index]['path'])

        # Add progress label
        if isinstance(self.records[self.index]['label'], str):
            # progress_string = "%d/%d" % (self.index, self.n_paths)
            progress_string = '{}/{} ({})'.format(self.index+1, self.n_records, self.records[self.index]['label'])
        else:
            progress_string = "%d/%d" % (self.index+1, self.n_records)
        self.progress_label = tk.Label(frame, text=progress_string)

        # Make buttons
        _button_index = 0
        self.buttons = []
        self.buttons.append(
            tk.Button(
                frame,
                text="<",
                fg="green",
                # Command MUST be a lambda.
                command=lambda: self.show_prev_image()
            )
        )
        self.buttons.append(
            tk.Button(
                frame,
                text=">",
                fg="green",
                # Command MUST be a lambda.
                command=lambda: self.show_next_image()
            )
        )
        self.buttons.append(
            tk.Button(
                frame,
                text="Unlabeled",
                fg="green",
                # Command MUST be a lambda.
                command=lambda: self.go_to_unlabeled()
            )
        )
        # self.buttons.append(tk.Button(frame, text="next im", width=10, height=1, fg='green', command=lambda l=label: self.move_next_image()))
        for key, label in enumerate(labels, start=1):
            self.buttons.append(
                tk.Button(
                    frame,
                    text=f'{label} ({key})',
                    command=lambda l=label: self.vote(l)
                )
            )
            # I am not sure why this `l=label` is necessary, but it is.
            #   command=lambda: self.vote(label)     ... uses whatever the value of label is at the time called.
            #   command=lambda l=label: self.vote(l) ... uses whatever the value of label is at the time initialized.
            # key bindings (so number pad can be used as shortcut)
            master.bind(str(key), self.vote_key)

        # Place progress label in grid
        row = 0
        self.progress_label.grid(row=row, column=self.n_labels, sticky='we')

        # Place buttons in grid
        row += 1
        for ll, button in enumerate(self.buttons):
            button.grid(row=row, column=ll, sticky='we')
            #frame.grid_columnconfigure(ll, weight=1)
        # Place the image in grid
        row += 1
        self.image_panel.grid(row=row, column=0, columnspan=self.n_labels+1, sticky='we')

    def _update_text_display(self, message=None):
        # Add progress label
        if isinstance(self.records[self.index]['label'], str):
            # progress_string = "%d/%d" % (self.index, self.n_paths)
            progress_string = '{}/{} ({})'.format(self.index+1, self.n_records, self.records[self.index]['label'])
        else:
            # progress_string = "%d/%d" % (self.index, self.n_paths)
            progress_string = '{}/{}'.format(self.index+1, self.n_records)
        if isinstance(message, str):
            progress_string = message + ' ' + progress_string
        self.progress_label.configure(text=progress_string)

    def _go_to_index(self, index):
        message = None
        if index >= self.n_records:
            self.index = self.n_records - 1
            message = "Cannot go past last image"
        elif index < 0:
            self.index = 0
            message = "Cannot go before first image"
        else:
            self.index = index
        self._update_text_display(message=message)
        # self.set_image(self.paths[self.index])
        self.set_image(self.records[self.index]['path'])
        # if self.index < self.n_paths:
        #     self.set_image(self.paths[self.index])
        # else:
        #     self.master.quit()

    def show_next_image(self):
        """
        Displays the next image in the paths list and updates the progress display
        """
        index = self.index + 1
        self._go_to_index(index)

    def show_prev_image(self):
        """
        Displays the next image in the paths list and updates the progress display
        """
        index = self.index - 1
        self._go_to_index(index)

    def go_to_unlabeled(self):
        """
        Displays the first unlabeled image in the paths list.
        """
        index = 0
        while self.records[index]['label'] is not None:
            index += 1
            if index >= self.n_records:
                break
        self._go_to_index(index)

    def set_image(self, path):
        """
        Helper function which sets a new image in the image view
        :param path: path to that image
        """
        image = self._load_image(path)
        self.image_raw = image
        self.image = ImageTk.PhotoImage(image)
        self.image_panel.configure(image=self.image)

    def vote(self, label):
        """
        Processes a vote for a label: Initiates the file copying and shows the next image
        :param label: The label that the user voted for
        """
        # input_path = self.paths[self.index]
        input_path = self.records[self.index]['path']
        print('[DEBUG] Button label: "{}"'.format(label))
        self.records[self.index]['label'] = label
        # print(self.records[self.index])
        self._copy_image(input_path, self.destination, label)
        self._write_data(self.records, self.data_path)
        self.show_next_image()

    def vote_key(self, event):
        """
        Processes voting via the number key bindings.
        :param event: The event contains information about which key was pressed
        """
        pressed_key = int(event.char)
        label = self.labels[pressed_key-1]
        self.vote(label)

    @staticmethod
    def _load_image(path, size=(800,600)):
        """
        Loads and resizes an image from a given path using the Pillow library
        :param path: Path to image
        :param size: Size of display image
        :return: Resized image
        """
        image = Image.open(path)
        # image = image.resize(size, Image.ANTIALIAS)
        # From image-sorter2:
        max_height = 500
        img = image 
        s = img.size
        ratio = max_height / s[1]
        image = img.resize((int(s[0]*ratio), int(s[1]*ratio)), Image.ANTIALIAS)
        return image

    @staticmethod
    def _copy_image(input_path, destination, label):
        """
        Copies a file to a new label folder using the shutil library. The file will be copied into a
        subdirectory called label in the input folder.
        :param input_path: Path of the original image
        :param label: The label
        """
        _, file_name = os.path.split(input_path)
        # output_path = os.path.join(dirname, label, file_name)
        output_folder = os.path.join(destination, label)
        output_path = os.path.join(output_folder, file_name)
        os.makedirs(output_folder, exist_ok=True)
        # print(" %s --> %s" % (file_name, label))
        print(" %s -> %s" % (input_path, output_path))
        shutil.copyfile(input_path, output_path)

    # @staticmethod
    # def _move_image(input_path, destination, label):
    #     """
    #     Moves a file to a new label folder using the shutil library. The file will be moved into a
    #     subdirectory called label in the input folder. This is an alternative to _copy_image, which is not
    #     yet used, function would need to be replaced above.
    #     :param input_path: Path of the original image
    #     :param label: The label
    #     """
    #     _, file_name = os.path.split(input_path)
    #     # output_path = os.path.join(dirname, label, file_name)
    #     output_folder = os.path.join(destination, label)
    #     output_path = os.path.join(output_folder, file_name)
    #     os.makedirs(output_folder, exist_ok=True)
    #     # print(" %s --> %s" % (file_name, label))
    #     print(" %s -> %s" % (input_path, output_path))
    #     shutil.move(input_path, output_path)

    def _write_data(self, records, path):
        """
        Moves a file to a new label folder using the shutil library. The file will be moved into a
        subdirectory called label in the input folder. This is an alternative to _copy_image, which is not
        yet used, function would need to be replaced above.
        :param input_path: Path of the original image
        :param label: The label
        """
        # _, file_name = os.path.split(input_path)
        # # output_path = os.path.join(dirname, label, file_name)
        # output_folder = os.path.join(destination, label)
        # output_path = os.path.join(output_folder, file_name)
        # os.makedirs(output_folder, exist_ok=True)
        # # print(" %s --> %s" % (file_name, label))
        # print(" %s -> %s" % (input_path, output_path))
        # shutil.move(input_path, output_path)
        print(json.dumps(records[self.index], indent=2))
        with open(path, 'w') as f:
            json.dump(records, f, indent=2, sort_keys=True)


# def make_folder(directory):
#     """
#     Make folder if it doesn't already exist
#     :param directory: The folder destination path
#     """
#     if not os.path.exists(directory):
#         os.makedirs(directory)

def find_images(dirname):
    '''
    Put all image file paths into a list
    '''
    image_paths = []
    for path in glob.glob(os.path.join(dirname, '**'), recursive=True):
        _, ext = os.path.splitext(path)
        if os.path.isdir(path):
            continue
        elif ext.lower() in IMAGE_EXTENSIONS:
            image_paths.append(path)
        else:
            pass
    return image_paths

def init_records(image_paths):
    '''
    Initialize records with image paths and empty labels.
    '''
    records = dict()
    for i, path in enumerate(image_paths):
        records[i] = {'path': path, 'label': None}
    return records

def load_records(path):
    '''
    Load records from json file.
    '''
    with open(path, 'r') as f:
        records = json.load(f)
    # Convert keys to ints.
    records = {int(k): v for k, v in records.items()}
    return records

def main():

    # Make input arguments
    parser = argparse.ArgumentParser()

    parser.add_argument('-l', '--labels', nargs='+', help='Possible labels in the images', required=True)
    parser.add_argument('-o', '--output-folder', help='Copy images to <output-folder>/<label>', required=False, default='sorted')

    # [TODO] Mutually exclusive group:
    parser.add_argument('--images', nargs='*', required=False)
    parser.add_argument('-f', '--input-folder', help='Find images in this directory.', required=False)
    parser.add_argument('-d', '--data', help='Path to data.json. (Continue from where you left off.)', required=False)

    args = parser.parse_args()
    print(args)

    # grab input arguments from args structure
    # input_folder = args.folder
    labels = args.labels
    output_folder = args.output_folder

    if isinstance(args.images, list):
        image_paths = args.images
        records = init_records(image_paths)
    elif isinstance(args.input_folder, str):
        # Put all image file paths into a list
        image_paths = find_images(args.input_folder)
        records = init_records(image_paths)
    elif isinstance(args.data, str):
        records = load_records(args.data)
        image_paths = [rec['path'] for rec in records.values() if os.path.exists(rec['path'])]
    # print(*image_paths, sep='\n')

    if not image_paths:
        print('[ERROR] No images found.')
        return 1

    # Start the GUI
    master = tk.Tk()
    app = ImageGui(master, labels, records, output_folder)
    master.mainloop()

    return 0


if __name__ == "__main__":
    res = main()
    sys.exit(res)

# END.
