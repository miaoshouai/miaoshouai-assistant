import launch
import os
import gzip
import io
from scripts.runtime.msai_prelude import MiaoshouPrelude


def install_preset_models_if_needed():
    assets_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets")
    configs_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "configs")

    for model_filename in ["civitai_models.json", "liandange_models.json"]:
        gzip_file = os.path.join(assets_folder, f"{model_filename}.gz")
        target_file = os.path.join(configs_folder, f"{model_filename}")
        if not os.path.exists(target_file):
            with gzip.open(gzip_file, "rb") as compressed_file:
                with io.TextIOWrapper(compressed_file, encoding="utf-8") as decoder:
                    content = decoder.read()
                    with open(target_file, "w") as model_file:
                        model_file.write(content)

def create_folders():
    prelude = MiaoshouPrelude()
    os.mkdir(prelude.cover_folder)
    os.mkdir(prelude.cache_folder)

req_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "requirements.txt")

with open(req_file) as file:
    for lib in file:
        lib = lib.strip()
        if not launch.is_installed(lib):
            launch.run_pip(f"install {lib}", f"Miaoshou assistant requirement: {lib}")

install_preset_models_if_needed()
create_folders()

