import os
import sys
import typing as t

import gradio as gr

import launch
import modules
from scripts.logging.msai_logger import Logger
from scripts.runtime.msai_prelude import MiaoshouPrelude
from scripts.runtime.msai_runtime import MiaoshouRuntime


class MiaoShouAssistant(object):
    # default css definition
    default_css = '#my_model_cover{width: 100px;} #my_model_trigger_words{width: 200px;}'

    def __init__(self) -> None:
        self.logger = Logger()
        self.prelude = MiaoshouPrelude()
        self.runtime = MiaoshouRuntime()
        self.refresh_symbol = '\U0001f504'

    def on_event_ui_tabs_opened(self) -> t.List[t.Optional[t.Tuple[t.Any, str, str]]]:
        with gr.Blocks(analytics_enabled=False, css=MiaoShouAssistant.default_css) as miaoshou_assistant:
            self.create_subtab_boot_assistant()
            self.create_subtab_model_management()
            self.create_subtab_model_download()

        return [(miaoshou_assistant.queue(), "Miaoshou Assistant", "miaoshou_assistant")]

    def create_subtab_boot_assistant(self) -> None:
        with gr.TabItem('Boot Assistant', elem_id="boot_assistant_tab") as boot_assistant:
            with gr.Row():
                with gr.Column(elem_id="col_model_list"):
                    gpu, theme, port, chk_args, txt_args, webui_ver = self.runtime.get_default_args()
                    gr.Markdown(value="Argument settings")
                    with gr.Row():
                        drp_gpu = gr.Dropdown(label="", elem_id="drp_args_vram",
                                              choices=list(self.prelude.gpu_setting.keys()),
                                              value=gpu, interactive=True)
                        drp_theme = gr.Dropdown(label="UI Theme", choices=list(self.prelude.theme_setting.keys()),
                                                value=theme,
                                                elem_id="drp_args_theme", interactive=True)
                        txt_listen_port = gr.Text(label='Listen Port', value=port, elem_id="txt_args_listen_port",
                                                  interactive=True)

                    with gr.Row():
                        chk_group_args = gr.CheckboxGroup(choices=list(self.prelude.checkboxes.keys()), value=chk_args,
                                                          show_label=False)
                    additional_args = gr.Text(label='COMMANDLINE_ARGS (Divide by space)', value=txt_args,
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
                            save_settings = gr.Button(value="Save settings", elem_id="btn_arg_save_setting")

                    with gr.Row():
                        # with gr.Column():
                        #    settings_submit = gr.Button(value="Apply settings", variant='primary', elem_id="ms_settings_submit")
                        # with gr.Column():
                        restart_gradio = gr.Button(value='Apply & Restart WebUI', variant='primary',
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
                                        inputs=[drp_choose_version, drp_gpu, drp_theme, txt_listen_port, chk_group_args,
                                                additional_args], outputs=[txt_save_status])

                    restart_gradio.click(
                        fn=self.request_restart,
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

        drp_gpu.change(self.runtime.update_xformers, inputs=[drp_gpu, chk_group_args], outputs=[chk_group_args])
        sys_info_refbtn.click(self.prelude.get_sys_info, None, txt_sys_info)

    def create_subtab_model_management(self) -> None:
        with gr.TabItem('Model Management', elem_id="model_management_tab") as tab_batch:
            with gr.Row():
                with gr.Column():
                    my_models = self.runtime.get_local_models()
                    ds_my_models = gr.Dataset(
                        components=[gr.HTML(visible=False, label='Cover', elem_id='my_model_cover'),
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
                    html_model_prompt = gr.HTML(visible=True,
                                                value='<div style="height:400px;"><p>No Model Selected</p></div>')

            with gr.Row():
                add = gr.Button(value="Add", variant="primary")
                # delete = gr.Button(value="Delete")
            with gr.Row():
                reset_btn = gr.Button(value="Reset")
                json_input = gr.Button(value="Load from JSON")
                png_input = gr.Button(value="Detect from image")
                png_input_area = gr.Image(label="Detect from image", elem_id="openpose_editor_input")
                bg_input = gr.Button(value="Add Background image")

    def create_subtab_model_download(self) -> None:
        with gr.TabItem('Model Download', elem_id="model_download_tab") as tab_downloads:
            with gr.Row():
                with gr.Column(elem_id="col_model_list"):
                    with gr.Row().style(equal_height=True):
                        model_source_dropdown = gr.Dropdown(choices=["civitai", "liandange"],
                                                            value=self.runtime.model_source,
                                                            label="Select Model Source",
                                                            type="value",
                                                            show_label=True,
                                                            elem_id="model_source").style(full_width=True)
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

                        is_civitai_model_source_active = self.runtime.model_source == "civitai"
                        with gr.Row(variant="panel"):
                            dwn_button = gr.Button(value='Download',
                                                   visible=is_civitai_model_source_active, elem_id='ms_dwn_button')
                            open_url_in_browser_newtab_button = gr.HTML(
                                value='<p style="text-align: center;">'
                                      '<a style="text-align: center;" href="https://models.paomiantv.cn/models" '
                                      'target="_blank">Download</a></p>',
                                visible=not is_civitai_model_source_active)
                    with gr.Row():
                        model_info = gr.HTML(visible=True)

        nsfw_checker.change(self.runtime.set_nsfw, inputs=[search_text, nsfw_checker, model_type],
                            outputs=self.runtime.ds_models)

        model_type.change(self.runtime.search_model, inputs=[search_text, model_type], outputs=self.runtime.ds_models)

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
                                     outputs=[self.runtime.ds_models, dwn_button, open_url_in_browser_newtab_button])

    def request_restart(self, drp_gpu, drp_theme, txt_listen_port, chk_group_args, additional_args):
        print('request_restart: cmd_arg  = ', self.runtime.cmdline_args)
        print('request_restart: sys.argv = ', sys.argv)

        modules.shared.state.interrupt()
        modules.shared.state.need_restart = True

        # reset args
        sys.argv = [sys.argv[0]]
        os.environ['COMMANDLINE_ARGS'] = ""
        print('remove', sys.argv)

        for arg in self.runtime.cmdline_args:
            sys.argv.append(arg)

        print('after', sys.argv)
        launch.prepare_environment()
        launch.start()

    def switch_model_source(self, new_model_source: str):
        self.runtime.model_source = new_model_source
        show_download_button = self.runtime.model_source == "civitai"
        images = self.runtime.get_images_html()
        self.runtime.ds_models.samples = images
        return (
            gr.Dataset.update(samples=images),
            gr.Button.update(visible=show_download_button),
            gr.HTML.update(visible=not show_download_button)
        )

    def introception(self) -> None:
        self.runtime.introception()
