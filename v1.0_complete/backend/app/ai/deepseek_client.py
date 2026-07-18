"""
DeepSeek API 客户端 — 基于 OpenAI 兼容 SDK

使用方式：
    client = DeepSeekClient(api_key="sk-xxx")
    result = client.chat_json(system_prompt, user_message)
"""

import json
import logging
import re
from typing import Optional

from openai import OpenAI

from ..config import settings

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """
    DeepSeek API 客户端

    封装 OpenAI SDK，提供 chat 和 chat_json 两个核心方法。
    DeepSeek 的 API 与 OpenAI 完全兼容，只需修改 base_url。

    使用示例：
        client = DeepSeekClient()
        kps = client.extract_knowledge_points(transcript_text)
        projs = client.extract_projects(transcript_text)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = base_url or settings.DEEPSEEK_BASE_URL
        self.model = model or settings.DEEPSEEK_MODEL

        if not self.api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY 未设置。请在 .env 文件中配置：\n"
                "  DEEPSEEK_API_KEY=sk-xxx"
            )

        self._client = OpenAI(
            api_key=self.api_key,
            base_url=f"{self.base_url}/v1",
        )

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """
        发送消息到 DeepSeek，返回文本响应

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            temperature: 采样温度（0-2），低温度更稳定
            max_tokens: 最大输出 token 数

        Returns:
            模型响应文本
        """
        logger.debug("调用 DeepSeek API: model=%s, temp=%.1f", self.model, temperature)

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content or ""
        logger.debug("DeepSeek 响应: %d chars, %d tokens",
                     len(content),
                     response.usage.total_tokens if response.usage else 0)

        return content

    def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
    ) -> dict:
        """
        发送消息到 DeepSeek，返回解析后的 JSON

        自动处理常见的 JSON 格式问题：
          - markdown 代码块包裹 (```json ... ```)
          - JSON 前后的多余文本

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            temperature: 采样温度

        Returns:
            解析后的 dict

        Raises:
            ValueError: JSON 解析失败
        """
        content = self.chat(system_prompt, user_message, temperature)

        # 尝试提取 JSON：移除 markdown 代码块标记
        # 匹配 ```json ... ``` 或 ``` ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            json_str = match.group(1).strip()
        else:
            # 尝试找到第一个 { 到最后一个 }
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                json_str = content[start:end + 1]
            else:
                json_str = content

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("JSON 解析失败: %s\n原始响应: %.500s", e, content)
            raise ValueError(f"DeepSeek 返回了无效的 JSON: {e}")

    # ===== 高级方法 =====

    def extract_knowledge_points(self, transcript_text: str) -> list[dict]:
        """
        从转写文本中提取知识点

        Args:
            transcript_text: 拼接后的完整转写文本

        Returns:
            [{title, description, importance, category}, ...]
        """
        from .prompts import (
            KNOWLEDGE_POINT_SYSTEM_PROMPT,
            build_knowledge_point_prompt,
        )

        logger.info("开始提取知识点: 文本长度=%d chars", len(transcript_text))
        result = self.chat_json(
            system_prompt=KNOWLEDGE_POINT_SYSTEM_PROMPT,
            user_message=build_knowledge_point_prompt(transcript_text),
        )

        kps = result.get("knowledge_points", [])
        logger.info("提取到 %d 个知识点", len(kps))
        return kps

    def extract_projects(self, transcript_text: str) -> list[dict]:
        """
        从转写文本中识别项目/实战任务

        Args:
            transcript_text: 拼接后的完整转写文本

        Returns:
            [{name, goal, input, output, technology_stack, workflow}, ...]
        """
        from .prompts import (
            PROJECT_SYSTEM_PROMPT,
            build_project_prompt,
        )

        logger.info("开始识别项目: 文本长度=%d chars", len(transcript_text))
        result = self.chat_json(
            system_prompt=PROJECT_SYSTEM_PROMPT,
            user_message=build_project_prompt(transcript_text),
        )

        projects = result.get("projects", [])
        logger.info("识别到 %d 个项目", len(projects))
        return projects

    def extract_relations(
        self,
        knowledge_points: list,
        projects: list,
    ) -> list[dict]:
        """
        分析知识点和项目之间的关联关系

        Args:
            knowledge_points:
                已提取的知识点列表

            projects:
                已识别的项目列表

        Returns:
            [
                {
                    "knowledge_point": "...",
                    "project": "...",
                    "reason": "..."
                }
            ]
        """

        from .prompts import (
            RELATION_SYSTEM_PROMPT,
            build_relation_prompt,
        )

        logger.info(
            "开始分析知识点-项目关系: 知识点=%d, 项目=%d",
            len(knowledge_points),
            len(projects),
        )

        result = self.chat_json(
            system_prompt=RELATION_SYSTEM_PROMPT,
            user_message=build_relation_prompt(
                knowledge_points,
                projects,
            ),
        )

        relations = result.get(
            "relations",
            []
        )

        logger.info(
            "发现 %d 个知识点-项目关联",
            len(relations),
        )

        return relations
