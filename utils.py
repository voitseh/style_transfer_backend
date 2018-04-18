# Copyright (c) 2016-2017 Shafeen Tejani. Released under GPLv3.
from os.path import exists
from PIL import Image
import PIL.Image
import os
import uuid
import base64
import numpy as np
import scipy
import scipy.misc


def load_image(image_path, img_size=None):
    assert exists(image_path), "image {} does not exist".format(image_path)
    img = scipy.misc.imread(image_path)
    if (len(img.shape) != 3) or (img.shape[2] != 3):   
        img = np.dstack((img, img, img))

    if (img_size is not None):
        img = scipy.misc.imresize(img, img_size)

    img = img.astype("float32")
    return img

def get_files(img_dir):
    files = list_files(img_dir)
    return map(lambda x: os.path.join(img_dir,x), files)

def list_files(in_path):
    files = []
    for (dirpath, dirnames, filenames) in os.walk(in_path):
        files.extend(filenames)
        break

    return files

def get_filename():
    filename = os.path.join('stylized-', str(uuid.uuid4())+ '{}'.format('.jpg'))
    return filename

def write_file(f_name, file):
    with open(f_name, 'wb') as f:
        f.write(file)
    
def make_thumbnail(filename):
    thumbnail_size = (300,300)
    im = Image.open(filename)
    im.thumbnail(thumbnail_size,  Image.ANTIALIAS)
    im.save(filename)

def decode_img(b64file, f_name):
    if ',' in b64file:
        imgdata = b64file.split(',')[1]
        decoded = base64.b64decode(imgdata)
        write_file(f_name, decoded)

def encode_img(filename):
    with open(filename, "rb") as image_file:
        return to_base64(image_file.read())
    
def to_base64(img):
    return base64.b64encode(img)

def process_base64(base64_str):
    base64_str = str(base64_str).split("b'")[-1].split("b'")[-1][:-1]
    return add_charakters_to_base64_str(base64_str)

def add_charakters_to_base64_str(base64_str, styles_gallery=True):
    return 'data:image/png;base64,{}{}'.format(base64_str,'=') if base64_str.endswith('=') and styles_gallery else  'data:image/png;base64,{}'.format(base64_str)

def png_to_3channels(filename):
    image = PIL.Image.open(filename)
    im = image.convert("RGB")
    im.save(filename)