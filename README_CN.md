# 喵手助理
[English](README.md) / [中文](README_CN.md)

喵手助理 [Automatic1111 WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)

1.80 增加了喵手AI作为模型源，让不能访问C站的人可以通过喵手AI源作为下载站点；增加了部分controlnet模型和官方模型的下载源
1.80 修复了webui 1.60中的下载问题；增加了对模型排序，子文件夹下载，模型版本等功能的支持。</br>
1.70 优化了Civitai的模型文件名关键词搜索，SDXL模型搜索（需要更新数据源），支持tag筛选。修复了在1.6下的模型加载问题。</br>
1.60 增加了显存自动清理功能。在启动助手中启用后可以在每次生图后自动清理显存。</br>
1.50 重构了assets的读取方式，大幅减少了下载时间和插件大小（使用1.5+版本需要重新安装）; 增加了一键下载封面功能。</br>
1.40 添加了使用GPT来生成咒语的功能; 修复了模型管理中对子文件夹的支持。</br>
1.30 增加了模型下载和管理功能中对LyCoris的支持(你需要将LoCoris模型放置在Lora目录下, 需要安装<a herf="https://github.com/KohakuBlueleaf/a1111-sd-webui-lycoris"> LyCoris插件 </a>)</br>
1.20 增加了模型搜索功能，可以直接在模型管理下load模型，增加了插件和模型源更新功能。</br>
1.10 模型管理下增加了对Lora, embedding and hypernetwork等模型的支持。修复了启动时与秋叶启动器的冲突。

### 安装
在 Automatic1111 WebUI 中，前往 `扩展插件`-> `从URL安装`，在`扩展插件的git仓库网址`中复制以下地址。

```sh
https://github.com/miaoshouai/miaoshouai-assistant.git
```

点击`安装`，等待安装完成。然后前往`设置` -> `重新加载界面`

### 使用方法
##### 启动助手

<p align="center">
   <img src="https://msdn.miaoshouai.com/msai/kt/ez/boot_assistant_en.png"/>
</p>

- 允许您更改 WebUI 启动设置，包括：
GPU 优化、UI 主题、启用端口监听、xformers、自动启动等。

- 允许您将所有设置保存到 webui-user.bat/其他启动脚本。

##### 模型管理

<p align="center">
   <img src="https://msdn.miaoshouai.com/msai/kt/ez/model_manager.png"/>
</p>

- 允许您查看所有模型，并从封面查看模型 civitai 提示和参数。
您可以非常容易的将 civitai 提示词发送到 txt2img/img2img/inpainting/extra

##### 模型下载器

<p align="center">
   <img src="https://msdn.miaoshouai.com/msai/kt/ez/model_downloader.gif"/>
</p>

- 允许您从 civitai.com 或 miaoshouai.com 搜索和下载模型，找到您想要的模型类型

<p align="center">
   <img src="https://msdn.miaoshouai.com/msai/kt/ez/controlnet_download.gif"/>
</p>

- 喵手助理还能让您找到 1.5, 2.1 的官方模型、controlnet 模型以及不同的 vae 模型。
