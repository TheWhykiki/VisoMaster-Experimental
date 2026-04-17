import gc
import inspect
import os
import shutil
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import torch
from PIL import Image

from app.helpers.paths import resolve_project_path
from app.processors.models_data import (
    ACE_LOCAL_AUTO_OPTION,
    ACE_PORTRAIT_AUTO_OPTION,
    ACE_SUBJECT_AUTO_OPTION,
    FLUX_FILL_AUTO_OPTION,
)

if TYPE_CHECKING:
    from app.processors.models_processor import ModelsProcessor


FLUX_FILL_REPO_ID = "black-forest-labs/FLUX.1-Fill-dev"
ACE_PLUS_REPO_ID = "ali-vilab/ACE_Plus"

ACE_LORA_AUTO_SPECS = {
    ACE_PORTRAIT_AUTO_OPTION: {
        "local_filename": "ace_plus_portrait_lora64.safetensors",
        "expected_filenames": (
            "comfyui_portrait_lora64.safetensors",
            "ace_plus_portrait_lora64.safetensors",
        ),
        "match_tokens": ("portrait", "lora"),
    },
    ACE_SUBJECT_AUTO_OPTION: {
        "local_filename": "ace_plus_subject_lora16.safetensors",
        "expected_filenames": (
            "comfyui_subject_lora16.safetensors",
            "ace_plus_subject_lora16.safetensors",
        ),
        "match_tokens": ("subject", "lora"),
    },
    ACE_LOCAL_AUTO_OPTION: {
        "local_filename": "ace_plus_local_editing_lora16.safetensors",
        "expected_filenames": (
            "comfyui_local_lora16.safetensors",
            "ace_plus_local_lora16.safetensors",
        ),
        "match_tokens": ("local", "lora"),
    },
}


class FluxAcePlusSwapper:
    """
    Encapsulates the complete FLUX + ACE++ LoRA swap workflow in one place.

    The surrounding application should treat this exactly like any other swapper:
    pass in a target face crop, a source face crop and a mask, and receive a
    swapped face crop back.
    """

    def __init__(self, models_processor: "ModelsProcessor"):
        self.models_processor = models_processor
        self.pipeline = None
        self.pipeline_source = ""
        self.pipeline_class_name = ""
        self.loaded_lora_source = ""

    def _get_runtime(self):
        try:
            from diffusers import FluxInpaintPipeline, FluxKontextInpaintPipeline

            return FluxKontextInpaintPipeline, FluxInpaintPipeline
        except ImportError as exc:
            raise RuntimeError(
                "ACE++ (FLUX) requires diffusers, transformers, accelerate and peft."
            ) from exc

    def _resolve_model_path(self, model_name: str) -> str:
        manager = self.models_processor.main_window.flux_model_manager
        manager.refresh_models()
        return manager.get_model_path(model_name)

    def _resolve_lora_path(self, lora_name: str) -> str:
        manager = self.models_processor.main_window.flux_lora_manager
        manager.refresh_models()
        return manager.get_model_path(lora_name)

    @staticmethod
    def _get_hf_token() -> str | None:
        return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")

    @staticmethod
    def _get_hf_runtime():
        try:
            from huggingface_hub import hf_hub_download, snapshot_download

            return hf_hub_download, snapshot_download
        except ImportError as exc:
            raise RuntimeError(
                "ACE++ (FLUX) auto-download requires huggingface-hub."
            ) from exc

    @staticmethod
    def _is_ready_flux_dir(path: Path) -> bool:
        return path.is_dir() and (path / "model_index.json").exists()

    def _download_flux_fill_model(self) -> str:
        _, snapshot_download = self._get_hf_runtime()
        target_dir = resolve_project_path("model_assets/flux_models/FLUX.1-Fill-dev")

        if self._is_ready_flux_dir(target_dir):
            return str(target_dir)

        try:
            snapshot_download(
                repo_id=FLUX_FILL_REPO_ID,
                local_dir=str(target_dir),
                token=self._get_hf_token(),
                resume_download=True,
            )
        except Exception as exc:
            raise RuntimeError(
                "Could not auto-download FLUX.1 Fill [dev]. "
                "Please make sure you accepted the Hugging Face model license "
                "and that a valid token is available via `HF_TOKEN` or a local "
                "Hugging Face login."
            ) from exc

        if not self._is_ready_flux_dir(target_dir):
            raise RuntimeError(
                "FLUX.1 Fill [dev] download completed, but the model folder is incomplete."
            )
        return str(target_dir)

    @staticmethod
    def _find_lora_candidate(snapshot_dir: Path, selection_label: str) -> Path | None:
        spec = ACE_LORA_AUTO_SPECS[selection_label]
        all_candidates = sorted(snapshot_dir.rglob("*.safetensors"))

        expected_names = {name.lower() for name in spec["expected_filenames"]}
        for candidate in all_candidates:
            if candidate.name.lower() in expected_names:
                return candidate

        match_tokens = spec["match_tokens"]
        token_matches = []
        for candidate in all_candidates:
            candidate_key = str(candidate.relative_to(snapshot_dir)).lower()
            if all(token in candidate_key for token in match_tokens):
                token_matches.append(candidate)
        if token_matches:
            return token_matches[0]

        return None

    def _download_ace_lora(self, selection_label: str) -> str:
        hf_hub_download, snapshot_download = self._get_hf_runtime()
        spec = ACE_LORA_AUTO_SPECS[selection_label]
        local_target = resolve_project_path(
            f"model_assets/flux_loras/{spec['local_filename']}"
        )
        if local_target.is_file():
            return str(local_target)

        token = self._get_hf_token()
        repo_snapshot_dir = resolve_project_path("model_assets/flux_loras/ace_plus_repo")
        repo_snapshot_dir.mkdir(parents=True, exist_ok=True)

        download_errors: list[str] = []
        for remote_filename in spec["expected_filenames"]:
            try:
                downloaded_path = Path(
                    hf_hub_download(
                        repo_id=ACE_PLUS_REPO_ID,
                        filename=remote_filename,
                        local_dir=str(repo_snapshot_dir),
                        token=token,
                    )
                )
                local_target.parent.mkdir(parents=True, exist_ok=True)
                if downloaded_path.resolve() != local_target.resolve():
                    shutil.copy2(downloaded_path, local_target)
                return str(local_target)
            except Exception as exc:
                download_errors.append(f"{remote_filename}: {exc}")

        try:
            snapshot_download(
                repo_id=ACE_PLUS_REPO_ID,
                local_dir=str(repo_snapshot_dir),
                token=token,
                resume_download=True,
                allow_patterns=["*.safetensors"],
            )
        except Exception as exc:
            download_errors.append(f"snapshot: {exc}")

        matched_file = self._find_lora_candidate(repo_snapshot_dir, selection_label)
        if matched_file is None:
            raise RuntimeError(
                "Could not auto-download the selected ACE++ LoRA. "
                "Please make sure the `ali-vilab/ACE_Plus` repo is accessible "
                "and, if needed, provide a valid Hugging Face token. "
                f"Tried: {' | '.join(download_errors)}"
            )

        local_target.parent.mkdir(parents=True, exist_ok=True)
        if matched_file.resolve() != local_target.resolve():
            shutil.copy2(matched_file, local_target)
        return str(local_target)

    def _resolve_or_download_model_path(self, model_name: str) -> str:
        model_source = self._resolve_model_path(model_name)
        if model_source:
            return model_source
        if model_name == FLUX_FILL_AUTO_OPTION:
            return self._download_flux_fill_model()
        raise RuntimeError(
            f"Selected FLUX model '{model_name}' was not found locally in model_assets/flux_models."
        )

    def _resolve_or_download_lora_path(self, lora_name: str) -> str:
        lora_source = self._resolve_lora_path(lora_name)
        if lora_source:
            return lora_source
        if lora_name in ACE_LORA_AUTO_SPECS:
            return self._download_ace_lora(lora_name)
        raise RuntimeError(
            f"Selected ACE++ / FLUX LoRA '{lora_name}' was not found locally in model_assets/flux_loras."
        )

    def _pick_pipeline_class(self, use_source_reference: bool):
        FluxKontextInpaintPipeline, FluxInpaintPipeline = self._get_runtime()
        if use_source_reference:
            return FluxKontextInpaintPipeline
        return FluxInpaintPipeline

    def _load_pipeline(
        self, model_source: str, use_source_reference: bool, cpu_offload: bool
    ):
        pipeline_class = self._pick_pipeline_class(use_source_reference)
        pipeline_class_name = pipeline_class.__name__

        if (
            self.pipeline is not None
            and self.pipeline_source == model_source
            and self.pipeline_class_name == pipeline_class_name
        ):
            return self.pipeline

        self.unload()

        if self.models_processor.device == "cuda":
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        else:
            dtype = torch.float32

        model_path = Path(model_source)
        if model_path.is_file():
            if not hasattr(pipeline_class, "from_single_file"):
                raise RuntimeError(
                    f"{pipeline_class_name} cannot load single-file checkpoints."
                )
            pipeline = pipeline_class.from_single_file(
                str(model_path),
                torch_dtype=dtype,
            )
        else:
            pipeline = pipeline_class.from_pretrained(
                str(model_path),
                torch_dtype=dtype,
                local_files_only=True,
            )

        if hasattr(pipeline, "set_progress_bar_config"):
            pipeline.set_progress_bar_config(disable=True)
        if hasattr(pipeline, "enable_vae_slicing"):
            pipeline.enable_vae_slicing()

        if self.models_processor.device == "cuda":
            if cpu_offload and hasattr(pipeline, "enable_model_cpu_offload"):
                pipeline.enable_model_cpu_offload()
            else:
                pipeline.to("cuda")

        self.pipeline = pipeline
        self.pipeline_source = model_source
        self.pipeline_class_name = pipeline_class_name
        self.loaded_lora_source = ""
        return pipeline

    def unload(self):
        if self.pipeline is not None:
            try:
                if hasattr(self.pipeline, "unload_lora_weights"):
                    self.pipeline.unload_lora_weights(
                        reset_to_overwritten_params=True
                    )
            except Exception:
                pass
            del self.pipeline
            self.pipeline = None

        self.pipeline_source = ""
        self.pipeline_class_name = ""
        self.loaded_lora_source = ""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _apply_lora(self, pipeline, lora_source: str, lora_scale: float):
        if not lora_source:
            if self.loaded_lora_source and hasattr(pipeline, "unload_lora_weights"):
                pipeline.unload_lora_weights(reset_to_overwritten_params=True)
                self.loaded_lora_source = ""
            return

        if (
            self.loaded_lora_source != lora_source
            and hasattr(pipeline, "unload_lora_weights")
        ):
            pipeline.unload_lora_weights(reset_to_overwritten_params=True)
            self.loaded_lora_source = ""

        if self.loaded_lora_source != lora_source:
            lora_path = Path(lora_source)
            if lora_path.is_file():
                pipeline.load_lora_weights(
                    str(lora_path.parent),
                    weight_name=lora_path.name,
                    adapter_name="ace_plus_swapper",
                )
            else:
                pipeline.load_lora_weights(
                    str(lora_path),
                    adapter_name="ace_plus_swapper",
                )
            self.loaded_lora_source = lora_source

        if hasattr(pipeline, "set_adapters"):
            pipeline.set_adapters(
                ["ace_plus_swapper"],
                adapter_weights=[lora_scale],
            )
        elif hasattr(pipeline, "fuse_lora"):
            pipeline.fuse_lora(
                lora_scale=lora_scale,
                adapter_names=["ace_plus_swapper"],
            )

    @staticmethod
    def _build_generator(seed: int):
        if seed <= 0:
            seed = int(torch.randint(1, 2**31 - 1, (1,)).item())
        generator = torch.Generator(device="cpu")
        generator.manual_seed(seed)
        return generator

    @staticmethod
    def _to_rgb_pil(image: np.ndarray | torch.Tensor | Image.Image) -> Image.Image:
        if isinstance(image, Image.Image):
            return image.convert("RGB")

        if isinstance(image, torch.Tensor):
            array = image.detach().cpu().numpy()
            if array.ndim == 3 and array.shape[0] in (1, 3):
                array = np.transpose(array, (1, 2, 0))
            image = array

        array = np.asarray(image)
        if array.dtype != np.uint8:
            array = np.clip(array, 0, 255).astype(np.uint8)
        return Image.fromarray(array).convert("RGB")

    def run(
        self,
        target_face_rgb: np.ndarray,
        source_face_rgb: np.ndarray | None,
        inpaint_mask: np.ndarray,
        parameters: dict,
    ) -> torch.Tensor:
        model_source = self._resolve_or_download_model_path(
            parameters["FluxModelSelection"]
        )
        lora_source = self._resolve_or_download_lora_path(
            parameters["FluxLoraSelection"]
        )
        use_source_reference = bool(
            parameters.get("FluxUseSourceReferenceToggle", True)
            and source_face_rgb is not None
        )

        pipeline = self._load_pipeline(
            model_source,
            use_source_reference=use_source_reference,
            cpu_offload=bool(parameters.get("FluxCPUOffloadToggle", True)),
        )
        self._apply_lora(
            pipeline,
            lora_source=lora_source,
            lora_scale=float(parameters.get("FluxLoRAStrengthDecimalSlider", 1.0)),
        )

        target_image = self._to_rgb_pil(target_face_rgb)
        source_image = (
            self._to_rgb_pil(source_face_rgb) if source_face_rgb is not None else None
        )
        mask_array = np.clip(inpaint_mask, 0.0, 1.0)
        mask_image = Image.fromarray((mask_array * 255.0).astype(np.uint8), mode="L")

        prompt = parameters.get("FluxPromptText", "").strip()
        negative_prompt = parameters.get("FluxNegativePromptText", "").strip()

        call_signature = inspect.signature(pipeline.__call__)
        call_kwargs = {
            "prompt": prompt,
            "image": target_image,
            "mask_image": mask_image,
            "num_inference_steps": int(parameters.get("FluxStepsSlider", 20)),
            "guidance_scale": float(parameters.get("FluxGuidanceDecimalSlider", 3.5)),
            "generator": self._build_generator(int(parameters.get("FluxSeedSlider", 0))),
            "width": target_image.width,
            "height": target_image.height,
            "output_type": "pil",
        }

        if "negative_prompt" in call_signature.parameters and negative_prompt:
            call_kwargs["negative_prompt"] = negative_prompt
        if "true_cfg_scale" in call_signature.parameters:
            call_kwargs["true_cfg_scale"] = float(
                parameters.get("FluxTrueCFGDecimalSlider", 1.0)
            )
        if "ip_adapter_image" in call_signature.parameters and use_source_reference:
            call_kwargs["ip_adapter_image"] = source_image

        with torch.inference_mode():
            result = pipeline(**call_kwargs).images[0]

        result_np = np.asarray(result.convert("RGB"), dtype=np.uint8)
        result_tensor = torch.from_numpy(result_np).permute(2, 0, 1).to(torch.float32)
        return result_tensor.to(self.models_processor.device)

    def run_safe(
        self,
        target_face_rgb: np.ndarray,
        source_face_rgb: np.ndarray | None,
        inpaint_mask: np.ndarray,
        parameters: dict,
    ) -> torch.Tensor | None:
        try:
            return self.run(
                target_face_rgb=target_face_rgb,
                source_face_rgb=source_face_rgb,
                inpaint_mask=inpaint_mask,
                parameters=parameters,
            )
        except Exception as exc:
            print(f"ACE++ (FLUX) swapper failed: {exc}")
            traceback.print_exc()
            return None
