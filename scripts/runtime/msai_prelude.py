import os
import platform
import sys
import typing as t

import psutil
import torch

import launch
from modules import shared
from scripts.msai_logging.msai_logger import Logger
from scripts.msai_utils import msai_toolkit as toolkit
from scripts.msai_utils.msai_singleton import MiaoshouSingleton
import modules


class MiaoshouPrelude(metaclass=MiaoshouSingleton):
    _dataset = None

    def __init__(self) -> None:
        # Potential race condition, not call in multithread environment
        if MiaoshouPrelude._dataset is None:
            self._init_constants()

            MiaoshouPrelude._dataset = {
                "log_folder": os.path.join(self.ext_folder, "logs")
            }

            disable_log_console_output: bool = False
            if self.all_settings.get("boot_settings"):
                if self.all_settings["boot_settings"].get("disable_log_console_output") is not None:
                    disable_log_console_output = self.all_settings["boot_settings"].get("disable_log_console_output")

            self._logger = Logger(self._dataset["log_folder"], disable_console_output=disable_log_console_output)

    def _init_constants(self) -> None:
        self._api_url = {
            "civitai.com": "https://civitai.com/api/v1/models",
            "liandange.com": "http://model-api.liandange.com/model/api/models",
        }
        self._ext_folder = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
        self._setting_file = os.path.join(self.ext_folder, "configs", "settings.json")
        self._model_hash_file = os.path.join(self.ext_folder, "configs", "model_hash.json")
        self._gpt_index = os.path.join(self.ext_folder, "configs", "gpt_index.json")
        self._assets_folder = os.path.join(self.ext_folder, "assets")
        self._cache_folder = os.path.join(self.ext_folder, "cache")
        self._cover_folder = os.path.join(self.ext_folder, "covers")
        self._no_preview_img = os.path.join(modules.paths.script_path, "html", "card-no-preview.png")
        self._model_json = {
            'civitai.com': os.path.join(self.ext_folder, 'configs', 'civitai_models.json'),
            'liandange.com': os.path.join(self.ext_folder, 'configs', 'liandange_models.json'),
            'official_models': os.path.join(self.ext_folder, 'configs', 'official_models.json'),
            'hugging_face': os.path.join(self.ext_folder, 'configs', 'hugging_face.json'),
            'controlnet': os.path.join(self.ext_folder, 'configs', 'controlnet.json')
        }
        self._checkboxes = {
            'Enable xFormers': '--xformers',
            'No Half': '--no-half',
            'No Half VAE': '--no-half-vae',
            'Enable API': '--api',
            'Auto Launch': '--autolaunch',
            'Allow Local Network Access': '--listen',
        }

        self._gpu_setting = {
            'CPU Only': '--precision full --no-half --use-cpu SD GFPGAN BSRGAN ESRGAN SCUNet CodeFormer --all',
            'GTX 16xx': '--lowvram --xformers --precision full --no-half',
            'Low: 4-6G VRAM': '--xformers --lowvram',
            'Med: 6-8G VRAM': '--xformers --medvram',
            'Normal: 8+G VRAM': '',
        }

        self._theme_setting = {
            'Auto': '',
            'Light Mode': '--theme light',
            'Dark Mode': '--theme dark',
        }
        self._ENV_EXCLUSION = ['COLAB_GPU', 'RUNPOD_POD_ID']
        self._model_type = {'Checkpoint': f'{os.path.join(shared.models_path,"Stable-diffusion")}',
                            'LORA': f'{os.path.join(shared.models_path,"Lora")}',
                            'LoCon': f'{os.path.join(shared.models_path, "Lora")}',
                            "TextualInversion": f'{os.path.join(shared.script_path,"embeddings")}',
                            "Hypernetwork": f'{os.path.join(shared.models_path,"hypernetworks")}'
        }

        self._gpt_type = ['gpt-3.5-turbo', 'text-davinci-003']

    @property
    def ext_folder(self) -> str:
        return self._ext_folder

    @property
    def log_folder(self) -> str:
        return self._dataset.get("log_folder")

    @property
    def all_settings(self) -> t.Any:
        return toolkit.read_json(self._setting_file)

    @property
    def boot_settings(self) -> t.Any:
        all_setting = self.all_settings
        if all_setting:
            return all_setting['boot_settings']
        else:
            return None

    def api_url(self, model_source: str) -> t.Optional[str]:
        return self._api_url.get(model_source)

    @property
    def setting_file(self) -> str:
        return self._setting_file

    @property
    def ENV_EXCLUSION(self) -> list[str]:
        return self._ENV_EXCLUSION

    @property
    def model_hash_file(self) -> str:
        return self._model_hash_file

    @property
    def gpt_index(self) -> str:
        return self._gpt_index

    @property
    def cache_folder(self) -> str:
        return self._cache_folder

    @property
    def assets_folder(self) -> str:
        return self._assets_folder

    @property
    def cover_folder(self) -> str:
        return self._cover_folder

    @property
    def no_preview_img(self) -> str:
        return self._no_preview_img

    @property
    def checkboxes(self) -> t.Dict[str, str]:
        return self._checkboxes

    @property
    def gpu_setting(self) -> t.Dict[str, str]:
        return self._gpu_setting

    @property
    def theme_setting(self) -> t.Dict[str, str]:
        return self._theme_setting

    @property
    def model_type(self) -> t.Dict[str, str]:
        return self._model_type

    @property
    def gpt_type(self) -> t.Dict[str, str]:
        return self._gpt_type

    @property
    def model_json(self) -> t.Dict[str, t.Any]:
        return self._model_json

    def update_model_json(self, site: str, models: t.Dict[str, t.Any]) -> None:
        if self._model_json.get(site) is None:
            self._logger.error(f"cannot save model info for {site}")
            return

        self._logger.info(f"{self._model_json[site]} updated")
        toolkit.write_json(self._model_json[site], models)

    def load(self) -> None:
        self._logger.info("start to do prelude")
        self._logger.info(f"cmdline args: {' '.join(sys.argv[1:])}")

    @classmethod
    def get_sys_info(cls) -> str:
        sys_info = 'System Information\n\n'

        sys_info += r'OS Name: {0} {1}'.format(platform.system(), platform.release()) + '\n'
        sys_info += r'OS Version: {0}'.format(platform.version()) + '\n'
        sys_info += r'WebUI Version: {0}'.format(
            f'https://github.com/AUTOMATIC1111/stable-diffusion-webui/commit/{launch.commit_hash()}') + '\n'
        sys_info += r'Torch Version: {0}'.format(getattr(torch, '__long_version__', torch.__version__)) + '\n'
        sys_info += r'Python Version: {0}'.format(sys.version) + '\n\n'
        sys_info += r'CPU: {0}'.format(platform.processor()) + '\n'
        sys_info += r'CPU Cores: {0}/{1}'.format(psutil.cpu_count(logical=False), psutil.cpu_count(logical=True)) + '\n'

        try:
            sys_info += r'CPU Frequency: {0} GHz'.format(round(psutil.cpu_freq().max/1000,2)) + '\n'
        except Exception as e:
            sys_info += r'CPU Frequency: N/A GHz' + '\n'

        sys_info += r'CPU Usage: {0}%'.format(psutil.cpu_percent()) + '\n\n'
        sys_info += r'RAM: {0}'.format(toolkit.get_readable_size(psutil.virtual_memory().total)) + '\n'
        sys_info += r'Memory Usage: {0}%'.format(psutil.virtual_memory().percent) + '\n\n'
        for i in range(torch.cuda.device_count()):
            sys_info += r'Graphics Card{0}: {1} ({2})'.format(i, torch.cuda.get_device_properties(i).name,
                                                              toolkit.get_readable_size(
                                                                  torch.cuda.get_device_properties(
                                                                      i).total_memory)) + '\n'
            sys_info += r'Available VRAM: {0}'.format(toolkit.get_readable_size(torch.cuda.mem_get_info(i)[0])) + '\n'

        return sys_info


