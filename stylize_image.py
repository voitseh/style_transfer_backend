# Copyright (c) 2016-2017 Shafeen Tejani. Released under GPLv3.
from PIL import Image
from io import BytesIO
from os.path import exists
from sys import stdout
import os
import numpy as np
import utils
import tensorflow as tf
import transform

CONTENT_PATH=''
NETWORK_PATH=''

def check_opts():
    assert exists(CONTENT_PATH), "content not found!"
    assert exists(NETWORK_PATH), "network not found!"

def main(content_path, network_path):
    global CONTENT_PATH, NETWORK_PATH
    CONTENT_PATH = content_path
    NETWORK_PATH = network_path
   
    check_opts()
    
    content_image = utils.load_image(CONTENT_PATH)
    reshaped_content_height = (content_image.shape[0] - content_image.shape[0] % 4)
    reshaped_content_width = (content_image.shape[1] - content_image.shape[1] % 4)
    reshaped_content_image = content_image[:reshaped_content_height, :reshaped_content_width, :]
    reshaped_content_image = np.ndarray.reshape(reshaped_content_image, (1,) + reshaped_content_image.shape)

    prediction = ffwd(reshaped_content_image, NETWORK_PATH)
    img = Image.fromarray(np.clip(prediction, 0, 255).astype(np.uint8), 'RGB')
    buffer = BytesIO()
    img.save(buffer,format="JPEG") 
    myimage = buffer.getvalue()    
    return utils.to_base64(myimage)
    


def ffwd(content, network_path):
    tf.reset_default_graph()
    with tf.Session() as sess:
        img_placeholder = tf.placeholder(tf.float32, shape=content.shape,
                                         name='img_placeholder')

        network = transform.net(img_placeholder)
        saver = tf.train.Saver()

        ckpt = tf.train.get_checkpoint_state(network_path)

        if ckpt and ckpt.model_checkpoint_path:
            saver.restore(sess, ckpt.model_checkpoint_path)
        else:
            raise Exception("No checkpoint found...")

        prediction = sess.run(network, feed_dict={img_placeholder:content})
        return prediction[0]
