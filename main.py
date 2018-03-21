from flask import Flask, g, url_for
from flask_cors import CORS
from flask import render_template
from gevent.wsgi import WSGIServer
from PIL import Image
import flask_sijax
import os, glob
import  base64 
import numpy as np
import logging
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

gallery_ID = ""

#################### PROCESS IMAGE ###############################
def decode_img(b64file, f_name):
    if ',' in b64file:
        imgdata = b64file.split(',')[1]
        decoded = base64.b64decode(imgdata)

        utils.write_file(f_name, decoded)
    
      

def make_thumbnail(filename):
    thumbnail_size = (300,300)
    im = Image.open(filename)
    im.thumbnail(thumbnail_size,  Image.ANTIALIAS)
    im.save(filename)

def encode_img(filename):
    with open(filename, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    return encoded_string

def process_base64(filename):
    filename = str(filename).split("b'")[-1].split("b'")[-1][:-1]
    filename = 'data:image/png;base64,{}{}'.format(filename,'=') if filename.endswith('=') else  'data:image/png;base64,{}'.format(filename)
   
    return filename

#################### FOR STYLIZED IMAGE ###############################

def remove_img(obj_response, img_id):
    obj_response.script("$('#%s').remove()"%(img_id));

def show_img(obj_response, parent_id, img_id, new_img, img_name):
    # process base64 image to be readeble in browser
    new_img = process_base64(new_img)
    obj_response.script("$('#%s').append($('<img>',{ style:'position:absolute; left:0px; top:0px; z-index: 2',id:'%s',src:'%s', name:'%s'}));"%(parent_id, img_id, new_img, img_name))
 
def change_img(obj_response, parent_id, img_id, new_img, img_name):
    #remove previous image from gallery
    if img_id != None:
        remove_img(obj_response, img_id);
    #send new image to frame
    show_img(obj_response, parent_id, img_id, new_img, img_name)

def response(obj_response, parent_id, img_id, filename):
    new_img = encode_img(filename)
    img_name = filename.split('/')[-1]
    change_img(obj_response, parent_id, img_id, new_img, img_name)
    
###################### STYLES GALLERY ##############################

def remove_gallery_imgs(obj_response, parent_id):
    obj_response.script("$('#%s').children().remove()"%(parent_id));

def show_gallery_img(obj_response, parent_id, img_id, new_img, del_id):
    img_name = new_img.split('style_gallery/')[-1]  
    file_address = UPLOAD_FOLDER + new_img.split('images')[-1]
    new_img = encode_img(file_address)
    new_img = process_base64(new_img)
    obj_response.script("$('#%s').append($('<li>',{class:'image_grid'}).append($('<a href=#>').append($('<label>').append($('<img>',{id:'%s', src:'%s', name:'%s'})).append($('<input>',{type:'radio', name:'selimg'})).append($('<span>',{class:'caption'})).append($('<span>',{id:'%s'})))));"%(parent_id, img_id, new_img, img_name, del_id))
   
def response_to_gallery(obj_response, parent_id, img_id, filename, del_id):
    filename = filename.split('/')[-1]
    result = url_for('static', filename='images/{}/{}'.format(parent_id,filename))
    show_gallery_img(obj_response, parent_id, img_id, result, del_id) 

def fill_gallery(obj_response, src_dir, gallery_ID):
    index = 0
    remove_gallery_imgs(obj_response, gallery_ID)
    if os.path.exists(src_dir):
        for filename in glob.glob(os.path.join( src_dir, "*.*")):
            img_id = '_img{}'.format(str(index))
            del_id = 'del_style{}'.format(str(index)) 
            index += 1
            #senf new image to frame
            response_to_gallery(obj_response, gallery_ID, img_id, filename, del_id) 
    else: 
         print("{} is not exist!".format(src_dir))

class SijaxHandler(object):
    
    """A container class for all Sijax handlers.
    Grouping all Sijax handler functions in a class
    (or a Python module) allows them all to be registered with
    a single line of code.
    """
    @staticmethod
    def client_data(obj_response, client_data):
      
        selected_style = ''
       
        if  'message' in client_data:
            obj_response.html("#server_response", "Stylize..")
    
        if  'data' in client_data:
            filename =  os.path.join(UPLOAD_FOLDER, 'photo_image.jpg')

            decode_img(client_data['data'][1], filename)
            
            #make 3 channels for png image
            image = PIL.Image.open(filename)
            im = image.convert("RGB")
            im.save(filename)
            
            selected_style = client_data['data'][2].split('.')[0]
            if client_data['data'][1] != '' and client_data['data'][3] != '':
                content = os.path.join(UPLOAD_FOLDER, filename )
                network = os.path.join(app.root_path, "pretrained-networks/{}".format(selected_style))
                output = utils.rename_file(UPLOAD_FOLDER,'styled-', 'jpg')
                
                try:
                    os.system("python {} {} {} {} {} {} {}".format(os.path.join(app.root_path, "stylize_image.py "),"--content ",content," --network-path ", network," --output-path ",output))
                    response(obj_response, 'border_result', 'stylized_img', output)
                    utils.remove_file(client_data['data'][0], UPLOAD_FOLDER)
                    utils.remove_file(output, UPLOAD_FOLDER)
                    obj_response.html('#server_response',  "")
                except Exception as e:
                    logging.exception("%s" % e)
                    obj_response.html('#server_response',  "%s" % e)
                    #obj_response.html('#server_response',  "Mistake!")

        # handle deleted styles gallery image
        if  'delGalleryImg' in client_data:
            filename = client_data['delGalleryImg']
            utils.remove_file(filename, STYLES_FOLDER) 
        
        # Fill styles gallery
        if  'style_gallery' in client_data:
            fill_gallery(obj_response, STYLES_FOLDER, client_data['style_gallery'])
           
        ############## styles gallery ###############################
        # handle loading new style file to send it into styles gallery
        if 'styleFile' in client_data:
            f_name =  os.path.join(STYLES_FOLDER, client_data['styleFile'][0])
            decode_img(client_data['styleFile'][1], f_name)
            make_thumbnail(f_name)
            fill_gallery(obj_response, STYLES_FOLDER, 'style_gallery')

@flask_sijax.route(app, "/")
def index():
    if g.sijax.is_sijax_request:
        # Sijax request detected - let Sijax handle it
        g.sijax.register_callback('client_data', SijaxHandler.client_data) 
        # The request looks like a valid Sijax request
        # The handlers are already registered above.. we can process the request
        return g.sijax.process_request()
    return render_template(index.html)
        
if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=63101, debug=True)
    http_server = WSGIServer(('', 63101), app)
    http_server.serve_forever()
    

