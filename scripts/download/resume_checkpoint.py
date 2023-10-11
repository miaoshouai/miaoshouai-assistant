import os
import glob
import pathlib
import pickle
import typing as t
from sha256bit import Sha256bit


class ResumeCheckpoint(object):
    VERSION_FILENAME = ".version_2.0"

    @staticmethod
    def load_resume_checkpoint(filename: str) -> t.Tuple[int, Sha256bit | None]:
        try:
            with open(filename, "rb") as file:
                (resume_point, hash_state) = pickle.load(file)
                return resume_point, Sha256bit.import_state(hash_state)
        except Exception as ex:
            print(f"Error: {ex}")

        return 0, None

    @staticmethod
    def store_resume_checkpoint(resume_point: int, checksum: Sha256bit, filename: str) -> bool:
        try:
            with open(filename, "wb") as file:
                pickle.dump((resume_point, checksum.export_state()), file)
                return True
        except Exception as ex:
            print(f"Error: {ex}")
            return False

    @staticmethod
    def cleanup_checkpoints_if_needed(checkpoint_dir: str) -> None:
        version_file = os.path.join(checkpoint_dir, ResumeCheckpoint.VERSION_FILENAME)
        if os.path.isfile(version_file):
            print("already version 2")
            return

        for file in glob.glob(os.path.join(checkpoint_dir, "*.downloading")):
            print(f"delete checkpoint file with old version: {file}")
            os.remove(file)

    @staticmethod
    def store_version_info(checkpoint_dir: str) -> bool:
        try:
            with open(os.path.join(checkpoint_dir, ResumeCheckpoint.VERSION_FILENAME), "wb") as file:
                file.write(f"version is {ResumeCheckpoint.VERSION_FILENAME}".encode())
                return True
        except Exception as ex:
            print(f"Store Version Info Error: {ex}")
