"""
@author: Dave Sierra
@title: Web API Suite
@Nickname: Web API Suite
@description: This extension offers various nodes that work within a web api context.
"""

from pathlib import Path
from uuid import uuid4
import torch
from folder_paths import get_input_directory, get_output_directory
from PIL import Image, ImageOps
import urllib.request
import numpy as np
import os

import json
from PIL.PngImagePlugin import PngInfo
from comfy.cli_args import args
import folder_paths
import requests

import re



def find_in_prompt(prompt, class_type, target):
    for key in prompt:
        # print(key, "->", prompt[key])
        if prompt[key]['class_type'] == class_type:
            print(f'found {class_type} on key {key}')
            print(f'{class_type} {target} is {prompt[key]["inputs"][target]}')
            return prompt[key]["inputs"][target]

def find_title_in_prompt(prompt, title):
    for key in prompt:
        # print(key, "->", prompt[key])
        if prompt[key]['_meta']['title'] == title:
            print(f'found {title} on key {key}')
            return prompt[key]

def get_string_from_title(title):
    return title['inputs']['string']

def find_object_by_title(prompt, title):
    for key in prompt:
        # print(key, "->", prompt[key])
        if prompt[key]['_meta']['title'] == title:
            print(f'found {title} on key {key}')
            return prompt[key]

def find_many_between(s, first, last):
    try:
        regex = rf'{first}(.*?){last}'
        return re.findall(regex, s)
    except ValueError:
        return -1
           
def replace_all_text(prompt, text):
    try:
        # get the original text
        print(f'prompt to use {prompt}')
        # text = find_in_prompt(prompt, 'DynamicText', 'text')
        print(f'text to replace {text}')
        # get the x amount of instances of words between % and %
        instances = find_many_between(text, "%", "%")
        
        for key in instances:
            print(f'key {key}')
            # find the node with the same title and grab its value
            object = find_object_by_title(prompt, key)
            title = object['inputs']['string']
            print(f'title {title}')
            text = text.replace(f'%{key}%', title)
            
        return text
    except ValueError:
        return -1

class Base():
    OUTPUT_NODE = True
    FUNCTION = "func"
    CATEGORY = "everywhere"
    RETURN_TYPES = ()

# class SimpleStringBoxTrue(Base):
#     OUTPUT_NODE = False
#     @classmethod
#     def INPUT_TYPES(s):
#         return {"required":{ "string": ("STRING", {"default": "",
#                                                    "multiline": True
#                                                    }) }}
#     RETURN_TYPES = ("STRING",)

#     def func(self,string):
#         return (string,)

     
class WINDynamicText:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING",{"multiline": True}),
            },
            "optional": {
                "text_a": ("STRING", {"forceInput": True}),
                "text_b": ("STRING", {"forceInput": True}),
                "text_c": ("STRING", {"forceInput": True}),
                "text_d": ("STRING", {"forceInput": True}),
            },
            "hidden": {
                "prompt": "PROMPT",
            },
        }
    RETURN_TYPES = ("STRING",)
    FUNCTION = "text_replace"

    CATEGORY = "text"

    def text_replace(self, prompt=None, text='', text_a='', text_b='', text_c='', text_d=''):
        print(f'text: {text}')      
        final_res = replace_all_text(prompt, text)
        return (final_res, )
    
class WINDynamicPrompt:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True}), 
                "clip": ("CLIP", )
            },
            "optional": {
                "text_a": ("STRING", {"forceInput": True}),
                "text_b": ("STRING", {"forceInput": True}),
                "text_c": ("STRING", {"forceInput": True}),
                "text_d": ("STRING", {"forceInput": True}),
            },
            "hidden": {
                "prompt": "PROMPT",
            },
        }
    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "text_replace"

    CATEGORY = "conditioning"

    def text_replace(self, clip, prompt=None, text='', text_a='', text_b='', text_c='', text_d=''):
        print(f'text: {text}')
        print(f'self: {self}')
        final_res = replace_all_text(prompt, text)
        print(f'final_res: {final_res}')
        tokens = clip.tokenize(final_res)
        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        return ([[cond, {"pooled_output": pooled}]], )


class LoadImageURL:
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "url": ("STRING", {"default": ''}),
                "save_name": ("STRING", {"default": 'ComfyUI'}),
                "save_format": (["jpg", "png"], {"default": "png"}),
                "input_dir": ("STRING", {"default": get_input_directory()}),
                "keep": ([False, True], {"default": False}),
            }
        }

    CATEGORY = "image"
    FUNCTION = "load_images"
    # OUTPUT_NODE = False
    RETURN_TYPES = ("IMAGE",)

    def load_images(self, url, input_dir, keep, save_format,save_name="ComfyUI"):
        input_dir = Path(input_dir)
        input_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"{save_name}-{uuid4().hex[:16]}.{save_format}"
        image_path = input_dir / file_name

        # This statement requests the resource at 
        # the given link, extracts its contents 
        # and saves it in a variable 
        data = requests.get(url).content 
        # res = requests.get(url, stream = True)        

        # Opening a new file named img with extension .jpg 
        # This file would store the data of the image file 
        f = open(image_path,'wb')
        # Storing the image data inside the data variable to the file 
        f.write(data) 
        f.close() 

        # request the image from the web, and save it into the input_dir
        # urllib.request.urlretrieve(url, image_path) //did not work with certain image providers, ie: cloudflare

        # Grabbed from ComfyUI/nodes.py -> load_image
        i = Image.open(image_path)
        i = ImageOps.exif_transpose(i)
        image = i.convert("RGB")
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None,]

        if keep == False:
            try:
                os.remove(image_path)
            except OSError:
                pass

        return (image,)


class SaveImageURL:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "url": ("STRING", {"default": "https://ny.bunnycdn.com/image-store/test.jpg"}),
                "presign_key": ("STRING", {"default": ""}),
                # "presign_step": (["false", "true"],),
                "method": ("STRING", {"default": "post"}),
                "headers": ("STRING", {"default": '{"foo" : 1, "bar" : 2, "baz" : 3}'}),
                "callback_api": ("STRING", {"default": "http://localhost:3000/api/prompts"})
            },
            "hidden": {
                "prompt": "PROMPT", 
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"

    OUTPUT_NODE = True

    CATEGORY = "image"

    def save_images(self, images, url, method, presign_key, callback_api,  headers='{}', filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None,presign_step="false"):
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        results = list()
        #this will be the output, whether a successful response, or error message
        message = ''

        print(f'filename_prefix: {filename_prefix}')
        print(f'full_output_folder: {full_output_folder}')

        print("The original headers: ", headers)
        # printing original string
        print("The original string for headers: ", str(headers))
        
        # using json.loads()
        # convert dictionary string to dictionary
            
        req_headers = json.loads(headers)

        # req_headers = headers
        
        # print result
        print("The converted req_headers: ", str(req_headers))

        def send_response_to_callback_api(self, prompt, extra_pnginfo, callback_api):
            # callback_api
            print(f'callback_api: {callback_api}')
        
        def process_request(method, url, **kwargs):
            print(f"process_request begin")
            print(f"process_request kwargs", kwargs)
            response = requests.request(method, url, **kwargs)
            print(f"process_request end {response.content}")
            return response

        def get_seed_by_class_type(prompt, class_type='KSampler'):
            seed = None
            for key in prompt:
                print(key, "->", prompt[key])
                if prompt[key]['class_type'] == class_type:
                    print(f'found KSampler on key {key}')
                    print(f'{class_type} seed is {prompt[key]["inputs"]["seed"]}')
                    seed = prompt[key]["inputs"]["seed"]
            return seed
        
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            file = f"{filename}_{counter:05}_.png"
            print(f'file: {file}')

            # print(f'prompt: {prompt}')
            
            img.save(os.path.join(full_output_folder, file), pnginfo=metadata, compress_level=self.compress_level)
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })
            counter += 1
            
            print(f'counter: {counter}')
            file_path = os.path.join(full_output_folder, file)
            file_data = open(file_path, "rb")

            # seed = get_seed_by_class_type(prompt)
            # print(f'seed: {seed}')

            try:
                if presign_key == "":
                    response = process_request(method, url, files = {"file": file_data}, headers=req_headers)
                else:
                    print(f'Presigning first {method} {url} {headers}')
                    presigned_response = process_request(method, url, headers=req_headers)
                    print(f'Presigning presigned_response {presigned_response}')
                    presigned_url_json = presigned_response.json()
                    print(f'full presigned_url_json: {presigned_url_json}')
                    presigned_url = presigned_url_json[presign_key]
                    response = process_request(method, presigned_url, files = {"file": file_data}, headers=req_headers)
                    print(f'Upload response text: {response.text}')

                if callback_api != "":
                    print(f'callback_api: {callback_api}')
                    # send_response_to_callback_api(self, prompt, extra_pnginfo, callback_api)
                    process_request(method, callback_api, data=response.text, headers=req_headers)

                response.raise_for_status()
                print(f'response code: ', response.status_code)
                print(f'response text: ', response.text)
            except requests.exceptions.HTTPError as errh:
                print ("Http Error:",errh)
            except requests.exceptions.ConnectionError as errc:
                print ("Error Connecting:",errc)
            except requests.exceptions.Timeout as errt:
                print ("Timeout Error:",errt)
            except requests.exceptions.RequestException as err:
                print ("OOps: Something Else",err)

            # send_file = open(file_path, "rb")
            # if method == "post":
            #     # response = requests.post(url, files = {"file": send_file})
            #     with open(file_path, 'rb') as file_data:
            #         response = requests.post(url, headers=dict_headers, data=file_data)
            # else:
            #     with open(file_path, 'rb') as file_data:
            #         # response = requests.put(url, headers=dict_headers, data=file_data)
            #         try:
            #             response = requests.put(url, headers=dict_headers, data=file_data)
            #         except requests.exceptions.RequestException as e:  # This is the correct syntax
            #             raise SystemExit(e)
                # response = requests.put(url, files = {"file": send_file})
            
            

            # if response.ok:
            #     print("Upload completed successfully!")
            #     # print(test_response.text)
            # else:
            #     print("Something went wrong!")

        return { "ui": { "images": results } }

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "LoadImageURL": LoadImageURL,
    "SaveImageURL": SaveImageURL,
    "WINDynamicPrompt": WINDynamicPrompt,
    "WINDynamicText": WINDynamicText,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageURL": "Load Image from URL",
    "SaveImageURL": "Save Image to URL",
    "WINDynamicPrompt": "Dynamic Prompt",
    "WINDynamicText": "Dynamic Text",
    
}
