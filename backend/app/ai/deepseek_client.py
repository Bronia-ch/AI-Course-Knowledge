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

        response = self._create_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content or ""
        logger.debug("DeepSeek 响应: %d chars, %d tokens",
                     len(content),
                     response.usage.total_tokens if response.usage else 0)

        return content

    def _create_completion(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool = False,
    ):
        """创建一次对话请求，JSON 任务使用服务端结构化输出模式。"""
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            request["response_format"] = {"type": "json_object"}
        return self._client.chat.completions.create(**request)

    @staticmethod
    def _parse_json_content(content: str) -> dict:
        """从模型响应中提取 JSON 对象，兼容 Markdown 代码块和前后说明。"""
        stripped = content.strip()
        if not stripped:
            raise ValueError("DeepSeek 返回了空内容")

        candidates = [stripped]
        # 只识别包裹整个响应的外层代码块，避免误取 JSON 字段内的目录树。
        match = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
        if match:
            candidates.append(match.group(1).strip())
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1:
            candidates.append(stripped[start:end + 1])

        last_error = None
        for json_str in dict.fromkeys(candidates):
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as exc:
                last_error = exc
                continue
            if not isinstance(result, dict):
                raise ValueError("DeepSeek 返回的 JSON 顶层必须是对象")
            return result

        context_start = max(0, last_error.pos - 80)
        context_end = min(len(json_str), last_error.pos + 80)
        logger.error(
            "DeepSeek JSON 语法错误上下文: position=%d, context=%r",
            last_error.pos,
            json_str[context_start:context_end],
        )
        raise ValueError(f"DeepSeek 返回了无效的 JSON: {last_error}") from last_error

    def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        retry_instruction: str | None = None,
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
        last_error = None
        last_finish_reason = None
        retry_message = user_message
        for attempt in range(2):
            response = self._create_completion(
                system_prompt=system_prompt,
                user_message=retry_message,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=True,
            )
            if not response.choices:
                content = ""
                last_error = ValueError("DeepSeek 没有返回可用的结果")
            else:
                choice = response.choices[0]
                content = choice.message.content or ""
                last_finish_reason = choice.finish_reason
                try:
                    return self._parse_json_content(content)
                except ValueError as exc:
                    last_error = exc

            logger.warning(
                "DeepSeek JSON 响应异常，准备重试: attempt=%d, finish_reason=%s, "
                "content_length=%d, error=%s",
                attempt + 1,
                last_finish_reason,
                len(content),
                last_error,
            )
            if attempt == 0:
                if last_finish_reason == "length":
                    correction = retry_instruction or (
                        "上一次响应因达到输出长度上限而被截断。请大幅压缩内容："
                        "不要重复背景，减少数组项目，每个字符串最多两三句；"
                        "宁可简洁，也必须只返回一个完整、可解析的 JSON 对象。"
                    )
                else:
                    correction = (
                        "上一次响应为空或不是合法 JSON。"
                        "请只返回一个完整、可解析的 JSON 对象。"
                    )
                retry_message = f"{user_message}\n\n{correction}"

        reason = f"（结束原因：{last_finish_reason}）" if last_finish_reason else ""
        logger.error("DeepSeek JSON 连续两次生成失败%s: %s", reason, last_error)
        raise ValueError(
            f"DeepSeek 连续两次未返回完整的 JSON{reason}，请稍后重试"
        ) from last_error

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

    def extract_portfolio_opportunities(
        self,
        transcript_text: str,
        knowledge_points: list,
        course_projects: list,
    ) -> list[dict]:
        """提取适合面试展示的作品机会。"""
        from .prompts import (
            PORTFOLIO_OPPORTUNITY_SYSTEM_PROMPT,
            build_portfolio_opportunity_prompt,
        )

        result = self.chat_json(
            system_prompt=PORTFOLIO_OPPORTUNITY_SYSTEM_PROMPT,
            user_message=build_portfolio_opportunity_prompt(
                transcript_text,
                knowledge_points,
                course_projects,
            ),
            temperature=0.3,
        )
        opportunities = result.get("portfolio_opportunities", [])
        logger.info("提取到 %d 个面试作品机会", len(opportunities))
        return opportunities

    def create_portfolio_project_blueprint(
        self,
        opportunity: dict,
        transcript_text: str,
        knowledge_points: list,
    ) -> dict:
        """将作品机会扩展为可执行项目蓝图。"""
        from .prompts import (
            PORTFOLIO_PROJECT_SYSTEM_PROMPT,
            build_portfolio_project_prompt,
        )

        return self.chat_json(
            system_prompt=PORTFOLIO_PROJECT_SYSTEM_PROMPT,
            user_message=build_portfolio_project_prompt(
                opportunity,
                transcript_text,
                knowledge_points,
            ),
            temperature=0.25,
        )

    def create_portfolio_reference_queries(self, project: dict) -> list[str]:
        """为 GitHub 相似项目检索生成简短英文查询。"""
        from .prompts import (
            PORTFOLIO_REFERENCE_QUERY_SYSTEM_PROMPT,
            build_portfolio_reference_query_prompt,
        )

        result = self.chat_json(
            system_prompt=PORTFOLIO_REFERENCE_QUERY_SYSTEM_PROMPT,
            user_message=build_portfolio_reference_query_prompt(project),
            temperature=0.1,
            max_tokens=500,
        )
        queries = result.get("queries", [])
        if not isinstance(queries, list):
            return []
        return [str(item).strip()[:120] for item in queries[:3] if str(item).strip()]

    def create_portfolio_concept_guide(
        self,
        project: dict,
        transcript_text: str,
        knowledge_points: list,
        reference_sources: list,
    ) -> dict:
        """生成不依赖真实源码的初学者作品指南。"""
        from .prompts import (
            PORTFOLIO_CONCEPT_FOUNDATION_SYSTEM_PROMPT,
            PORTFOLIO_CONCEPT_FLOW_SYSTEM_PROMPT,
            PORTFOLIO_CONCEPT_LADDER_SYSTEM_PROMPT,
            PORTFOLIO_CONCEPT_LESSONS_SYSTEM_PROMPT,
            build_portfolio_concept_guide_prompt,
        )

        user_message = build_portfolio_concept_guide_prompt(
            project,
            transcript_text,
            knowledge_points,
            reference_sources,
        )
        try:
            foundation = self.chat_json(
                system_prompt=PORTFOLIO_CONCEPT_FOUNDATION_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.25,
                max_tokens=2500,
                retry_instruction=(
                    "上次开场故事不完整。content 控制在 350-450 个中文字符，"
                    "只返回包含 guide_title 和 beginner_story 的完整 JSON。"
                ),
            )
        except ValueError as exc:
            raise ValueError(f"学习指南的开场故事生成失败：{exc}") from exc
        try:
            flow = self.chat_json(
                system_prompt=PORTFOLIO_CONCEPT_FLOW_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.2,
                max_tokens=4000,
                retry_instruction=(
                    "上次运行流程不完整。只输出恰好 5 项，每个字段不超过 80 字，"
                    "只返回完整 JSON。"
                ),
            )
        except ValueError as exc:
            raise ValueError(f"学习指南的运行流程生成失败：{exc}") from exc
        try:
            ladder = self.chat_json(
                system_prompt=PORTFOLIO_CONCEPT_LADDER_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.2,
                # DeepSeek v4 Flash 在过大的 JSON 输出上限下可能直接返回空的
                # length 响应。概念卡的受控篇幅在 3000 token 内足够完整。
                max_tokens=3000,
                retry_instruction=(
                    "上次概念阶梯不完整。只输出恰好 8 项，每个字段不超过 55 字，"
                    "只返回完整 JSON。"
                ),
            )
        except ValueError as exc:
            raise ValueError(f"学习指南的概念阶梯生成失败：{exc}") from exc
        try:
            lessons = self.chat_json(
                system_prompt=PORTFOLIO_CONCEPT_LESSONS_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.25,
                # 连续课程的结构受提示词约束，4000 token 可以容纳五节正文及自测，
                # 同时兼容 Flash 的稳定输出范围。
                max_tokens=4000,
                retry_instruction=(
                    "上次课程部分不完整。保留 5 个 story_sections 和所有 JSON 字段，"
                    "每节正文约 200-240 字，self_checks 只保留 3 项，只返回完整 JSON。"
                ),
            )
        except ValueError as exc:
            raise ValueError(f"学习指南的连续课程部分生成失败：{exc}") from exc
        return {**foundation, **flow, **ladder, **lessons}

    def create_portfolio_execution_package(
        self,
        project: dict,
        knowledge_points: list,
    ) -> dict:
        """生成可直接交给 Codex 等开发型 AI 的项目执行包。"""
        from .prompts import (
            PORTFOLIO_EXECUTION_SYSTEM_PROMPT,
            build_portfolio_execution_prompt,
        )

        return self.chat_json(
            system_prompt=PORTFOLIO_EXECUTION_SYSTEM_PROMPT,
            user_message=build_portfolio_execution_prompt(
                project,
                knowledge_points,
            ),
            temperature=0.2,
            max_tokens=8192,
            retry_instruction=(
                "上一次响应因达到输出长度上限而被截断。必须显著缩短："
                "不要输出任何 Codex、审查或讲解提示词；开发阶段控制在 3-5 个，"
                "每个阶段的任务和验收标准各不超过 4 项；其他数组只保留核心项目。"
                "不要重复项目背景，只返回一个完整、可解析的 JSON 对象。"
            ),
        )
