"""
Whisper 语音转文字 — 基于 faster-whisper

使用方式：
    transcriber = WhisperTranscriber(model_size="small", device="cuda")
    segments, info = transcriber.transcribe("audio.mp3")
    # segments: 生成器，逐条产出 {start_time, end_time, text}
    # info: 元信息 {duration, language}

显存参考（RTX 2060 6GB）：
    small + int8    → ~1.2 GB（推荐默认）
    small + float16 → ~2 GB
    medium + int8   → ~3 GB

生命周期：
    单例模式 — 应用启动时只创建轻量转录器，首次转录时才加载模型。
    转录器存于 app.state.whisper_model，所有请求共享同一实例。
"""

import logging
from threading import Lock
from typing import Generator, Optional

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class TranscriberConfig:
    """转录器配置（从 Settings 映射到可读结构）"""

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cuda",
        compute_type: str = "int8",
        beam_size: int = 5,
        language: str | None = "zh",
        vad_filter: bool = True,
        condition_on_previous_text: bool = False,
        no_speech_threshold: float = 0.6,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size
        self.language = language or None
        self.vad_filter = vad_filter
        self.condition_on_previous_text = condition_on_previous_text
        self.no_speech_threshold = no_speech_threshold

    def __repr__(self) -> str:
        return (
            f"TranscriberConfig(model={self.model_size}, "
            f"device={self.device}, compute={self.compute_type}, "
            f"beam={self.beam_size}, language={self.language}, "
            f"vad={self.vad_filter}, previous_text={self.condition_on_previous_text})"
        )


class WhisperTranscriber:
    """
    Whisper 转录器 — 封装 faster-whisper 模型生命周期

    使用示例：
        tc = WhisperTranscriber(
            model_size="small", device="cuda", compute_type="int8"
        )
        segments, info = tc.transcribe("/path/to/audio.mp3")
        for seg in segments:
            print(f"[{seg.start:.1f}s - {seg.end:.1f}s] {seg.text}")
    """

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cuda",
        compute_type: str = "int8",
        beam_size: int = 5,
        language: str | None = "zh",
        vad_filter: bool = True,
        condition_on_previous_text: bool = False,
        no_speech_threshold: float = 0.6,
    ):
        self.config = TranscriberConfig(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            beam_size=beam_size,
            language=language,
            vad_filter=vad_filter,
            condition_on_previous_text=condition_on_previous_text,
            no_speech_threshold=no_speech_threshold,
        )
        self._model: Optional[WhisperModel] = None
        self._load_lock = Lock()

    def _ensure_model(self) -> WhisperModel:
        """首次使用时线程安全地加载模型，后续直接复用。"""
        if self._model is not None:
            return self._model

        with self._load_lock:
            if self._model is not None:
                return self._model

            self._model = self._load_model()

        return self._model

    def _load_model(self) -> WhisperModel:
        """加载 Whisper 模型到 GPU/CPU。"""
        logger.info(
            "加载 Whisper 模型: %s (compute=%s) on %s ...",
            self.config.model_size,
            self.config.compute_type,
            self.config.device,
        )
        model = WhisperModel(
            self.config.model_size,
            device=self.config.device,
            compute_type=self.config.compute_type,
        )
        logger.info("Whisper 模型加载完成")
        return model

    def transcribe(self, audio_path: str) -> tuple:
        """
        转写音频文件

        Args:
            audio_path: 音频文件绝对路径

        Returns:
            (segments_generator, info)
            - segments_generator: 逐段产出 faster_whisper Segment 对象
            - info: 包含 duration（总时长秒数）、language（检测到的语言）

        Raises:
            FileNotFoundError: 音频文件不存在
            RuntimeError: 模型未加载或转写失败
        """
        model = self._ensure_model()

        logger.info("开始转写: %s (beam_size=%d)", audio_path, self.config.beam_size)

        segments, info = model.transcribe(
            audio_path,
            beam_size=self.config.beam_size,
            language=self.config.language,
            vad_filter=self.config.vad_filter,
            vad_parameters={"min_silence_duration_ms": 1000},
            condition_on_previous_text=self.config.condition_on_previous_text,
            temperature=0.0,
            no_speech_threshold=self.config.no_speech_threshold,
        )

        logger.info(
            "转写完成 — 语言: %s, 总时长: %.1fs",
            info.language,
            info.duration,
        )

        return segments, info

    def get_model_info(self) -> dict:
        """返回当前模型配置信息（供调试）"""
        return {
            "model_size": self.config.model_size,
            "device": self.config.device,
            "compute_type": self.config.compute_type,
            "beam_size": self.config.beam_size,
            "language": self.config.language,
            "vad_filter": self.config.vad_filter,
            "condition_on_previous_text": self.config.condition_on_previous_text,
            "no_speech_threshold": self.config.no_speech_threshold,
            "loaded": self._model is not None,
        }
