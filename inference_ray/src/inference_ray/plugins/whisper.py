from inference_ray.plugin import AnalyserPlugin, AnalyserPluginManager
from data import AudioData, AnnotationData, Annotation

# from inference_ray import InferenceServer
from data import DataManager, Data

from typing import Callable, Optional, Dict
import logging

default_config = {
    "data_dir": "/data/",
    "host": "localhost",
    "port": 6379,
}

default_parameters = {
    "sr": 16000,
    "chunk_length": 30,
    # None = auto-detect. Pinning this (e.g. "de") when the video's language is known ahead
    # of time skips language detection on the first chunk -- on sports footage that often
    # opens with a whistle/crowd noise rather than clean speech, a wrong detection there can
    # otherwise send the whole transcript off in the wrong language.
    "language": None,
    # The rest are the standard openai-whisper CLI hallucination-guard defaults (see call()'s
    # own comment) -- also exposed to the UI (see usePluginParams.js's whisperParams /
    # ModalPlugin.vue's whisper entry) so they can be tuned per-video instead of only here.
    "condition_on_prev_tokens": False,
    "temperature_fallback": True,
    "no_speech_threshold": 0.6,
    "logprob_threshold": -1.0,
    "compression_ratio_threshold": 2.4,
    # Whisper-specific hallucination guards (above) only ever retry a *whole* chunk's
    # generation from scratch when it looks bad overall -- they don't stop a single decode
    # from looping on the same phrase over and over within an otherwise "acceptable" chunk.
    # These are the generic, model-agnostic transformers.generate() antidote for exactly
    # that: no_repeat_ngram_size forbids repeating any 3-word sequence at all, and
    # repetition_penalty makes already-used tokens progressively less likely. 1.0 = off.
    "no_repeat_ngram_size": 3,
    "repetition_penalty": 1.3,
}

requires = {
    "audio": AudioData,
}

provides = {
    "annotations": AnnotationData,
}


@AnalyserPluginManager.export("whisper")
class Whisper(
    AnalyserPlugin,
    config=default_config,
    parameters=default_parameters,
    version="0.1",
    requires=requires,
    provides=provides,
):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)
        # inference_config = self.config.get("inference", None)
        # self.server = InferenceServer.build(inference_config.get("type"), inference_config.get("params", {}))

        self.model = None
        self.model_name = self.config.get("model", "openai/whisper-base")

    def call(
        self,
        inputs: Dict[str, Data],
        data_manager: DataManager,
        parameters: Dict = None,
        callbacks: Callable = None,
    ) -> Dict[str, Data]:
        import librosa
        import torch
        from transformers import pipeline

        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        if self.model is None:
            self.model = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                chunk_length_s=30,
                device=device,
            )
            self.device = device

        with inputs["audio"] as input_data, data_manager.create_data(
            "AnnotationData"
        ) as output_data:
            with input_data.open_audio("r") as f_audio:
                y, sr = librosa.load(f_audio, sr=parameters.get("sr"))

                # Non-studio audio (whistle/crowd noise, a shout from far off mic, silence
                # before the first whistle) makes Whisper prone to hallucinating -- either a
                # single chunk decoding into a degenerate repeated loop ("1,2,3,4,5,5,5,5,...",
                # the same sentence over and over), or, once that happens, every later chunk
                # continuing to condition on that garbage and inheriting it. Two standard
                # mitigations for exactly that, matching what the openai-whisper CLI itself
                # does by default (this pipeline call was overriding neither before):
                #   - a temperature fallback ladder + the three quality thresholds below --
                #     whenever a chunk's output looks degenerate (too repetitive/compressed,
                #     low average log-prob, or classified as no-speech), it's retried at the
                #     next (more random) temperature instead of being accepted as-is.
                #   - condition_on_prev_tokens=False, so one bad chunk can't drag every later
                #     chunk down with it -- each chunk gets decoded fresh.
                # All five are also just default_parameters, so a per-run override (see
                # ModalPlugin.vue/usePluginParams.js) always wins over the values used here.
                temperature = (
                    (0.0, 0.2, 0.4, 0.6, 0.8, 1.0) if parameters.get("temperature_fallback") else 0.0
                )
                prediction = self.model(
                    y,
                    batch_size=8,
                    return_timestamps=True,
                    generate_kwargs={
                        "task": "transcribe",
                        # "or None": an empty string should mean the same as it being absent
                        # (auto-detect), not get passed through to generate() as-is.
                        "language": parameters.get("language") or None,
                        "condition_on_prev_tokens": parameters.get("condition_on_prev_tokens"),
                        "temperature": temperature,
                        "compression_ratio_threshold": parameters.get("compression_ratio_threshold"),
                        "logprob_threshold": parameters.get("logprob_threshold"),
                        "no_speech_threshold": parameters.get("no_speech_threshold"),
                        "no_repeat_ngram_size": parameters.get("no_repeat_ngram_size"),
                        "repetition_penalty": parameters.get("repetition_penalty"),
                    },
                )["chunks"]

                for chunk in prediction:
                    start = chunk["timestamp"][0]
                    end = chunk["timestamp"][1]
                    if start is None:
                        start = 0.0
                    if end is None:
                        end = len(y) / sr
                    output_data.annotations.append(
                        Annotation(start=start, end=end, labels=[str(chunk["text"])])
                    )

                self.update_callbacks(callbacks, progress=1.0)
                return {"annotations": output_data}
