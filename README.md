# miaoshouai-assistant

[English](README.md) / [中文](README_CN.md)

MiaoshouAI Assistant for [Automatic1111 WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)

1.7 Improved search capability for Civitai to include keyword search in model names; Now supports SDXL model search (Data source update and full of restart webui update required) and filter model by tags. Fixed model loading error.
1.6 Add VRAM garbage collection for image generation so that VRAM is freed up after every run; if your run into out of memory, just go to Boot Assistant and click "VRAM Release" to free up the memory.
1.5 Rewrote how assets are loaded to largely reduce the size and installation time for the extension. (extension reinstall is needed for this version and up). Added download covers for all models.
1.4 Add new feature for using GPT to generate prompts. Fixed sub folder support for model management</br>
1.3 Add support for LyCoris(just put them in the lora folder, <a herf="">LyCoris extension</a> is needed.); Cleanup work for git to reduce project size</br>
1.2 Add support for model search. Allow model to load directly from model management. Now you can update model source directly under update tab.</br>
1.1 Add support for Lora, embedding and hypernetwork models under model manangement. bug fixes.

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

- Allows you to search and download models from civitai.com or liandange.com, find the model type you want

<p align="center">
   <img src="https://msdn.miaoshouai.com/msai/kt/ez/controlnet_download.gif"/>
</p>

- It also allows you to find 1.5, 2.1 official models, controlnet models or different vae models.

