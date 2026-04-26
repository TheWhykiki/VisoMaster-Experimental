from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

cv2_module = types.ModuleType("cv2")
cv2_module.VideoCapture = object
cv2_module.COLOR_GRAY2BGR = 0
cv2_module.COLOR_RGBA2BGR = 1
cv2_module.INTER_LANCZOS4 = 0
cv2_module.IMWRITE_JPEG_QUALITY = 1
cv2_module.IMWRITE_JPEG_OPTIMIZE = 2
cv2_module.IMWRITE_JPEG_PROGRESSIVE = 3
cv2_module.CAP_PROP_FRAME_WIDTH = 4
cv2_module.CAP_PROP_FRAME_HEIGHT = 5
cv2_module.IMREAD_COLOR = 1
sys.modules.setdefault("cv2", cv2_module)
if "torchvision" not in sys.modules:
    torchvision_module = types.ModuleType("torchvision")
    transforms_module = types.ModuleType("torchvision.transforms")
    transforms_module.v2 = types.SimpleNamespace()
    torchvision_module.transforms = transforms_module
    sys.modules["torchvision"] = torchvision_module
    sys.modules["torchvision.transforms"] = transforms_module

from app.helpers.miscellaneous import FluxLoraManager, FluxModelManager
from app.processors.models_data import FLUX_FILL_AUTO_OPTION


class FluxModelDiscoveryTest(unittest.TestCase):
    def test_flux_manager_discovers_comfyui_diffusers_folder_from_env(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            local_dir = Path(tmp_dir) / "local"
            comfy_root = Path(tmp_dir) / "ComfyUI_Models" / "models"
            flux_dir = comfy_root / "diffusers" / "FLUX.1-Fill-dev"
            (flux_dir / "transformer").mkdir(parents=True)
            (flux_dir / "model_index.json").write_text("{}", encoding="utf-8")

            with mock.patch.dict(
                "os.environ",
                {"VISOMASTER_COMFYUI_MODELS_PATH": str(comfy_root)},
            ):
                manager = FluxModelManager(str(local_dir))

            values = manager.get_selection_values()
            self.assertIn(FLUX_FILL_AUTO_OPTION, values)
            self.assertIn("FLUX.1-Fill-dev", values)
            self.assertEqual(str(flux_dir), manager.get_model_path("FLUX.1-Fill-dev"))

    def test_flux_lora_manager_discovers_comfyui_loras_from_env(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            local_dir = Path(tmp_dir) / "local"
            comfy_root = Path(tmp_dir) / "ComfyUI_Models" / "models"
            lora_path = comfy_root / "loras" / "ace_plus_portrait_lora64.safetensors"
            lora_path.parent.mkdir(parents=True)
            lora_path.write_bytes(b"fake-lora")

            with mock.patch.dict(
                "os.environ",
                {"VISOMASTER_COMFYUI_MODELS_PATH": str(comfy_root)},
            ):
                manager = FluxLoraManager(str(local_dir))

            values = manager.get_selection_values()
            self.assertIn("ace_plus_portrait_lora64.safetensors", values)
            self.assertEqual(
                str(lora_path),
                manager.get_model_path("ace_plus_portrait_lora64.safetensors"),
            )


if __name__ == "__main__":
    unittest.main()
