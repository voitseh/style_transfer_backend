from flask import Flask, g, url_for
from os.path import exists
from flask_cors import CORS
from flask import render_template
from gevent.wsgi import WSGIServer
from PIL import Image
import flask_sijax
import os, glob
import  base64 
import numpy as np
import PIL.Image
import stylize_image
import utils


# The path where you want the extension to create the needed javascript files
# DON'T put any of your files in this directory, because they'll be deleted!
path = os.path.join('.', os.path.dirname(__file__), 'static/js/sijax/')
app = Flask(__name__)
CORS(app)
app.config['SIJAX_STATIC_PATH'] = path
# You need to point Sijax to the json2.js library if you want to support
# browsers that don't support JSON natively (like IE <= 7)
app.config['SIJAX_JSON_URI'] = '/static/js/sijax/json2.js'
flask_sijax.Sijax(app)

UPLOAD_FOLDER = os.path.join(app.root_path, 'static/images')
STYLES_FOLDER = os.path.join(UPLOAD_FOLDER, 'style_gallery')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024


class StylesGallery:

    __gallery_id = 'style_gallery'

    def __init__(self, obj_response):
        global STYLES_FOLDER
        self.__obj_response = obj_response
  
    def add_new_style(self,filename, base64_img):
        style_path =  os.path.join(STYLES_FOLDER, filename)
        utils.decode_img(base64_img, style_path)
        utils.make_thumbnail(style_path)
    
    def delete_style(self, filename):
        style_path = os.path.join(STYLES_FOLDER,filename)
        assert exists(style_path), "Style you want delete not found!"
        os.remove(style_path)
    
    def check_styles_folder_exists(self):
        assert exists(STYLES_FOLDER), "STYLES_FOLDER not found!"

    def reload_gallery_imgs(self):
        self.__remove_gallery_imgs()
        self.__load_gallery_imgs()
    
    def __remove_gallery_imgs(self):
        self.__obj_response.script("$('#%s').children().remove()"%(self.__gallery_id));
    
    def __load_gallery_imgs(self):
        self.__id_index = 0 
        for filename in glob.glob(os.path.join( STYLES_FOLDER, "*.*")):
            self.__response_style_img_to_gallery(filename)
  
    def __response_style_img_to_gallery(self, img_path):
        img_name, img_base64, img_id, img_delete_bttn_id = self.__get_style_img_attributes(img_path)
        self.__obj_response.script("$('#%s').append($('<li>',{class:'image_grid'}).append($('<a href=#>').append($('<label>').append($('<img>',{id:'%s', src:'%s', name:'%s'})).append($('<input>',{type:'radio', name:'selimg'})).append($('<span>',{class:'caption'})).append($('<span>',{id:'%s'})))));"%(self.__gallery_id, img_id, img_base64, img_name, img_delete_bttn_id))
     
    def __get_style_img_attributes(self, img_path):
        img_name = img_path.split('/')[-1]
        img_base64 = self.__make_base64_encoded_string(img_path)
        img_id = '_img{}'.format(str(self.__id_index))
        img_delete_bttn_id = 'del_style{}'.format(str(self.__id_index)) 
        self.__id_index += 1
        return img_name, img_base64, img_id, img_delete_bttn_id
    
    def __make_base64_encoded_string(self, img_path):
        encoded_img = utils.encode_img(img_path)
        return utils.process_base64(encoded_img)

    


class ContentImageProcessor:
    
    def __init__(self, encoded_content_img):
        global UPLOAD_FOLDER
        self.__content_img_path = os.path.join(UPLOAD_FOLDER, 'photo_image.jpg')
        self.__encoded_content_img = encoded_content_img
    
    def get_content_img_path(self):
        return self.__content_img_path
    
    def process_content_img(self):
        self.__decode_content_img()
        self.__convert_content_img_to_3_channels()

    def __decode_content_img(self):
        return utils.decode_img(self.__encoded_content_img, self.__content_img_path)
        
    def __convert_content_img_to_3_channels(self):
        return utils.png_to_3channels(self.__content_img_path)
        

class ServerResponder():

    def __init__(self, obj_response):
        self.__obj_response = obj_response
    
    def send_message(self, message_type):
        self.__obj_response.html("#server_response", message_type)

    def send_image(self, img_base64):
        img_name, img_base64 = self.__get_img_attributes(img_base64)
        self.__obj_response.script("$('#%s').append($('<img>',{ style:'position:absolute; left:0px; top:0px; z-index: 2',id:'%s',name:'%s',src:'%s'}));"%('card_result', 'stylized_img', img_name, img_base64))
    
    def __get_img_attributes(self, img_base64):
        img_name = utils.get_filename()
        img_base64 = utils.add_charakters_to_base64_str(img_base64, False)
        return img_name, img_base64
    
class ImageStylizer:
    
    def __init__(self, content_path, network_path):
        self.__content = content_path
        self.__network = network_path
        
    def stylize_image(self):
        return stylize_image.main(self.__content, self.__network)
       

@flask_sijax.route(app, "/")
def index():
    if g.sijax.is_sijax_request:
        # Sijax request detected - let Sijax handle it
        g.sijax.register_callback('client_data', Dispatcher().dispatch) 
        # The request looks like a valid Sijax request
        # The handlers are already registered above.. we can process the request
        return g.sijax.process_request()
    return render_template(index.html)

"""A container class for all Sijax handlers.
    Grouping all Sijax handler functions in a class
    (or a Python module) allows them all to be registered with
    a single line of code.
"""
class Dispatcher(object):

    __CONTENT = ''
    __NETWORK = ''

    __obj_response = ''
    __client_data = ''
    
    __initial_message = 'Stylize..'
    __cleared_massage = ''

    __styles_gallery = None
    __server_responder = None
   
    def dispatch(self, obj_response, client_data):

        self.__obj_response = obj_response
        self.__client_data = client_data
        
        self.__make_instances()
        
        self.__styles_gallery.check_styles_folder_exists()
        
        if   'message' in self.__client_data: 
            self.__response_stylize_message(self.__initial_message),
        if   'data' in self.__client_data: 
            self.__apply_style(),
        if   'delGalleryImg' in self.__client_data: 
            self.__delete_stylesgallery_img(),
        if   'styleFile' in self.__client_data:  
            self.__add_stylegallery_img(),
        if   'style_gallery' in self.__client_data: 
            self.__reload_stylesgallery()
        
    def __make_instances(self):
        self.__styles_gallery = StylesGallery(self.__obj_response)
        self.__server_responder = ServerResponder(self.__obj_response)

    def __response_stylize_message(self, text):
        self.__server_responder.send_message(text)

    def __apply_style(self):
        self.__set_stylize_params()
        self.__response_stylized_img()
        self.__response_stylize_message(self.__cleared_massage)

    def __set_stylize_params(self):
        self.__CONTENT = self.__process_content_img()
        self.__NETWORK = self.__get_network_path()

    def __process_content_img(self):
        content_processor = ContentImageProcessor(self.__client_data['data'][1])
        content_processor.process_content_img()
        return content_processor.get_content_img_path()
   
    def __get_network_path(self):
        return os.path.join(app.root_path, "pretrained-networks/{}".format(self.__get_selected_style()))
 
    def __get_selected_style(self):
        return self.__client_data['data'][2].split('.')[0] 

    def __response_stylized_img(self):
        self.__server_responder.send_image(self.__get_stylized_img())
                
    def __get_stylized_img(self):
        stylizer = ImageStylizer(self.__CONTENT, self.__NETWORK)
        return stylizer.stylize_image()
       
    
    
    def __delete_stylegallery_img(self):
        self.__styles_gallery.delete_style(self.__client_data['delGalleryImg'])


    def __add_stylesgallery_img(self):
        self.__styles_gallery.add_new_style(client_data['styleFile'][0], client_data['styleFile'][1])
        self.__reload_stylesgallery()

    
    def __reload_stylesgallery(self):
        self.__styles_gallery.reload_gallery_imgs()


if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=63101, debug=True)
    http_server = WSGIServer(('', 63101), app)
    http_server.serve_forever()
    

