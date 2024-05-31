# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/ocr_idefics.ipynb.

# %% ../nbs/ocr_idefics.ipynb 1
from __future__ import annotations


# %% auto 0
__all__ = ['IdeficsOCR']

# %% ../nbs/ocr_idefics.ipynb 5
import subprocess
from pathlib import Path
from typing import Any
from typing import Literal
from typing import TypeAlias

import torch
import transformers.image_utils as image_utils
from PIL import Image
from rich.console import Console
from transformers import AutoProcessor
from transformers import Idefics2ForConditionalGeneration

from .experiments import OCRExperimentContext
from .helpers import IN_MAC
from .helpers import IN_LINUX
from .helpers import default_device
from .ocr_metric import remove_multiple_whitespaces


# %% ../nbs/ocr_idefics.ipynb 12
console = Console(width=104, tab_size=4, force_jupyter=True)
cprint = console.print


# %% ../nbs/ocr_idefics.ipynb 16
if IN_MAC:
    import mlx.core as mx
    from mlx_vlm import load, generate


# %% ../nbs/ocr_idefics.ipynb 17
def load_image(img_ref: str | Path | Image.Image) -> Image.Image:
    return image_utils.load_image(str(img_ref) if isinstance(img_ref, Path) else img_ref)


# %% ../nbs/ocr_idefics.ipynb 18
def get_gpu_vram(total=True):
    if total:
        if IN_MAC:
            return mx.metal.device_info()['memory_size']//1024//1024
        else:
            command = "nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits"
    else:
        if IN_MAC:
            return mx.metal.get_active_memory()//1024//1024
        else:
            command = "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits"
    try:
        vram = subprocess.check_output(command, shell=True).decode('utf-8').strip()
        return vram
    except subprocess.CalledProcessError:
        return "Failed to get VRAM"


# %% ../nbs/ocr_idefics.ipynb 61
QuantT: TypeAlias = Literal['float16'] | Literal['8bit'] | Literal['4bit']

def _setup_processor(model_id: str = "HuggingFaceM4/idefics2-8b", **kwargs):
    quant: QuantT = kwargs.pop('quant', '8bit')
    if IN_MAC and quant != 'float16':
        from mlx_vlm.utils import get_model_path, load_processor
        model_id = f'mlx-community/idefics2-8b-{quant}'
        processor_config = kwargs.pop('processor_config', None)
        model_path = get_model_path(model_id)
        if processor_config is None:
            processor = load_processor(model_path)
        else:
            processor = load_processor(model_path, processor_config=processor_config)
    else:
        processor = AutoProcessor.from_pretrained(
            model_id, 
            do_image_splitting=False  #  cropped boxes are usually small
        )
    return processor


# %% ../nbs/ocr_idefics.ipynb 63
def _setup_model(quant: QuantT, flashattn: bool=True, lazy: bool = False):
    if IN_MAC and quant != 'float16':
        from mlx_vlm.utils import load_model, get_model_path
        model_id = f"mlx-community/idefics2-8b-{quant}"
        model_path = get_model_path(model_id)
        model = load_model(model_path, lazy=lazy)
    else:
        kwargs: dict = dict(
            torch_dtype=torch.float16,
        )
        if quant == 'float16':
            pass
        else:
            from transformers import BitsAndBytesConfig
            quantization_config = None
            if quant == '8bit':
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                )
            if quant == '4bit':
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_compute_dtype=torch.float16
                )
            if quantization_config is not None:
                kwargs.update(quantization_config=quantization_config)
        if flashattn and not IN_MAC:
            kwargs.update(_attn_implementation="flash_attention_2")
        model = Idefics2ForConditionalGeneration.from_pretrained(
            "HuggingFaceM4/idefics2-8b", 
            device_map='auto', 
            **kwargs)
    return model

# %% ../nbs/ocr_idefics.ipynb 64
prompt_text_tmpl = (
        "Please perform optical character recognition (OCR) on this image, which displays "
        "speech balloons from a comic book. The text is in {}. Extract the text and "
        "format it as follows: transcribe in standard sentence case, avoid using all capital "
        "letters. Provide the transcribed text clearly and double check the sentence is not all capital letters.")

# prompt_text_tmpl = ("Please perform optical character recognition (OCR) on this image, which displays "
#         f"speech balloons from a manga comic. The text is in {}. Extract the text and "
#         "format it without newlines. Provide the transcribed text clearly.")

# prompt_text_tmpl = ("Please perform optical character recognition (OCR) on this image, which displays "
#         "speech balloons from a comic book. The text is in {}. Extract the text and "
#         "format it as follows: transcribe in standard sentence case (avoid using all capital "
#         "letters) and use asterisks to denote any words that appear in bold within the image. "
#         "Provide the transcribed text clearly.")

# prompt_text_tmpl = ("Please perform optical character recognition (OCR) on this image, which displays "
#         "speech balloons from a comic book. The text is in {}. Extract the text and "
#         "format it as follows: transcribe in standard sentence case, capitalized. Avoid using "
#         "all capital letters. In comics, it is common to use two hyphens '--' to interrupt a sentence. "
#         "Retain any hyphens as they appear in the original text. Provide the transcribed text "
#         "clearly, ensuring it is capitalized where appropriate, including proper nouns.")

prompt_text_tmpl = (
        "Please perform optical character recognition (OCR) on this image, which displays "
        "speech balloons from a comic book. The text is in {}. Extract the text and "
        "format it as follows: transcribe in standard sentence case, capitalized. Avoid using "
        "all capital letters, but ensure it is capitalized where appropriate, including proper nouns. "
        "Provide the transcribed text clearly. Double check the text is not all capital letters.")


# prompt_text_tmpl = (
#         "Please perform optical character recognition (OCR) on this image, which contains speech "
#         "balloons from a comic book. The text is in English. Carefully transcribe the text, "
#         "ensuring that you preserve the original formatting and line breaks as they appear "
#         "in the speech balloon."
# )

prompt_text_tmpl = (
        "Perform optical character recognition OCR on this image, which contains speech "
        "balloons from a comic book. The text is in {}."
)

prompt_text_tmpl = (
        "Do perform optical character recognition OCR on the image, which contains speech "
        "balloons from a comic book. The text is in {}. Carefully extract the text exactly "
        "as it appears, ensuring that you preserve the original capitalization, punctuation, and "
        "formatting."
)

default_prompt_text_tmpl = prompt_text_tmpl

# %% ../nbs/ocr_idefics.ipynb 66
class IdeficsOCR:
    prompt_text_tmpl: str = default_prompt_text_tmpl
    PROCESSOR: Any = None
    MODEL: Any = None


    @classmethod
    def setup_processor(cls, model_id: str='HuggingFaceM4/idefics2-8b', quant: QuantT='float16'):
        cls.PROCESSOR = _setup_processor(model_id, quant=quant)
        return cls.PROCESSOR
    
    @classmethod
    def setup_model(cls, quant: QuantT='float16', flashattn: bool=True):
        cls.MODEL = _setup_model(quant, flashattn)
        return cls.MODEL
    
    @staticmethod
    def is_idefics2_available() -> bool:
        return IdeficsOCR.PROCESSOR is not None and IdeficsOCR.MODEL is not None
    is_model_ready = is_idefics2_available
    
    def setup_idefics2(self):
        if self.PROCESSOR is None:
            type(self).setup_processor(quant=self.quant)
        if self.MODEL is None:
            type(self).setup_model(self.quant, self.flashattn)
    setup = setup_idefics2

    def cleanup(self):
        try: del self.PROCESSOR
        except Exception: pass
        try: del self.MODEL
        except Exception: pass
        if IN_MAC:
            mx.metal.clear_cache()
        else:
            torch.cuda.empty_cache()
        import gc
        gc.collect()
        self.MODEL = self.PROCESSOR = None

    def _generation_args_mac(self, image: Image.Image, resulting_messages: list[dict]):
        prompt = self.PROCESSOR.apply_chat_template(resulting_messages, add_generation_prompt=True)
        max_new_tokens = 100
        temperature = 0.0
        top_p = 1.0
        # repetition_penalty = 1.2
        # repetition_context_size = 20
        generation_args: dict = {
            'model': self.MODEL,
            'processor': self.PROCESSOR,
            "image": image,
            'prompt': prompt,
            "max_tokens": max_new_tokens,
            'temp': temperature,
            'top_p': top_p,
            # 'repetition_penalty': repetition_penalty,
            # 'repetition_context_size': repetition_context_size,
        }
        return prompt, generation_args

    def _generation_args(self, image: Image.Image, resulting_messages: list[dict]):
        prompt = self.PROCESSOR.apply_chat_template(resulting_messages, add_generation_prompt=True)
        
        max_new_tokens = 512
        repetition_penalty = 1.2
        decoding_strategy = "Greedy"
        temperature = 0.4
        top_p = 0.8

        generation_args = {
            "max_new_tokens": max_new_tokens,
            "repetition_penalty": repetition_penalty,
        }

        assert decoding_strategy in [
            "Greedy",
            "Top P Sampling",
        ]

        if decoding_strategy == "Greedy":
            generation_args["do_sample"] = False
        elif decoding_strategy == "Top P Sampling":
            generation_args["temperature"] = temperature
            generation_args["do_sample"] = True
            generation_args["top_p"] = top_p

        inputs = self.PROCESSOR(text=prompt, images=[image], return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        generation_args.update(inputs)
        return prompt, generation_args

    def _generate_mac(self, image: Image.Image, resulting_messages: list[dict]):
        prompt, generation_args = self._generation_args_mac(image, resulting_messages)
        output = generate(
            **generation_args, 
            verbose=False#True
        )
        return prompt, [output.strip('<end_of_utterance>').strip(' ')]

    def _generate(self, image: Image.Image, resulting_messages: list[dict]):
        prompt, generation_args = self._generation_args(image, resulting_messages)
        generated_ids = self.MODEL.generate(**generation_args)
        generated_texts = self.PROCESSOR.batch_decode(
            generated_ids[:, generation_args["input_ids"].size(1):], skip_special_tokens=True)
        return prompt, generated_texts

    def postprocess_ocr(self, text):
        return ' '.join(remove_multiple_whitespaces(text).splitlines())
    
    def show_info(self):
        cfg = IdeficsOCR.MODEL.config if IdeficsOCR.MODEL is not None else None
        quant = self.quant
        flashattn = self.flashattn
        if cfg is not None:
            if hasattr(cfg, 'quantization_config'):
                qcfg = cfg.quantization_config
                quant = '4bit' if qcfg.load_in_4bit else '8bit'
            if hasattr(cfg, '_attn_implementation'):
                flashattn = cfg._attn_implementation == 'flash_attention_2'
        cprint(
            f"{'Quantization':>17}: {quant!r}\n"
            f"{'Flash attention 2':>17}: {flashattn if IN_LINUX else 'N/A'}\n"
            f"{'VRAM':>17}: {get_gpu_vram(False)}/{get_gpu_vram()} MiB\n"
        )


    def __call__(
        self,
        img_or_path: Image.Image | Path | str,
        lang: str | None = None,
        prompt_text: str | None = None,
        config: str | None = None,
        show_prompt: bool = False,
        **kwargs,
    ) -> str:
        self.setup_idefics2()
        if not self.is_idefics2_available():
            raise RuntimeError("Idefics is not installed or not found.")
        resulting_messages = [
            {
                "role": "user",
                "content": [{"type": "image"}] + [
                    {"type": "text", "text": prompt_text or self.prompt_text_tmpl.format(lang or self.lang)}
                ]
            }
        ]
        image = load_image(img_or_path)
        gen_func = self._generate_mac if IN_MAC and self.quant != 'float16' else self._generate
        prompt, generated_texts = gen_func(image, resulting_messages)
        if show_prompt:
            cprint("INPUT:", prompt, "\nOUTPUT:", generated_texts)
        return generated_texts[0]#.strip('"')


    def __init__(self, 
            lang: str | None = None, 
            quant: Any | None = None,
            flashattn: bool | None = None, 
            device: str | None = None, 
            *,
            prompt_text_tmpl: str | None = None, 
            lazy: bool | None = False,
            **_
        ):
        self.lang = lang
        self.prompt_text_tmpl = prompt_text_tmpl or self.prompt_text_tmpl
        self.quant: QuantT = quant or 'float16'#'4bits'
        self.flashattn = flashattn or True
        self.device = device or default_device()
        if not lazy and not self.is_idefics2_available():
            self.setup_idefics2()



OCRExperimentContext.register_model('Idefics', IdeficsOCR, {
            "quant": 'float16',
            "flashattn": True,
        })

