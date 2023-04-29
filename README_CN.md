# 喵手助理
[English](README.md) / [中文](README_CN.md)

1.1 版更新: 模型管理下增加了对Lora, embedding and hypernetwork等模型的支持。修复了启动时与秋叶启动器的冲突。

喵手助理 [Automatic1111 WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)

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

- 允许您从 civitai.com 或 liandange.com 搜索和下载模型，找到您想要的模型类型

<p align="center">
   <img src="https://msdn.miaoshouai.com/msai/kt/ez/controlnet_download.gif"/>
</p>

- 喵手助理还能让您找到 1.5, 2.1 的官方模型、controlnet 模型以及不同的 vae 模型。
