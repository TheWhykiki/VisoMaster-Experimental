from __future__ import annotations

import tempfile
import unittest
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

try:
    import torch
except ModuleNotFoundError:
    torch = types.ModuleType("torch")

    class FakeTensor:
        def __init__(self, array):
            self.array = np.asarray(array)

        @property
        def shape(self):
            return self.array.shape

        def permute(self, *dims):
            return FakeTensor(np.transpose(self.array, dims))

        def to(self, *_args, **_kwargs):
            return self

        def detach(self):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return self.array

    class FakeRandomValue:
        def item(self):
            return 123

    class FakeGenerator:
        def __init__(self, device=None):
            self.device = device
            self.seed = None

        def manual_seed(self, seed):
            self.seed = seed
            return self

    class FakeCuda:
        @staticmethod
        def is_available():
            return False

        @staticmethod
        def is_bf16_supported():
            return False

        @staticmethod
        def empty_cache():
            pass

    @contextmanager
    def fake_inference_mode():
        yield

    torch.Tensor = FakeTensor
    torch.Generator = FakeGenerator
    torch.float16 = "float16"
    torch.bfloat16 = "bfloat16"
    torch.float32 = "float32"
    torch.cuda = FakeCuda()
    torch.randint = lambda *_args, **_kwargs: FakeRandomValue()
    torch.from_numpy = lambda array: FakeTensor(array)
    torch.inference_mode = fake_inference_mode
    sys.modules["torch"] = torch

import app.processors.utils.flux_ace_plus as flux_module
from app.processors.models_data import (
    ACE_PORTRAIT_AUTO_OPTION,
    FLUX_FILL_AUTO_OPTION,
)
from app.processors.utils.flux_ace_plus import FluxAcePlusSwapper, FluxRuntime


class FakePipelineBase:
    def __init__(self, model_source: str):
        self.model_source = model_source
        self.loaded_lora = None
        self.adapter_weights = None
        self.last_kwargs = None

    @classmethod
    def from_pretrained(cls, model_source: str, **_kwargs):
        return cls(model_source)

    def set_progress_bar_config(self, **_kwargs):
        pass

    def enable_vae_slicing(self):
        pass

    def load_lora_weights(self, path: str, weight_name: str | None = None, **_kwargs):
        self.loaded_lora = (path, weight_name)

    def set_adapters(self, _adapter_names, adapter_weights):
        self.adapter_weights = adapter_weights

    def __call__(
        self,
        prompt=None,
        image=None,
        mask_image=None,
        num_inference_steps=None,
        guidance_scale=None,
        generator=None,
        width=None,
        height=None,
        output_type=None,
        max_sequence_length=None,
        strength=None,
        image_reference=None,
    ):
        self.last_kwargs = {
            "prompt": prompt,
            "image": image,
            "mask_image": mask_image,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "generator": generator,
            "width": width,
            "height": height,
            "output_type": output_type,
            "max_sequence_length": max_sequence_length,
            "strength": strength,
            "image_reference": image_reference,
        }
        return SimpleNamespace(images=[Image.new("RGB", (width, height), (24, 48, 96))])


class FakeFillPipeline(FakePipelineBase):
    pass


class FakeKontextPipeline(FakePipelineBase):
    pass


class FakeFluxManager:
    def __init__(self, paths: dict[str, str] | None = None):
        self.paths = paths or {}

    def refresh_models(self):
        pass

    def get_model_path(self, name: str) -> str:
        return self.paths.get(name, "")


class TestableFluxAcePlusSwapper(FluxAcePlusSwapper):
    def __init__(self, tmp_path: Path, model_paths: dict[str, str] | None = None):
        main_window = SimpleNamespace(
            flux_model_manager=FakeFluxManager(model_paths),
            flux_lora_manager=FakeFluxManager(),
        )
        super().__init__(SimpleNamespace(device="cpu", main_window=main_window))
        self.tmp_path = tmp_path
        self.lora_path = tmp_path / "ace_plus_portrait_lora64.safetensors"
        self.lora_path.write_bytes(b"fake-lora")

    def _get_runtime(self):
        return FluxRuntime(FakeFillPipeline, FakeKontextPipeline)

    def _download_flux_fill_model(self) -> str:
        model_dir = self.tmp_path / "FLUX.1-Fill-dev"
        model_dir.mkdir(parents=True, exist_ok=True)
        return str(model_dir)

    def _resolve_or_download_lora_path(self, _lora_name: str) -> str:
        return str(self.lora_path)


class FluxAcePlusSwapperTest(unittest.TestCase):
    def _base_parameters(self, use_source_reference: bool = False) -> dict:
        return {
            "FluxModelSelection": FLUX_FILL_AUTO_OPTION,
            "FluxLoraSelection": ACE_PORTRAIT_AUTO_OPTION,
            "FluxUseSourceReferenceToggle": use_source_reference,
            "FluxCPUOffloadToggle": True,
            "FluxLoRAStrengthDecimalSlider": 1.0,
            "FluxPromptText": "swap the masked face",
            "FluxNegativePromptText": "",
            "FluxStepsSlider": 4,
            "FluxGuidanceDecimalSlider": 3.5,
            "FluxSeedSlider": 123,
        }

    def _images(self):
        target = np.full((8, 8, 3), 120, dtype=np.uint8)
        source = np.full((8, 8, 3), 80, dtype=np.uint8)
        mask = np.ones((8, 8), dtype=np.float32)
        return target, source, mask

    def test_fill_model_uses_flux_fill_pipeline_without_reference_kwargs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            swapper = TestableFluxAcePlusSwapper(Path(tmp_dir))
            target, source, mask = self._images()

            result = swapper.run(target, source, mask, self._base_parameters())

            self.assertIsInstance(swapper.pipeline, FakeFillPipeline)
            self.assertEqual(tuple(result.shape), (3, 8, 8))
            self.assertIsInstance(result, torch.Tensor)
            self.assertIsNone(swapper.pipeline.last_kwargs["image_reference"])

    def test_fill_model_rejects_source_reference(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            swapper = TestableFluxAcePlusSwapper(Path(tmp_dir))
            target, source, mask = self._images()

            with self.assertRaisesRegex(RuntimeError, "Source Reference"):
                swapper.run(
                    target,
                    source,
                    mask,
                    self._base_parameters(use_source_reference=True),
                )

    def test_kontext_model_passes_image_reference(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            kontext_dir = Path(tmp_dir) / "FLUX.1-Kontext-dev"
            kontext_dir.mkdir()
            parameters = self._base_parameters(use_source_reference=True)
            parameters["FluxModelSelection"] = "Local Kontext"
            swapper = TestableFluxAcePlusSwapper(
                Path(tmp_dir),
                {"Local Kontext": str(kontext_dir)},
            )
            target, source, mask = self._images()

            swapper.run(target, source, mask, parameters)

            self.assertIsInstance(swapper.pipeline, FakeKontextPipeline)
            self.assertIsNotNone(swapper.pipeline.last_kwargs["image_reference"])

    def test_ace_lora_download_prefers_repo_subfolder_filename(self):
        original_resolver = flux_module.resolve_project_path
        calls: list[str] = []

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            def fake_resolve_project_path(*parts):
                return tmp_path.joinpath(*parts)

            def fake_hf_hub_download(repo_id, filename, local_dir, token):
                calls.append(filename)
                downloaded_path = Path(local_dir) / filename
                downloaded_path.parent.mkdir(parents=True, exist_ok=True)
                downloaded_path.write_bytes(b"fake-lora")
                return str(downloaded_path)

            def fake_snapshot_download(**_kwargs):
                raise AssertionError("snapshot fallback should not be used")

            flux_module.resolve_project_path = fake_resolve_project_path
            try:
                swapper = TestableFluxAcePlusSwapper(tmp_path)
                swapper._get_hf_runtime = lambda: (
                    fake_hf_hub_download,
                    fake_snapshot_download,
                )

                lora_path = swapper._download_ace_lora(ACE_PORTRAIT_AUTO_OPTION)
                lora_exists = Path(lora_path).is_file()
            finally:
                flux_module.resolve_project_path = original_resolver

        self.assertEqual(calls[0], "portrait/comfyui_portrait_lora64.safetensors")
        self.assertTrue(lora_exists)


if __name__ == "__main__":
    unittest.main()
