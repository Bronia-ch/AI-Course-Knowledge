"""Whisper 转录结果的轻量质量检查。"""

from collections import Counter
import re


class TranscriptionQualityError(ValueError):
    """转录结果明显异常，不能覆盖数据库中的旧结果。"""


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _has_meaningful_character(text: str) -> bool:
    return any(character.isalnum() for character in text)


def validate_transcription(segments: list[dict]) -> None:
    """拒绝整节重复、长段循环和大量纯符号组成的结果。"""
    if not segments:
        raise TranscriptionQualityError("Whisper 未生成有效转录文本")

    normalized = [_normalize_text(segment["text"]) for segment in segments]
    segment_count = len(normalized)
    frequencies = Counter(normalized)
    top_text, top_count = frequencies.most_common(1)[0]

    if segment_count >= 20 and top_count / segment_count >= 0.8:
        raise TranscriptionQualityError(
            f"转录结果异常：{top_count}/{segment_count} 个片段重复“{top_text[:40]}”"
        )

    longest_text = normalized[0]
    longest_count = 1
    longest_start = float(segments[0]["start_time"])
    longest_end = float(segments[0]["end_time"])
    current_text = normalized[0]
    current_count = 1
    current_start = longest_start

    for index in range(1, segment_count):
        text = normalized[index]
        if text == current_text:
            current_count += 1
        else:
            current_text = text
            current_count = 1
            current_start = float(segments[index]["start_time"])

        current_end = float(segments[index]["end_time"])
        current_span = current_end - current_start
        longest_span = longest_end - longest_start
        if current_count > longest_count or (
            current_count == longest_count and current_span > longest_span
        ):
            longest_text = current_text
            longest_count = current_count
            longest_start = current_start
            longest_end = current_end

    longest_span = longest_end - longest_start
    repeated_too_long = longest_count >= 20 and longest_span >= 20
    repeated_across_silence = longest_count >= 12 and longest_span >= 60
    if repeated_too_long or repeated_across_silence:
        raise TranscriptionQualityError(
            "转录结果异常：文本“{}”连续重复 {} 次，跨度 {:.1f} 秒".format(
                longest_text[:40], longest_count, longest_span
            )
        )

    symbol_only_count = sum(
        1 for text in normalized if not _has_meaningful_character(text)
    )
    if (
        segment_count >= 20
        and symbol_only_count >= 20
        and symbol_only_count / segment_count >= 0.2
    ):
        raise TranscriptionQualityError(
            f"转录结果异常：{symbol_only_count}/{segment_count} 个片段仅包含符号"
        )
