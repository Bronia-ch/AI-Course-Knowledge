"""AI 学习助手服务。"""

from ..ai.deepseek_client import DeepSeekClient
from ..ai.prompts import (
    LESSON_QA_SYSTEM_PROMPT,
    build_lesson_qa_prompt,
    format_transcript_context,
)


def answer_lesson_question(
    segments: list,
    question: str,
    client: DeepSeekClient | None = None,
) -> str:
    """根据当前课节转写内容回答用户问题。"""
    transcript_text = format_transcript_context(segments)
    if not transcript_text.strip():
        raise ValueError("当前课节没有可用的转写内容")

    ai_client = client or DeepSeekClient()
    answer = ai_client.chat(
        system_prompt=LESSON_QA_SYSTEM_PROMPT,
        user_message=build_lesson_qa_prompt(transcript_text, question.strip()),
        temperature=0.2,
        max_tokens=1500,
    ).strip()
    if not answer:
        raise RuntimeError("AI 未返回有效回答")
    return answer
