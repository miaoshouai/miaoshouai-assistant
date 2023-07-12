import modules
import modules.scripts as scripts

from scripts.assistant.miaoshou import MiaoShouAssistant
from scripts.runtime.msai_runtime import MiaoshouRuntime


class MiaoshouScript(scripts.Script):
    def __init__(self) -> None:
        super().__init__()

    def title(self):
        return "Miaoshou Assistant"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        return ()

    def postprocess(self, p, processed):
        self.runtime = MiaoshouRuntime()
        self.runtime.mem_release()
        return None

assistant = MiaoShouAssistant()
modules.script_callbacks.on_ui_tabs(assistant.on_event_ui_tabs_opened)
