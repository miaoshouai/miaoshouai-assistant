import os
import sys
import typing as t

import gradio as gr

import launch
import modules
from modules import shared
from scripts.logging.msai_logger import Logger
from scripts.runtime.msai_prelude import MiaoshouPrelude
from scripts.runtime.msai_runtime import MiaoshouRuntime
import modules.generation_parameters_copypaste as parameters_copypaste
from modules.ui_components import ToolButton


class MiaoShouAssistant(object):
    # default css definition
    default_css = '#my_model_cover{width: 100px;} #my_model_trigger_words{width: 200px;}'

    def __init__(self) -> None:
        self.logger = Logger()
        self.prelude = MiaoshouPrelude()
        self.runtime = MiaoshouRuntime()
        self.refresh_symbol = '\U0001f504'
        self.coffee_symbol = '\U0001f9cb' # 🧋
        self.folder_symbol = '\U0001f4c2'  # 📂

    def on_event_ui_tabs_opened(self) -> t.List[t.Optional[t.Tuple[t.Any, str, str]]]:
        with gr.Blocks(analytics_enabled=False, css=MiaoShouAssistant.default_css) as miaoshou_assistant:
            self.create_subtab_boot_assistant()
            self.create_subtab_model_management()
            self.create_subtab_model_download()
            self.create_subtab_about()

        return [(miaoshou_assistant.queue(), "Miaoshou Assistant", "miaoshou_assistant")]

    def create_subtab_boot_assistant(self) -> None:
        with gr.TabItem('Boot Assistant', elem_id="boot_assistant_tab") as boot_assistant:
            with gr.Row():
                with gr.Column(elem_id="col_model_list"):
                    gpu, theme, port, chk_args, txt_args, webui_ver = self.runtime.get_default_args()
                    gr.Markdown(value="Argument settings")
                    with gr.Row():
                        self.drp_gpu = gr.Dropdown(label="VRAM Size", elem_id="drp_args_vram",
                                              choices=list(self.prelude.gpu_setting.keys()),
                                              value=gpu, interactive=True)
                        self.drp_theme = gr.Dropdown(label="UI Theme", choices=list(self.prelude.theme_setting.keys()),
                                                value=theme,
                                                elem_id="drp_args_theme", interactive=True)
                        self.txt_listen_port = gr.Text(label='Listen Port', value=port, elem_id="txt_args_listen_port",
                                                  interactive=True)

                    with gr.Row():

                        self.chk_group_args = gr.CheckboxGroup(choices=list(self.prelude.checkboxes.keys()), value=chk_args,
                                                          show_label=False)
                    self.additional_args = gr.Text(label='COMMANDLINE_ARGS (Divide by space)', value=txt_args,
                                              elem_id="txt_args_more", interactive=True)

                    with gr.Row():
                        with gr.Column():
                            txt_save_status = gr.Markdown(visible=False, interactive=False, show_label=False)
                            drp_choose_version = gr.Dropdown(label="WebUI Version",
                                                             choices=['Official Release', 'Python Integrated'],
                                                             value=webui_ver, elem_id="drp_args_version",
                                                             interactive=True)
                            gr.HTML(
                                '<div><p>*Save your settings to webui-user.bat file. Use Python Integrated only if your'
                                ' WebUI is extracted from a zip file and does not need python installation</p></div>')
                            save_settings = gr.Button(value="Save Boot Settings", elem_id="btn_arg_save_setting")

                    with gr.Row():
                        # with gr.Column():
                        #    settings_submit = gr.Button(value="Apply settings", variant='primary', elem_id="ms_settings_submit")
                        # with gr.Column():
                        btn_apply = gr.Button(value='Apply Settings', variant='primary',
                                                   elem_id="ms_settings_restart_gradio")
                        restart_gradio = gr.Button(value='Restart WebUI', variant='primary',
                                                   elem_id="ms_settings_restart_gradio")

                        '''def mod_args(drp_gpu, drp_theme, txt_listen_port, chk_group_args, additional_args):
                          global commandline_args
      
                          get_final_args(drp_gpu, drp_theme, txt_listen_port, hk_group_args, additional_args)
      
                          print(commandline_args)
                          print(sys.argv)
                          #if '--xformers' not in sys.argv:
                            #sys.argv.append('--xformers')
      
                        settings_submit.click(mod_args, inputs=[drp_gpu, drp_theme, txt_listen_port, chk_group_args, additional_args], outputs=[])'''

                    save_settings.click(self.runtime.change_boot_setting,
                                        inputs=[drp_choose_version, self.drp_gpu, self.drp_theme, self.txt_listen_port, self.chk_group_args,
                                                self.additional_args], outputs=[txt_save_status])
                    btn_apply.click(
                        self.save_cmdline_args,
                        inputs=[self.drp_gpu, self.drp_theme, self.txt_listen_port, self.chk_group_args,
                                self.additional_args],
                        outputs=[txt_save_status],
                    )

                    def request_restart():
                        shared.state.interrupt()
                        shared.state.need_restart = True
                        launch.prepare_environment()
                        #launch.start()

                    restart_gradio.click(
                        request_restart,
                        _js='restart_reload',
                        inputs=[],
                        outputs=[],
                    )

                with gr.Column():
                    with gr.Row():
                        machine_settings = self.prelude.get_sys_info()
                        txt_sys_info = gr.TextArea(value=machine_settings, lines=20, max_lines=20,
                                                   label="System Info",
                                                   show_label=False, interactive=False)
                    with gr.Row():
                        sys_info_refbtn = gr.Button(value="Refresh")



        self.drp_gpu.change(self.runtime.update_xformers, inputs=[self.drp_gpu, self.chk_group_args], outputs=[self.chk_group_args])
        sys_info_refbtn.click(self.prelude.get_sys_info, None, txt_sys_info)


    def create_subtab_model_management(self) -> None:
        with gr.TabItem('Model Management', elem_id="model_management_tab") as tab_batch:
            with gr.Row():
                with gr.Column():
                    with gr.Row():
                        gr.Markdown(value="If you want your model directory to be other than [your_webui_dir]\\models, select a new directory down below. "
                                          "Your default models directory needs to be removed first before you apply. Make sure do your backups!")
                        md_result = gr.Markdown(visible=False, value="")
                    with gr.Row():
                        model_folder_path = gr.Textbox("", label="Model path", placeholder="Copy & paste your model destination folder here", interactive=True)
                        #open_folder_button = ToolButton(value=self.folder_symbol, elem_id="hidden_element" if shared.cmd_opts.hide_ui_dir_config else "open_folder_metadata_editor")
                        refresh_models_button = ToolButton(value=self.refresh_symbol, elem_id="hidden_element")
                    with gr.Row():
                        btn_connect_modeldir = gr.Button(value="Apply Virtual Model Folder")

                    with gr.Row():
                        my_models = self.runtime.get_local_models()
                        self.runtime.ds_my_models = gr.Dataset(
                            components=[gr.Image(visible=False, label='Cover', elem_id='my_model_cover'),
                                        gr.Textbox(visible=False, label='ModelId'),
                                        gr.Textbox(visible=False, label='Name/Version'),
                                        gr.Textbox(visible=False, label='File Name'),
                                        gr.Textbox(visible=False, label='Hash'), gr.Textbox(visible=False, label='Creator'),
                                        gr.Textbox(visible=False, label='Type'), gr.Textbox(visible=False, label='NSFW'),
                                        gr.Textbox(visible=False, label='Trigger Words', elem_id='my_model_trigger_words')],
                            elem_id='my_model_lib',
                            label="My Models",
                            headers=None,
                            samples=my_models,
                            samples_per_page=50)
                with gr.Column():
                    self.runtime.ds_my_model_covers = gr.Dataset(components=[gr.HTML(visible=False)],
                                                    elem_id='my_model_covers',
                                                    label="Model Cover",
                                                    headers=None,
                                                    samples=[],
                                                    samples_per_page=10)
                    with gr.Row(variant='panel'):
                        btn_set_cover = gr.Button(visible=False, value='Set as Cover')
                    with gr.Row(variant='panel'):
                        c_image = gr.Image(elem_id="pnginfo_image", label="Source", source="upload", interactive=True,
                                         type="pil", visible=False)

                    with gr.Row(variant='panel'):
                        generation_info = gr.Textbox(label='prompt', interactive=False, visible=True, elem_id="imginfo_generation_info")

                    with gr.Row(variant='panel'):
                        with gr.Row():
                            buttons = parameters_copypaste.create_buttons(["txt2img", "img2img", "inpaint", "extras"])

                        for tabname, button in buttons.items():
                            parameters_copypaste.register_paste_params_button(parameters_copypaste.ParamBinding(
                                paste_button=button, tabname=tabname, source_text_component=generation_info,
                                source_image_component=c_image,
                            ))

        btn_set_cover.click(self.runtime.set_cover, inputs=[self.runtime.ds_my_models, c_image], outputs=[self.runtime.ds_my_models])
        #open_folder_button.click(self.runtime.open_folder, inputs=[model_folder_path], outputs=[model_folder_path])
        btn_connect_modeldir.click(self.runtime.change_model_folder, inputs=[model_folder_path], outputs=[md_result])
        refresh_models_button.click(self.runtime.refresh_local_models, inputs=[], outputs=[self.runtime.ds_my_models])

        self.runtime.ds_my_models.click(self.runtime.get_my_model_covers,
                                     inputs=[self.runtime.ds_my_models],
                                     outputs=[self.runtime.ds_my_model_covers])

        self.runtime.ds_my_model_covers.click(self.runtime.update_cover_info,
                                        inputs=[self.runtime.ds_my_models, self.runtime.ds_my_model_covers],
                                        outputs=[btn_set_cover, generation_info, c_image])


    def create_subtab_model_download(self) -> None:
        with gr.TabItem('Model Download', elem_id="model_download_tab") as tab_downloads:
            with gr.Row():
                with gr.Column(elem_id="col_model_list"):
                    with gr.Row().style(equal_height=True):
                        model_source_dropdown = gr.Dropdown(choices=["civitai.com", "liandange.com", "official_models", "controlnet"],
                                                            value=self.runtime.model_source,
                                                            label="Select Model Source",
                                                            type="value",
                                                            show_label=True,
                                                            elem_id="model_source").style(full_width=True)

                        #btn_fetch = gr.Button("Fetch")

                    with gr.Row().style(equal_height=True):
                        search_text = gr.Textbox(
                            label="Model name",
                            show_label=False,
                            max_lines=1,
                            placeholder="Enter model name",
                        )
                        btn_search = gr.Button("Search")

                    with gr.Row().style(equal_height=True):
                        nsfw_checker = gr.Checkbox(label='NSFW', value=False, elem_id="chk_nsfw", interactive=True)
                        model_type = gr.Radio(["All", "Checkpoint", "LORA", "TextualInversion", "Hypernetwork"],
                                              show_label=False, value='All', elem_id="rad_model_type",
                                              interactive=True).style(full_width=True)

                    images = self.runtime.get_images_html()
                    self.runtime.ds_models = gr.Dataset(
                        components=[gr.HTML(visible=False)],
                        headers=None,
                        type="values",
                        label="Models",
                        samples=images,
                        samples_per_page=60,
                        elem_id="model_dataset").style(type="gallery", container=True)

                with gr.Column(elem_id="col_model_info"):
                    with gr.Row():
                        cover_gallery = gr.Gallery(label="Cover", show_label=False, visible=True).style(grid=[4],
                                                                                                        height="2")

                    with gr.Row():
                        with gr.Column():
                            download_summary = gr.HTML('<div><span>No downloading tasks ongoing</span></div>')
                            downloading_status = gr.Button(value=f"{self.refresh_symbol} Refresh Downloading Status",
                                                           elem_id="ms_dwn_status")
                    with gr.Row():
                        model_dropdown = gr.Dropdown(choices=['Select Model'], label="Models", show_label=False,
                                                     value='Select Model', elem_id='ms_dwn_button',
                                                     interactive=True)

                        is_civitai_model_source_active = self.runtime.model_source == "civitai.com"
                        with gr.Row(variant="panel"):
                            dwn_button = gr.Button(value='Download',
                                                   visible=is_civitai_model_source_active, elem_id='ms_dwn_button')
                            open_url_in_browser_newtab_button = gr.HTML(
                                value='<p style="text-align: center;">'
                                      '<a style="text-align: center;" href="http://www.liandange.com/models" '
                                      'target="_blank">Download</a></p>',
                                visible=not is_civitai_model_source_active)
                    with gr.Row():
                        model_info = gr.HTML(visible=True)

        nsfw_checker.change(self.runtime.set_nsfw, inputs=[search_text, nsfw_checker, model_type],
                            outputs=self.runtime.ds_models)

        model_type.change(self.runtime.search_model, inputs=[search_text, model_type], outputs=self.runtime.ds_models)

        #btn_fetch.click(self.runtime.refresh_all_models, inputs=[], outputs=self.runtime.ds_models)

        btn_search.click(self.runtime.search_model, inputs=[search_text, model_type], outputs=self.runtime.ds_models)

        self.runtime.ds_models.click(self.runtime.get_model_info,
                                     inputs=[self.runtime.ds_models],
                                     outputs=[
                                         cover_gallery,
                                         model_dropdown,
                                         model_info,
                                         open_url_in_browser_newtab_button
                                     ])

        dwn_button.click(self.runtime.download_model, inputs=[model_dropdown], outputs=[download_summary])
        downloading_status.click(self.runtime.get_downloading_status, inputs=[], outputs=[download_summary])

        model_source_dropdown.change(self.switch_model_source,
                                     inputs=[model_source_dropdown],
                                     outputs=[self.runtime.ds_models, self.runtime.ds_my_models, dwn_button, open_url_in_browser_newtab_button])

    def create_subtab_about(self) -> None:
        with gr.TabItem('About', elem_id="about_tab") as tab_about:
            with gr.Row():
                gr.HTML(
                    f"""
                    <div><p>
                    This extension is created to improve some of the use experience for automatic1111 webui.</br>
                    It is free of charge, use it as you wish, please DO NOT sell this extension.</br>
                    Follow us on github, discord and give us suggestions, report bugs. support us with love or coffee~</br></br>
                    Cheers~</p>
                    <p style="text-align: left;">
                        <a target="_blank" href="https://github.com/miaoshouai/miaoshouai-assistant"><img src="https://img.shields.io/github/followers/miaoshouai?style=social" style="display: inline;" alt="MiaoshouAI GitHub"/></a>
                        <a href="https://discord.gg/S22Jgn3rtz"><img src="https://img.shields.io/discord/1086407792451129374?label=Discord" style="display: inline;" alt="Discord server"></a>|
                        <a target="_blank" href='https://www.buymeacoffee.com/miaoshou'>【buy me coffee~ \U0001f9cb】</a>|
                        <a target="_blank" href="https://jq.qq.com/?_wv=1027&k=p5ZhOHAh">【QQ群：256734228】</a>|
                        <a target="_blank" href='https://t.zsxq.com/0d6EqTqDN'>【加入异能AI研究所-知识星球】</a>|
                        <a target="_blank" href='https://docs.qq.com/doc/DY0pVZWJUWWRHa0tM'>【其它你可能用得到的】</a>
                    </p>

                    """
                )

    def save_cmdline_args(self, drp_gpu, drp_theme, txt_listen_port, chk_group_args, additional_args):
        #print(drp_gpu, drp_theme, txt_listen_port, chk_group_args, additional_args)
        self.runtime.get_final_args(drp_gpu, drp_theme, txt_listen_port, chk_group_args, additional_args)
        #print('request_restart: cmd_arg  = ', self.runtime.cmdline_args)
        #print('request_restart: sys.argv = ', sys.argv)

        # reset args
        sys.argv = [sys.argv[0]]
        os.environ['COMMANDLINE_ARGS'] = ""
        #print('remove', sys.argv)

        for arg in list(dict.fromkeys(self.runtime.cmdline_args)):
            sys.argv.append(arg)

        print('saved args', sys.argv)
        #launch.start()
        return gr.Markdown.update(value="Settings Saved", visible=True)

    def switch_model_source(self, new_model_source: str):
        self.runtime.model_source = new_model_source
        show_download_button = self.runtime.model_source != "liandange.com"
        images = self.runtime.get_images_html()
        self.runtime.ds_models.samples = images
        my_models = self.runtime.get_local_models()
        self.runtime.ds_my_models.samples = my_models

        return (
            gr.Dataset.update(samples=images),
            gr.Dataset.update(samples=my_models),
            gr.Button.update(visible=show_download_button),
            gr.HTML.update(visible=not show_download_button)
        )

    def introception(self) -> None:
        self.runtime.introception()
