import datetime
import fileinput
import os
import platform
import re
import shutil
import sys
import io
import time
import typing as t
import gzip
import git
import gradio as gr
import requests
from bs4 import BeautifulSoup
import subprocess
import modules
import random
from gpt_index import SimpleDirectoryReader, GPTListIndex, GPTSimpleVectorIndex, LLMPredictor, PromptHelper
import openai
import gc
import json
#import tkinter as tk
#from tkinter import filedialog, ttk
import modules.devices as devices
import torch
from numba import cuda
from modules import shared, sd_hijack, sd_samplers, processing
from modules.sd_models import CheckpointInfo
from scripts.download.msai_downloader_manager import MiaoshouDownloaderManager
from scripts.msai_logging.msai_logger import Logger
from scripts.msai_utils import msai_toolkit as toolkit
from scripts.runtime.msai_prelude import MiaoshouPrelude


class MiaoshouRuntime(object):
    def __init__(self):
        self.cmdline_args: t.List[str] = None
        self.logger = Logger()
        self.prelude = MiaoshouPrelude()
        self._old_additional: str = None
        self._model_set: t.List[t.Dict] = None
        self._my_model_set: t.List[t.Dict] = None
        self._active_model_set: str = None
        self._model_set_last_access_time: datetime.datetime = None
        self._my_model_set_last_access_time: datetime.datetime = None
        self._ds_models: gr.Dataset = None
        self._ds_cover_gallery: gr.Dataset = None
        self._ds_my_models: gr.Dataset = None
        self._ds_my_model_covers: gr.Dataset = None
        self._allow_nsfw: bool = False
        self._model_source: str = "civitai.com"  # civitai is the default model source
        self._my_model_source: str = "civitai.com"
        self._git_address: str = "https://github.com/miaoshouai/miaoshouai-assistant.git"

        # TODO: may be owned by downloader class
        self.model_files = []

        self.downloader_manager = MiaoshouDownloaderManager()


    def get_default_args(self, commandline_args: t.List[str] = None):
        if commandline_args is None:
            commandline_args: t.List[str] = toolkit.get_args(sys.argv[1:])
        commandline_args = list(map(lambda x: x.replace('theme=', 'theme '), commandline_args))
        self.cmdline_args = list(dict.fromkeys(commandline_args))

        self.logger.info(f"default commandline args: {commandline_args}")

        checkbox_values = []
        additional_args = ""
        saved_setting = self.prelude.boot_settings

        gpu = saved_setting.get('drp_args_vram')
        theme = saved_setting.get('drp_args_theme')
        port = saved_setting.get('txt_args_listen_port')

        for arg in commandline_args:
            if 'theme' in arg:
                theme = [k for k, v in self.prelude.theme_setting.items() if v == arg][0]
            if 'port' in arg:
                port = arg.split(' ')[-1]

        for chk in self.prelude.checkboxes:
            for arg in commandline_args:
                if self.prelude.checkboxes[chk] == arg and chk not in checkbox_values:
                    checkbox_values.append(chk)

        gpu_arg_list = [f'--{i.strip()}' for i in ' '.join(list(self.prelude.gpu_setting.values())).split('--')]
        for arg in commandline_args:
            if 'port' not in arg \
                    and arg not in list(self.prelude.theme_setting.values()) \
                    and arg not in list(self.prelude.checkboxes.values()) \
                    and arg not in gpu_arg_list:
                additional_args += (' ' + rf'{arg}')

        self._old_additional = additional_args
        webui_ver = saved_setting['drp_choose_version']

        return gpu, theme, port, checkbox_values, additional_args.replace('\\', '\\\\').strip(), webui_ver

    def add_arg(self, args: str = "") -> None:
        for arg in args.split('--'):
            if f"--{arg.strip()}" not in self.cmdline_args and arg.strip() != '':
                self.logger.info(f'add arg: {arg.strip()}')
                self.cmdline_args.append(f'--{arg.strip()}')

        #remove duplicates
        self.cmdline_args = list(dict.fromkeys(self.cmdline_args))
        #print('added dup',self.cmdline_args)

    def remove_arg(self, args: str = "") -> None:
        arg_keywords = ['port', 'theme']

        for arg in args.split('--'):
            if arg in arg_keywords:
                for cmdl in self.cmdline_args:
                    if arg in cmdl:
                        self.cmdline_args.remove(cmdl)
                        break
            elif f'--{arg.strip()}' in self.cmdline_args and arg.strip() != '':
                self.cmdline_args.remove(f'--{arg.strip()}')

        # remove duplicates
        self.cmdline_args = list(dict.fromkeys(self.cmdline_args))
        #print('removed dup',self.cmdline_args)

    def get_final_args(self, gpu, theme, port, checkgroup, more_args) -> None:
        # remove duplicates
        self.cmdline_args = list(dict.fromkeys(self.cmdline_args))
        # gpu settings
        for s1 in self.prelude.gpu_setting:
            if s1 in gpu:
                for s2 in self.prelude.gpu_setting:
                    if s2 != s1:
                        self.remove_arg(self.prelude.gpu_setting[s2])
                self.add_arg(self.prelude.gpu_setting[s1])

        if port != '7860':
            self.add_arg(f'--port {port}')
        else:
            self.remove_arg('--port')

        # theme settings
        self.remove_arg('--theme')
        for t in self.prelude.theme_setting:
            if t == theme:
                self.add_arg(self.prelude.theme_setting[t])
                break

        # check box settings
        for chked in checkgroup:
            self.logger.info(f'checked:{self.prelude.checkboxes[chked]}')
            self.add_arg(self.prelude.checkboxes[chked])

        for unchk in list(set(list(self.prelude.checkboxes.keys())) - set(checkgroup)):
            print(f'unchecked:{unchk}')
            self.remove_arg(self.prelude.checkboxes[unchk])

        # additional commandline settings
        self.remove_arg(self._old_additional)
        self.add_arg(more_args.replace('\\\\', '\\'))
        self._old_additional = more_args.replace('\\\\', '\\')

    def refresh_all_models(self) -> None:
        self.install_preset_models_if_needed(True)
        if self.ds_models:
            self.ds_models.samples = self.model_set
            self.ds_models.update(samples=self.model_set)
        else:
            self.logger.error(f"ds models is null")

    def get_images_html(self, search: str = '', chk_nsfw: bool = False, model_type: str = 'All') -> t.List[str]:
        self.logger.info(f"get_image_html: model_type = {model_type}, and search pattern = '{search}'")

        model_cover_thumbnails = []
        model_format = []

        if self.model_set is None:
            self.logger.error("model_set is null")
            return []

        self.logger.info(f"{len(self.model_set)} items inside '{self.model_source}'")

        search = search.lower()
        for model in self.model_set:
            try:
                if model.get('type') is not None \
                        and model.get('type') not in model_format:
                    model_format.append(model['type'])

                if search == '' or \
                        (model.get('name') is not None and search.lower() in model.get('name').lower()) \
                        or (model.get('description') is not None and search.lower() in model.get('description').lower()):

                    self._allow_nsfw = chk_nsfw
                    if (model_type == 'All' or model_type in model.get('type')) \
                            and (self.allow_nsfw or (not self.allow_nsfw and not model.get('nsfw'))):
                        model_cover_thumbnails.append([
                            [f"""
                                <div style="display: flex; align-items: center;">
                                    <div id="{str(model.get('id'))}" style="margin-right: 10px;" class="model-item">
                                        <img referrerpolicy="no-referrer" src="{model['modelVersions'][0]['images'][0]['url'].replace('width=450', 'width=100')}" style="width:100px;">
                                    </div>
                                    <div style="flex:1; width:100px;">
                                        <h3 style="text-align:left; word-wrap:break-word;">{model.get('name')}</h3>
                                        <p  style="text-align:left;">Type: {model.get('type')}</p>
                                        <p  style="text-align:left;">Rating: {model.get('stats')['rating']}</p>
                                    </div>
                                </div>
                             """],
                            model['id']])
            except Exception:
                continue

        return model_cover_thumbnails

    # TODO: add typing hint
    def update_boot_settings(self, version, drp_gpu, drp_theme, txt_listen_port, chk_group_args, additional_args):
        boot_settings = self.prelude.boot_settings
        boot_settings['drp_args_vram'] = drp_gpu
        boot_settings["drp_args_theme"] = drp_theme
        boot_settings['txt_args_listen_port'] = txt_listen_port
        for chk in chk_group_args:
            self.logger.debug(chk)
            boot_settings[chk] = self.prelude.checkboxes[chk]
        boot_settings['txt_args_more'] = additional_args
        boot_settings['drp_choose_version'] = version

        all_settings = self.prelude.all_settings
        all_settings['boot_settings'] = boot_settings

        toolkit.write_json(self.prelude.setting_file, all_settings)

    def update_boot_setting(self, setting, value):
        boot_settings = self.prelude.boot_settings
        boot_settings[setting] = value

        all_settings = self.prelude.all_settings
        all_settings['boot_settings'] = boot_settings
        toolkit.write_json(self.prelude.setting_file, all_settings)

    def change_auto_vram(self, auto_vram):
        self.update_boot_setting('auto_vram', auto_vram)

    def mem_release(self):
        try:
            gc.collect()
            devices.torch_gc()
            torch.cuda.empty_cache()
            gc.collect()

            print('Miaoshouai boot assistant: Memory Released!')
        except:
            print('Miaoshouai boot assistant: Memory Release Failed...!')

    def force_mem_release(self):
        try:
            if hasattr(sd_samplers, "create_sampler_original_md"):
                sd_samplers.create_sampler = sd_samplers.create_sampler_original_md
                del sd_samplers.create_sampler_original_md
            if hasattr(processing, "create_random_tensors_original_md"):
                processing.create_random_tensors = processing.create_random_tensors_original_md
                del processing.create_random_tensors_original_md

            cuda.select_device(0)
            cuda.close()
            cuda.select_device(0)
            self.mem_release()
            msg = 'Memory Released! (May not work if you already got CUDA out of memory error)'
        except Exception as e:
            msg = f'Memory Release Failed! ({str(e)})'

        return gr.Markdown.update(visible=True, value=msg)

        return gr.Markdown.update(visible=True, value=msg)
    def get_all_models(self, site: str) -> t.Any:
        return toolkit.read_json(self.prelude.model_json[site])

    def update_model_json(self, site: str, models: t.Any) -> None:
        toolkit.write_json(self.prelude.model_json[site], models)

    def get_hash_from_json(self, chk_point: CheckpointInfo) -> CheckpointInfo:
        model_hashes = toolkit.read_json(self.prelude.model_hash_file)

        if len(model_hashes) == 0 or chk_point.title not in model_hashes.keys():
            chk_point.shorthash = self.calculate_shorthash(chk_point)
            model_hashes[chk_point.title] = chk_point.shorthash
            toolkit.write_json(self.prelude.model_hash_file, model_hashes)
        else:
            chk_point.shorthash = model_hashes[chk_point.title]

        return chk_point

    def calculate_shorthash(self, chk_point: CheckpointInfo):
        if chk_point.sha256 is None:
            return
        else:
            return chk_point.sha256[0:10]


    def update_my_model_type(self, search_txt, model_type) -> t.Dict:
        my_models = self.get_local_models(search_txt, model_type)
        self.ds_my_models.samples = my_models

        return gr.Dataset.update(samples=my_models)

    def get_local_models(self, search_txt='', model_type='Checkpoint') -> t.List[t.Any]:
        models = []

        for root, dirs, files in os.walk(self.prelude.model_type[model_type]):
            for file in files:
                mpath = os.path.join(root, file)

                fname, ext = os.path.splitext(file)
                if ext in ['.ckpt', '.safetensors', '.pt'] and file != 'scaler.pt' and (search_txt in fname or search_txt == ''):
                    chkpt_info = modules.sd_models.get_closet_checkpoint_match(file)
                    if chkpt_info is None:
                        chkpt_info = CheckpointInfo(os.path.join(root, file))

                    if chkpt_info.sha256 is None and chkpt_info.shorthash is None:
                        chkpt_info = self.get_hash_from_json(chkpt_info)

                    model_info = self.search_model_info(chkpt_info, mpath, model_type)
                    fname = re.sub(r'\[.*?\]', "", chkpt_info.title)

                    if model_info is not None:
                        models.append(model_info)
                    else:
                        self.logger.info(
                            f"{chkpt_info.title}, {chkpt_info.hash}, {chkpt_info.shorthash}, {chkpt_info.sha256}")
                        models.append([
                            self.prelude.no_preview_img,
                            0,
                            [os.path.basename(fname)],
                            [mpath.replace(self.prelude.model_type[model_type]+'\\', '')]])

        return models


    def refresh_local_models(self, search_txt, model_type) -> t.Dict:
        my_models = self.get_local_models(search_txt, model_type)
        self.ds_my_models.samples = my_models

        return gr.Dataset.update(samples=my_models)

    def delete_model(self, model, search_txt, model_type):
        fname = model[3][0]
        mfolder = self.prelude.model_type[model_type]
        mpapth = os.path.join(mfolder, fname)

        os.remove(mpapth)
        my_models = self.get_local_models(search_txt, model_type)
        self.ds_my_models.samples = my_models

        return gr.Dataset.update(samples=my_models)

    def set_all_covers(self, search_txt, model_type):
        for model in self.ds_my_models.samples:
            try:
                if model[0] == self.prelude.no_preview_img and model[1] != 0:
                    img_list, l1, htmlDetail, h2 = self.get_model_info(model)
                    soup = BeautifulSoup(img_list[0][0])
                    cover_url = soup.findAll('img')[0]['src'].replace('width=150', 'width=450')

                    fname = model[3][0]
                    mname, ext = os.path.splitext(fname)
                    mfolder = self.prelude.model_type[model_type]
                    dst = os.path.join(mfolder, f'{mname}.jpg')

                    if fname is not None and not os.path.exists(dst):
                        if self.my_model_source == 'liandange.com':
                            cover_url = soup.findAll('img')[0]['src'].replace('/w/150', '/w/450')
                        r = requests.get(cover_url, timeout=30, stream=True)
                        r.raw.decode_content = True
                        with open(dst, 'wb') as f:
                            shutil.copyfileobj(r.raw, f)
            except Exception as e:
                print(model[1], cover_url, dst, str(e))
                continue

        my_models = self.get_local_models(search_txt, model_type)
        self.ds_my_models.samples = my_models

        return gr.Dataset.update(samples=my_models)

    def set_cover(self, model, cover, search_txt, model_type):
        fname = model[3][0]
        mname, ext = os.path.splitext(fname)
        mfolder = self.prelude.model_type[model_type]

        dst = os.path.join(mfolder, f'{mname}.jpg')
        cover.save(dst)

        my_models = self.get_local_models(search_txt, model_type)
        self.ds_my_models.samples = my_models

        return gr.Dataset.update(samples=my_models)



    def search_model_info(self, chkpt_info: CheckpointInfo, mpath: str, model_type: str) -> t.Optional[t.List[t.Any]]:

        lookup_sha256 = chkpt_info.sha256
        lookup_shash = chkpt_info.shorthash
        fname = re.sub(r'\[.*?\]', "", chkpt_info.title)
        if '\\' in fname:
            fname = fname.split('\\')[-1]

        self.logger.info(f"lookup_sha256: {lookup_sha256}, lookup_shash: {lookup_shash}, fname: {fname}")

        res = None
        if lookup_sha256 is None and lookup_shash is None and fname is None:
            return None

        prefix, ext = os.path.splitext(mpath)

        if os.path.exists(f'{prefix}.jpg'):
            cover_img = os.path.join(os.path.dirname(mpath), f'{os.path.basename(prefix)}.jpg')
        elif os.path.exists(f'{prefix}.png'):
            cover_img = os.path.join(os.path.dirname(mpath), f'{os.path.basename(prefix)}.png')
        elif os.path.exists(f'{prefix}.webp'):
            cover_img = os.path.join(os.path.dirname(mpath), f'{os.path.basename(prefix)}.webp')
        else:
            cover_img = self.prelude.no_preview_img

        if not os.path.exists(self.prelude.cover_folder):
            os.mkdir(self.prelude.cover_folder)

        dst = os.path.join(self.prelude.cover_folder, os.path.basename(cover_img))
        try:
            if cover_img != self.prelude.no_preview_img and os.path.exists(cover_img) and os.path.exists(dst):
                dst_size = os.stat(dst).st_size
                cover_size = os.stat(cover_img).st_size
                if dst_size != cover_size:
                    print('update to new cover')
                    shutil.copyfile(cover_img, dst)
            elif cover_img != self.prelude.no_preview_img and os.path.exists(cover_img) and not os.path.exists(dst):
                shutil.copyfile(cover_img, dst)
            elif cover_img == self.prelude.no_preview_img:
                dst = cover_img
        except Exception as e:
            dst = self.prelude.no_preview_img

        for model in self.my_model_set:
            match = False

            for ver in model['modelVersions']:
                for file in ver['files']:
                    if fname == file['name']:
                        match = True
                    elif lookup_sha256 is not None and 'SHA256' in file['hashes'].keys():
                        match = (lookup_sha256.upper() == file['hashes']['SHA256'].upper())
                    elif lookup_shash is not None:
                        match = (lookup_shash[:10].upper() in [h.upper() for h in file['hashes'].values()])

                    if match:
                        mid = model['id']

                        res = [
                            dst,
                            mid,
                            [f"{model['name']}/{ver['name']}"],
                            [mpath.replace(self.prelude.model_type[model_type]+'\\', '')]
                        ]

            if match:
                break

        return res

    def update_xformers(self, gpu, checkgroup):
        if '--xformers' in self.prelude.gpu_setting[gpu]:
            if 'Enable xFormers' not in checkgroup:
                checkgroup.append('Enable xFormers')

        return checkgroup

    def set_nsfw(self, search='', nsfw_checker=False, model_type='All') -> t.Dict:
        self._allow_nsfw = nsfw_checker
        new_list = self.get_images_html(search, model_type)
        if self._ds_models is None:
            self.logger.error(f"_ds_models is not initialized")
            return {}

        self._ds_models.samples = new_list
        return self._ds_models.update(samples=new_list)

    def search_model(self, search='', chk_nsfw=False, model_type='All') -> t.Dict:
        if self._ds_models is None:
            self.logger.error(f"_ds_models is not initialized")
            return {}

        new_list = self.get_images_html(search, chk_nsfw, model_type)

        self._ds_models.samples = new_list
        return self._ds_models.update(samples=new_list)

    def search_my_model(self, search_txt='', model_type='Checkpoint') -> t.Dict:
        if self._ds_models is None:
            self.logger.error(f"_ds_models is not initialized")
            return {}

        new_list = self.get_local_models(search_txt, model_type)

        self._ds_my_models.samples = new_list
        return self._ds_my_models.update(samples=new_list)

    def get_model_byid(self, mid, model_source) -> t.List:
        response = requests.get(self.prelude.api_url(model_source) + f'/{mid}')
        payload = response.json()
        if payload.get("success") is not None and not payload.get("success"):
            return []

        return [payload]

    def get_model_info(self, models) -> t.Tuple[t.List[t.List[str]], t.Dict, str, t.Dict]:
        drop_list = []
        cover_imgs = []
        htmlDetail = "<div><p>No info found</p></div>"

        mid = models[1]

        # TODO: use map to enhance the performances
        if self.active_model_set == 'model_set':
            if self.model_source == "civitai.com" or self.model_source == "liandange.com":
                m_list = self.get_model_byid(mid, self.model_source)
            else:
                m_list = [e for e in self.model_set if e['id'] == mid]
        else:
            if self.my_model_source == "civitai.com" or self.my_model_source == "liandange.com":
                m_list = self.get_model_byid(mid, self.my_model_source)
                self._allow_nsfw = True
            else:
                m_list = [e for e in self.my_model_set if e['id'] == mid]

        if m_list is not None and len(m_list) > 0:
            m = m_list[0]
        else:
            return [[]], {}, htmlDetail, {}

        self.model_files.clear()

        download_url_by_default = None
        if m and m.get('modelVersions') and len(m.get('modelVersions')) > 0:
            latest_version = m['modelVersions'][0]

            if latest_version.get('images') and isinstance(latest_version.get('images'), list):
                for img in latest_version['images']:
                    if self.allow_nsfw or (not self.allow_nsfw and (not img.get('nsfw') or img.get('nsfw') in ['None', 'Soft'])):
                        if img.get('url'):
                            cover_imgs.append([f'<img referrerpolicy="no-referrer" src="{img["url"].replace("width=450","width=150").replace("/w/100", "/w/150")}" style="width:150px;">'])

            if latest_version.get('files') and isinstance(latest_version.get('files'), list):
                for file in latest_version['files']:
                    # error checking for mandatory fields
                    if file.get('id') is not None and file.get('downloadUrl') is not None:
                        item_name = None
                        if file.get('name'):
                            item_name = file.get('name')
                        if not item_name and latest_version.get('name'):
                            item_name = latest_version['name']
                        if not item_name:
                            item_name = "unknown"

                        self.model_files.append({
                            "id:": file['id'],
                            "url": file['downloadUrl'],
                            "name": item_name,
                            "type": m['type'] if m.get('type') else "unknown",
                            "size": file['sizeKB'] * 1024 if file.get('sizeKB') else "unknown",
                            "format": file['format'] if file.get('format') else "unknown",
                            "cover": cover_imgs[0][0] if len(cover_imgs) > 0 else toolkit.get_not_found_image_url(),
                        })
                        file_size = toolkit.get_readable_size(file['sizeKB'] * 1024) if file.get('sizeKB') else ""
                        if file_size:
                            drop_list.append(f"{item_name} ({file_size})")
                        else:
                            drop_list.append(f"{item_name}")

                        if not download_url_by_default:
                            download_url_by_default = file.get('downloadUrl')

            htmlDetail = '<div>'
            if m.get('name'):
                htmlDetail += f"<h1>{m['name']}</h1></br>"
            if m.get('stats') and m.get('stats').get('downloadCount'):
                htmlDetail += f"<p>Downloads: {m['stats']['downloadCount']}</p>"
            if m.get('stats') and m.get('stats').get('rating'):
                htmlDetail += f"<p>Rating: {m['stats']['rating']}</p>"
            if m.get('creator') and m.get('creator').get('username'):
                htmlDetail += f"<p>Author: {m['creator']['username']}</p></div></br></br>"
            if latest_version.get('name'):
                htmlDetail += f"<div><table><tbody><tr><td>Version:</td><td>{latest_version['name']}</td></tr>"
            if latest_version.get('updatedAt'):
                htmlDetail += f"<tr><td>Updated Time:</td><td>{latest_version['updatedAt']}</td></tr>"
            if m.get('type'):
                htmlDetail += f"<tr><td>Type:</td><td>{m['type']}</td></tr>"
            if latest_version.get('baseModel'):
                htmlDetail += f"<tr><td>Base Model:</td><td>{latest_version['baseModel']}</td></tr>"
            htmlDetail += f"<tr><td>NFSW:</td><td>{m.get('nsfw') if m.get('nsfw') is not None else 'false'}</td></tr>"
            if m.get('tags') and isinstance(m.get('tags'), list):
                htmlDetail += f"<tr><td>Tags:</td><td>"
                for t in m['tags']:
                    htmlDetail += f'<span style="margin-right:5px>{t}</span>'
                htmlDetail += "</td></tr>"
            if latest_version.get('trainedWords'):
                htmlDetail += f"<tr><td>Trigger Words:</td><td>"
                for t in latest_version['trainedWords']:
                    htmlDetail += f'<span style="margin-right:5px;">{t}</span>'
                htmlDetail += "</td></tr>"
            htmlDetail += "</tbody></table></div>"
            htmlDetail += f"<div>{m['description'] if m.get('description') else 'N/A'}</div>"

        self._ds_cover_gallery.samples = cover_imgs

        return (
            cover_imgs,
            gr.Dropdown.update(choices=drop_list, value=drop_list[0] if len(drop_list) > 0 else []),
            htmlDetail,
            gr.HTML.update(value=f'<p style="text-align: center;">'
                                 f'<a style="text-align: center;" href="{download_url_by_default}" '
                                 'target="_blank">Download</a></p>')
        )

    def get_my_model_covers(self, model, model_type):
        img_list, l1, htmlDetail, h2 = self.get_model_info(model)
        if self._ds_my_model_covers is None:
            self.logger.error(f"_ds_my_model_covers is not initialized")
            return {}

        new_html = '<div></div>'
        if htmlDetail is not None:
            new_html = htmlDetail.split('</tbody></table></div>')[0] + '</tbody></table></div>'

        cover_list = []
        for img_link in img_list:
            cover_html = '<div style="display: flex; align-items: center;">\n'
            cover_html += f'<div style = "margin-right: 10px;" class ="model-item" >\n'
            if len(img_link) > 0:
                cover_html += f'{img_link[0]}\n'

            cover_html += '</div>\n</div>'
            cover_list.append([cover_html])

        if model_type == 'TextualInversion':
            mname, ext = os.path.splitext(model[3][0])
            button_html = '<div class ="lg secondary gradio-button svelte-1ipelgc" style="text-align: center;" ' \
                            f'onclick="return cardClicked(&quot;txt2img&quot;, &quot;{mname}&quot;, true)"><a href="javascript:void(0)">Send to Prompt</a></div>'

        elif model_type == 'LORA':
            mname, ext = os.path.splitext(model[3][0])
            button_html = '<div class ="lg secondary gradio-button svelte-1ipelgc" style="text-align: center;" ' \
                          f'onclick="return cardClicked(&quot;txt2img&quot;, &quot;<lora:{mname}:&quot; + opts.extra_networks_default_multiplier + &quot;>&quot;, false)"><a href="javascript:void(0)">Send to Prompt</a></div>'
        elif model_type.upper() == 'LoCon'.upper():
            mname, ext = os.path.splitext(model[3][0])
            button_html = '<div class ="lg secondary gradio-button svelte-1ipelgc" style="text-align: center;" ' \
                          f'onclick="return cardClicked(&quot;txt2img&quot;, &quot;<lyco:{mname}:&quot; + opts.extra_networks_default_multiplier + &quot;>&quot;, false)"><a href="javascript:void(0)">Send to Prompt</a></div>'
        else:
            mpath = os.path.join(self.prelude.model_type[model_type], model[3][0])
            checkpoint_info = CheckpointInfo(mpath)
            button_html = f'<div class="lg secondary gradio-button svelte-1ipelgc" style="text-align: center;"' \
                          f'onclick="return selectCheckpoint(&quot;{checkpoint_info.title}&quot;)"><a href="javascript:void(0)">Load Model</a></div>'

        self._ds_my_model_covers.samples = cover_list
        return self._ds_my_model_covers.update(samples=cover_list), gr.HTML.update(visible=True, value=new_html), gr.HTML.update(visible=True, value=button_html)


    def update_cover_info(self, model, covers):

        soup = BeautifulSoup(covers[0])
        cover_url = soup.findAll('img')[0]['src'].replace('width=150', 'width=450')

        if self.my_model_set is None:
            self.logger.error("model_set is null")
            return []

        mid = model[1]
        m_list = self.get_model_byid(mid, self.my_model_source)
        if m_list is not None or m_list != []:
            m = m_list[0]
        else:
            return {}, {}

        generation_info = ''
        fname = None
        for mv in m['modelVersions']:
            for img in mv['images']:
                if img['url'] == cover_url:
                    if img['meta'] is not None and img['meta'] != '':
                        try:
                            meta = img['meta']
                            generation_info += f"{meta['prompt']}\n"
                            if meta['negativePrompt'] is not None:
                                generation_info += f"Negative prompt: {meta['negativePrompt']}\n"
                            generation_info += f"Steps: {meta['steps']}, Sampler: {meta['sampler']}, "
                            generation_info += f"CFG scale: {meta['cfgScale']}, Seed: {meta['seed']}, Size: {meta['Size']},"
                            if meta['Model hash'] is not None:
                                generation_info += f"Model hash: {meta['Model hash']}"

                        except Exception as e:
                            self.logger.info(f"generation_info error:{str(e)}")
                            pass

                    if not os.path.exists(self.prelude.cache_folder):
                        os.mkdir(self.prelude.cache_folder)

                    if self.my_model_source == 'civitai.com':
                        fname = os.path.join(self.prelude.cache_folder, f"{cover_url.split('/')[-1]}.jpg")
                    elif self.my_model_source == 'liandange.com':
                        fname = os.path.join(self.prelude.cache_folder, cover_url.split('?')[0].split('/')[-1])

                    break

        if fname is not None and not os.path.exists(fname):
            if self.my_model_source == 'liandange.com':
                cover_url = soup.findAll('img')[0]['src'].replace('/w/150', '/w/450')
            r = requests.get(cover_url, timeout=30, stream=True)
            r.raw.decode_content = True
            with open(fname, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

        return gr.Button.update(visible=True), gr.Text.update(value=generation_info), gr.Image.update(value=fname)

    def get_downloading_status(self):
        (_, _, desc) = self.downloader_manager.tasks_summary()
        return gr.HTML.update(value=desc)

    def download_model(self, filename: str):
        model_path = modules.paths.models_path
        script_path = modules.paths.script_path

        urls = []
        for _, f in enumerate(self.model_files):
            if not f.get('name'):
                continue
            model_fname = re.sub(r"\s*\(\d+(?:\.\d*)?.B\)\s*$", "", f['name'])

            if model_fname in filename:
                m_pre, m_ext = os.path.splitext(model_fname)
                cover_fname = f"{m_pre}.jpg"
                soup = BeautifulSoup(f['cover'])
                cover_link = soup.findAll('img')[0]['src'].replace('/w/150', '/w/450').replace('width=150', 'width=450')

                if f['type'] == 'LORA':
                    cover_fname = os.path.join(model_path, 'Lora', cover_fname)
                    model_fname = os.path.join(model_path, 'Lora', model_fname)
                elif f['type'].upper() == 'LoCon'.upper():
                    cover_fname = os.path.join(model_path, 'LyCORIS', cover_fname)
                    model_fname = os.path.join(model_path, 'LyCORIS', model_fname)
                elif f['type'] == 'VAE':
                    cover_fname = os.path.join(model_path, 'VAE', cover_fname)
                    model_fname = os.path.join(model_path, 'VAE', model_fname)
                elif f['type'] == 'TextualInversion':
                    cover_fname = os.path.join(script_path, 'embeddings', cover_fname)
                    model_fname = os.path.join(script_path, 'embeddings', model_fname)
                elif f['type'] == 'Hypernetwork':
                    cover_fname = os.path.join(model_path, 'hypernetworks', cover_fname)
                    model_fname = os.path.join(model_path, 'hypernetworks', model_fname)
                elif f['type'] == 'Controlnet':
                    cover_fname = os.path.join(shared.script_path, 'extensions', 'sd-webui-controlnet', 'models', cover_fname)
                    model_fname = os.path.join(shared.script_path, 'extensions', 'sd-webui-controlnet', 'models', model_fname)
                else:
                    cover_fname = os.path.join(model_path, 'Stable-diffusion', cover_fname)
                    model_fname = os.path.join(model_path, 'Stable-diffusion', model_fname)

                urls.append((cover_link, f['url'], f['size'], cover_fname, model_fname))
                break

        for (cover_url, model_url, total_size, local_cover_name, local_model_name) in urls:
            self.downloader_manager.download(
                source_url=cover_url,
                target_file=local_cover_name,
                estimated_total_size=None,
            )
            self.downloader_manager.download(
                source_url=model_url,
                target_file=local_model_name,
                estimated_total_size=total_size,
            )

        #
        # currently, web-ui is without queue enabled.
        #
        # webui_queue_enabled = False
        # if webui_queue_enabled:
        #     start = time.time()
        #     downloading_tasks_iter = self.downloader_manager.iterator()
        #     for i in progressbar.tqdm(range(100), unit="byte", desc="Models Downloading"):
        #         while True:
        #             try:
        #                 finished_bytes, total_bytes = next(downloading_tasks_iter)
        #                 v = finished_bytes / total_bytes
        #                 print(f"\n v = {v}")
        #                 if isinstance(v, float) and int(v * 100) < i:
        #                     print(f"\nv({v}) < {i}")
        #                     continue
        #                 else:
        #                     break
        #             except StopIteration:
        #                 break
        #
        #         time.sleep(0.5)
        #
        #     self.logger.info(f"[downloading] finished after {time.time() - start} secs")

        time.sleep(2)

        #self.model_files.clear()
        return gr.HTML.update(value=f"<h4>{len(urls)} downloading tasks added into task list</h4>")

    def install_preset_models_if_needed(self, update_ds: bool):
        assets_folder = os.path.join(self.prelude.ext_folder, "assets")
        configs_folder = os.path.join(self.prelude.ext_folder, "configs")

        for model_filename in ["civitai_models.json", "liandange_models.json", "gpt_index.json"]:
            gzip_file = os.path.join(assets_folder, f"{model_filename}.gz")
            target_file = os.path.join(configs_folder, f"{model_filename}")

            if not os.path.exists(gzip_file):
                self.relocate_assets_if_needed()
                sub_repo = git.Repo(self.prelude.assets_folder)
                sub_repo.git.fetch(all=True)
                sub_repo.git.reset('origin', hard=True)

            if update_ds or not os.path.exists(target_file):
                with gzip.open(gzip_file, "rb") as compressed_file:
                    with io.TextIOWrapper(compressed_file, encoding="utf-8") as decoder:
                        content = decoder.read()
                        with open(target_file, "w") as model_file:
                            model_file.write(content)

                print('Data source unpacked successfully')

    def relocate_assets_if_needed(self):
        repo = git.Repo(self.prelude.ext_folder)
        print('Updating asset repo...')
        try:
            old_repo = True
            if os.path.exists(self.prelude.assets_folder):
                for filename in os.listdir(self.prelude.assets_folder):
                    if '.git' in filename:
                        old_repo = False
                        break

                if old_repo:
                    shutil.rmtree(self.prelude.assets_folder)

            for submodule in repo.submodules:
                submodule.update(init=True)
        except Exception as e:
            print('error', str(e))

    def get_dir_and_file(self, file_path):
        dir_path, file_name = os.path.split(file_path)
        return (dir_path, file_name)

    def open_folder(self, folder_path=''):
        if not any(var in os.environ for var in self.prelude.ENV_EXCLUSION) and sys.platform != 'darwin':
            current_folder_path = folder_path

            initial_dir, initial_file = self.get_dir_and_file(folder_path)

            #root = tk.Tk()
            #root.wm_attributes('-topmost', 1)
            #root.withdraw()
            #folder_path = filedialog.askdirectory(initialdir=initial_dir)
            #root.destroy()

            if folder_path == '':
                folder_path = current_folder_path

        return folder_path

    def change_model_folder(self, folder_path=''):

        res = 'Model folder is linked successfully'
        if folder_path == '':
            return gr.Markdown.update(value='No directory is set', visible=True)

        try:
            src = shared.models_path
            # Destination file path
            dst = folder_path

            # Create a symbolic link
            # pointing to src named dst
            # using os.symlink() method
            subprocess.check_call('mklink /J "%s" "%s"' % (src, dst), shell=True)
        except Exception as e:
            res = str(e)

        return gr.Markdown.update(value=res, visible=True)

    def change_boot_setting(self, version, drp_gpu, drp_theme, txt_listen_port, chk_group_args, additional_args):
        self.get_final_args(drp_gpu, drp_theme, txt_listen_port, chk_group_args, additional_args)
        self.logger.info(f'saved_cmd: {self.cmdline_args}')

        if version == 'Official Release':
            target_webui_user_file = "webui-user.bat"
        else:
            target_webui_user_file = "webui-user-launch.bat"
        script_export_keyword = "export"
        if platform.system() == "Linux":
            target_webui_user_file = "webui-user.sh"
        elif platform.system() == "Darwin":
            target_webui_user_file = "webui-macos-env.sh"
        else:
            script_export_keyword = "set"

        filepath = os.path.join(modules.shared.script_path, target_webui_user_file)
        self.logger.info(f"to update: {filepath}")

        msg = 'Result: Setting Saved.'
        if version == 'Official Release':
            try:
                if not os.path.exists(filepath):
                    shutil.copyfile(os.path.join(self.prelude.ext_folder, 'configs', target_webui_user_file), filepath)

                with fileinput.FileInput(filepath, inplace=True, backup='.bak') as file:
                    for line in file:
                        if 'COMMANDLINE_ARGS' in line:
                            rep_txt = ' '.join(self.cmdline_args).replace('\\', '\\\\')
                            line = f'{script_export_keyword} COMMANDLINE_ARGS={rep_txt}\n'
                        sys.stdout.write(line)

            except Exception as e:
                msg = f'Error: {str(e)}'
        else:
            try:
                if not os.path.exists(filepath):
                    shutil.copyfile(os.path.join(self.prelude.ext_folder, 'configs', target_webui_user_file), filepath)

                new_data = ''
                with open(filepath, 'r+') as file:
                    data = file.readlines()
                    for line in data:
                        if 'webui.py' in line:
                            rep_txt = ' '.join(self.cmdline_args).replace('\\', '\\\\')
                            line = f"python\python.exe webui.py {rep_txt}\n"
                        new_data += line
                    file.seek(0)
                    file.write(new_data)
                    file.truncate()

            except Exception as e:
                msg = f'Error: {str(e)}'

        self.update_boot_settings(version, drp_gpu, drp_theme, txt_listen_port, chk_group_args, additional_args)
        return gr.update(value=msg, visible=True)

    def check_update(self):
        update_status = 'latest'
        show_update = False
        repo = git.Repo(self.prelude.ext_folder)
        print('Checking updates for miaoshouai-assistant...')
        for fetch in repo.remote().fetch(dry_run=True):
            if fetch.flags != fetch.HEAD_UPTODATE:
                show_update = True
                update_status = "behind"
                break

        print('Checking updates for data source...')
        if os.path.exists(self.prelude.assets_folder):
            fcount = len([entry for entry in os.listdir(self.prelude.assets_folder) if os.path.isfile(os.path.join(self.prelude.assets_folder, entry))])

        if not os.path.exists(self.prelude.assets_folder) or fcount <= 0:
            self.relocate_assets_if_needed()
            show_update = True
            update_status = "behind"
        else:
            try:
                asset_repo = git.Repo(self.prelude.asset_folder)
                for fetch in asset_repo.remote().fetch(dry_run=True):
                    if fetch.flags != fetch.HEAD_UPTODATE:
                        show_update = True
                        update_status = "behind"
                        break
            except Exception as e:
                self.logger.info(f"Error during checking asset, try to relocate.\n{str(e)}")
                self.relocate_assets_if_needed()
                show_update = True
                update_status = "behind"

        return gr.Markdown.update(visible=True, value=update_status), gr.Checkbox.update(visible=show_update), gr.Button.update(visible=show_update)

    def process_prompt(self, model, model_type, prompt: str):
        text_replace = {'/': '|', 'a girl': '1girl', 'a boy': '1boy', 'a women': '1women', 'a man': '1man'}
        for rep in text_replace.keys():
            prompt = prompt.strip().lower().replace(rep, text_replace[rep])

        try:
            mid = model[1]
            m_list = self.get_model_byid(mid, self.my_model_source)
            if m_list is not None or m_list != []:
                m = m_list[0]
            else:
                return prompt
        except Exception as e:
            self.logger.info(f"generation_info error:{str(e)}")
            return prompt

        generation_info = ''
        for mv in m['modelVersions']:
            img_cnt = len(mv['images'])
            img = mv['images'][random.randint(0, img_cnt-1)]
            if img['meta'] is not None and img['meta'] != '':
                try:
                    meta = img['meta']

                    lora = ''
                    if model_type == 'LORA':
                        mname, ext = os.path.splitext(model[3][0])
                        lora = f', <lora:{mname}:0.7>'
                    elif model_type.upper() == 'LoCon'.upper():
                        mname, ext = os.path.splitext(model[3][0])
                        lora = f', <lyco:{mname}:0.7>'

                    tw_count = len(mv['trainedWords'])
                    if tw_count > 0:
                        twords = mv['trainedWords'][random.randint(0, tw_count-1)]
                        generation_info += f"{prompt}, {twords}{lora}\n"
                    else:
                        generation_info += f"{prompt}{lora}\n"

                    if meta['negativePrompt'] is not None:
                        generation_info += f"Negative prompt: {meta['negativePrompt']}\n"
                    generation_info += f"Steps: {meta['steps']}, Sampler: {meta['sampler']}, "
                    generation_info += f"CFG scale: {meta['cfgScale']}, Seed: -1, Size: {meta['Size']},"
                    if meta['Model hash'] is not None:
                        generation_info += f"Model hash: {meta['Model hash']}"

                except Exception as e:
                    self.logger.info(f"generation_info error:{str(e)}")
                    return generation_info

            break

        return generation_info

    def get_gpt_prompt(self, model, model_type, main_prompt):
        os.environ["OPENAI_API_KEY"] = self.prelude.boot_settings['openai_api']

        if model is None:
            return gr.TextArea.update(value='Please select a model first')

        if not os.path.exists(self.prelude.gpt_index):
            self.install_preset_models_if_needed(True)

        index = GPTSimpleVectorIndex.load_from_disk(self.prelude.gpt_index)
        max_tokens = 4000

        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=f"translate the following text into English:\n{main_prompt}",
                max_tokens=max_tokens,
                n=1,
                stop=None,
                temperature=0.5,
            )
            res_prompt = response.choices[0].text.strip().replace('Translation:', '')
            gpt_prompt = 'give me a prompt for: ' + res_prompt

            response = index.query(gpt_prompt, response_mode="compact")
            res_prompt = self.process_prompt(model, model_type, response.response)
        except Exception as e:
            res_prompt = str(e)
            return gr.TextArea.update(value=res_prompt)

        return gr.TextArea.update(value=res_prompt)

    def update_gptapi(self, apikey):
        if apikey == '':
            res = 'Please enter a valid API Key'
            gpt_hint_text = 'Set your OpenAI api key in Setting & Update first: https://platform.openai.com/account/api-keys'
            value_text = gpt_hint_text
        else:
            self.update_boot_setting('openai_api', apikey)
            os.environ["OPENAI_API_KEY"] = apikey
            res = 'API Key updated'
            gpt_hint_text = 'Select a model and type some text here, ChatGPT will generate prompt for you. Supports different text in different languages.'
            value_text = ''

        return gr.Markdown.update(value=res, visible=True), gr.Textbox.update(placeholder=gpt_hint_text, value=value_text)

    def update_program(self, dont_update_ms=False):
        result = "Update successful, restart to take effective."
        try:
            print('Updating miaoshouai-assistant...')
            repo = git.Repo(self.prelude.ext_folder)
            # Fix: `error: Your local changes to the following files would be overwritten by merge`,
            # because WSL2 Docker set 755 file permissions instead of 644, this results to the error.
            repo.git.fetch(all=True)
            repo.git.reset('origin', hard=True)
            if not dont_update_ms:
                sub_repo = git.Repo(self.prelude.assets_folder)
                sub_repo.git.fetch(all=True)
                sub_repo.git.reset('origin', hard=True)
                self.install_preset_models_if_needed(True)
        except Exception as e:
            result = str(e)

        return gr.Markdown.update(visible=True, value=result)


    @property
    def model_set(self) -> t.List[t.Dict]:
        try:
            self.install_preset_models_if_needed(False)
            self.logger.info(f"access to model info for '{self.model_source}'")
            model_json_mtime = toolkit.get_file_last_modified_time(self.prelude.model_json[self.model_source])

            if self._model_set is None or self._model_set_last_access_time is None \
                    or self._model_set_last_access_time < model_json_mtime:
                self._model_set = self.get_all_models(self.model_source)
                self._model_set_last_access_time = model_json_mtime
                self.logger.info(f"load '{self.model_source}' model data from local file")
        except Exception as e:
            self.refresh_all_models()
            self._model_set_last_access_time = datetime.datetime.now()

        return self._model_set

    @property
    def my_model_set(self) -> t.List[t.Dict]:
        try:
            self.install_preset_models_if_needed(False)
            self.logger.info(f"access to model info for '{self.my_model_source}'")
            model_json_mtime = toolkit.get_file_last_modified_time(self.prelude.model_json[self.my_model_source])

            if self._my_model_set is None or self._my_model_set_last_access_time is None \
                or self._my_model_set_last_access_time < model_json_mtime:
                self._my_model_set = self.get_all_models(self.my_model_source)
                self._my_model_set_last_access_time = model_json_mtime
                self.logger.info(f"load '{self.my_model_source}' model data from local file")
        except Exception as e:
            self.refresh_all_models()
            self._my_model_set_last_access_time = datetime.datetime.now()

        return self._my_model_set


    @property
    def allow_nsfw(self) -> bool:
        return self._allow_nsfw

    @property
    def old_additional_args(self) -> str:
        return self._old_additional

    @property
    def ds_models(self) -> gr.Dataset:
        return self._ds_models

    @ds_models.setter
    def ds_models(self, newone: gr.Dataset):
        self._ds_models = newone

    @property
    def ds_cover_gallery(self) -> gr.Dataset:
        return self._ds_cover_gallery

    @ds_cover_gallery.setter
    def ds_cover_gallery(self, newone: gr.Dataset):
        self._ds_cover_gallery = newone

    @property
    def ds_my_models(self) -> gr.Dataset:
        return self._ds_my_models

    @ds_my_models.setter
    def ds_my_models(self, newone: gr.Dataset):
        self._ds_my_models = newone

    @property
    def ds_my_model_covers(self) -> gr.Dataset:
        return self._ds_my_model_covers

    @ds_my_model_covers.setter
    def ds_my_model_covers(self, newone: gr.Dataset):
        self._ds_my_model_covers = newone

    @property
    def model_source(self) -> str:
        return self._model_source

    @model_source.setter
    def model_source(self, newone: str):
        self.logger.info(f"model source changes from {self.model_source} to {newone}")
        self._model_source = newone
        self._model_set_last_access_time = None  # reset timestamp

    @property
    def my_model_source(self) -> str:
        return self._my_model_source

    @my_model_source.setter
    def my_model_source(self, newone: str):
        self.logger.info(f"model source changes from {self.my_model_source} to {newone}")
        self._my_model_source = newone
        self._my_model_set_last_access_time = None  # reset timestamp

    @property
    def active_model_set(self) -> str:
        return self._active_model_set

    @active_model_set.setter
    def active_model_set(self, newone: str):
        self.logger.info(f"model set changes from {self.active_model_set} to {newone}")
        self._active_model_set = newone

    @property
    def git_address(self) -> str:
        return self._git_address

    def introception(self) -> None:
        (gpu, theme, port, checkbox_values, extra_args, ver) = self.get_default_args()

        print("################################################################")
        print("MIAOSHOU ASSISTANT ARGUMENTS:")

        print(f"  gpu = {gpu}")
        print(f"  theme = {theme}")
        print(f"  port = {port}")
        print(f"  checkbox_values = {checkbox_values}")
        print(f"  extra_args = {extra_args}")
        print(f"  webui ver = {ver}")

        print("################################################################")

