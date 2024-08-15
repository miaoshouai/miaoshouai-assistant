# miaoshouai-assistant

[English](README.md) / [中文](README_CN.md)

MiaoshouAI Assistant for [Automatic1111 WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)


#### Some Notice for this version
If you want to use MiaoshouAI Assistant in [Forge WebUI](https://github.com/lllyasviel/stable-diffusion-webui-forge), you can install [MiaoshouAI Assistant Forge Version](https://github.com/miaoshouai/miaoshouai-assistant-forge)  

If you had download failures for when downloading models, it is likely because model auther has restricted a login requirement for the model.
You need to go to civitai, under your [Account Settings](https://civitai.com/user/account) to apply for a civitai api key and save it through the ```Setting & Update``` tab.

### Version History

-1.90 Add support for civitai key and updated base model types.</br>
-1.81 Added MiaoshouAI as a model download source for people who can't access civitai; added a few sdxl controlnet and official downloads.
-1.80 Fixed download problem in webui 1.60; Added support for model sorting; Model version, sub-folder support for download; Other bug fixes and improvements</br>
-1.70 Improved search capability for Civitai to include keyword search in model names; Now supports SDXL model search (Data source update and full of restart webui update required) and filter model by tags. Fixed model loading error.</br>
-1.60 Add VRAM garbage collection for image generation so that VRAM is freed up after every run; if your run into out of memory, just go to Boot Assistant and click "VRAM Release" to free up the memory.</br>
-1.50 Rewrote how assets are loaded to largely reduce the size and installation time for the extension. (extension reinstall is needed for this version and up). Added download covers for all models.</br>
-1.40 Add new feature for using GPT to generate prompts. Fixed sub folder support for model management</br>
-1.30 Add support for LyCoris(just put them in the lora folder, <a herf="">LyCoris extension</a> is needed.); Cleanup work for git to reduce project size</br>
-1.20 Add support for model search. Allow model to load directly from model management. Now you can update model source directly under update tab.</br>
-1.10 Add support for Lora, embedding and hypernetwork models under model manangement. bug fixes.

### Installation
In Automatic1111 WebUI, go to `Extensions Tab`->`Install from URL`, copy the following address in "**URL for extension's git repository**".

```sh
https://github.com/miaoshouai/miaoshouai-assistant.git
```

Click `Install`, wait until it's done. Go to `Settings`-> `Reload UI`

### Usage

##### Boot Assistant

<p align="center">
   <img src="https://msdn.miaoshouai.com/msai/kt/ez/boot_assistant_en.png"/>
</p>

- Allows you to change your webui boot settings including:
GPU optimization, UI Theme, enable port listening, xformers, auto launch, etc.

- Allows you to save all your settings to your webui-user.bat/other boot script for your webui.

##### Model Management

<p align="center">
   <img src="https://msdn.miaoshouai.com/msai/kt/ez/model_manager_en.png"/>
</p>

- Allows you to view all your models and view the model civitai prompts and parameters from the covers.
You can easily send these civitai prompts to txt2img/img2img/inpainting/extra

##### Model Downloader

<p align="center">
   <img src="https://msdn.miaoshouai.com/msai/kt/ez/model_downloader.gif"/>
</p>

- Allows you to search and download models from civitai.com or miaoshouai.com, find the model type you want

<p align="center">
   <img src="https://msdn.miaoshouai.com/msai/kt/ez/controlnet_download.gif"/>
</p>

- It also allows you to find 1.5, 2.1 official models, controlnet models or different vae models.

