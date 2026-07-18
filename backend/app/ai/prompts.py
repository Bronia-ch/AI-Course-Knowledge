"""
AI 提示词模板 — DeepSeek 知识分析

所有 prompt 返回结构化 JSON，便于程序解析。
"""

# =============================================================================
# 知识点提取
# =============================================================================
KNOWLEDGE_POINT_SYSTEM_PROMPT = """\
你是一个AI课程知识分析师。请分析以下课程转写文本，提取其中的关键知识点。

要求：
1. 每个知识点包含：
   - title: 知识点标题（简洁，不超过15字）
   - description: 详细说明（2-3句话，概括核心内容）
   - importance: 重要程度 1-5（1=提及，3=重点讲解，5=核心概念）
   - category: 分类标签
   - timestamp: 该知识点首次出现的时间（秒）
2. 知识点数量控制在 5-15 个
3. 按课程内容出现顺序排列
4. 只提取课程中明确讲到的内容，不要编造
5. timestamp 必须来自输入文本中的时间戳
6. 如果知识点来自：
   [00:07] 反向传播算法是...
   则timestamp填写 7
7. 不允许自己估算时间
8. 每个知识点必须尽可能对应一个原始转录片段

请严格按以下JSON格式返回（不要包含markdown代码块标记）：
{
  "knowledge_points": [
    {
      "title": "...",
      "description": "...",
      "importance": 4,
      "category": "基础概念",
      "timestamp": 12
    }
  ]
}"""


def build_knowledge_point_prompt(transcript_text: str) -> str:
    """构建知识点提取的 user message"""
    return f"课程转写文本：\n---\n{transcript_text}\n---"


# =============================================================================
# 项目识别
# =============================================================================
PROJECT_SYSTEM_PROMPT = """\
你是一个AI课程项目分析师。请分析以下课程转写文本，识别其中提到的实战项目或练习任务。

要求：
1. 每个项目包含：
   - name: 项目名称（简洁明了）
   - goal: 项目目标（一句话描述要达成什么）
   - input: 输入说明（项目需要什么数据/条件作为输入）
   - output: 输出说明（项目完成后产出什么）
   - technology_stack: 技术栈列表（如 ["Python", "PyTorch", "Flask"]）
   - workflow: 工作流程（3-5个步骤的列表）
2. 如果没有明确的实战项目或练习，返回空数组 []
3. 不要编造课程中未提到的项目

请严格按以下JSON格式返回（不要包含markdown代码块标记）：
{
  "projects": [
    {
      "name": "...",
      "goal": "...",
      "input": "...",
      "output": "...",
      "technology_stack": ["tech1", "tech2"],
      "workflow": ["步骤1", "步骤2", "步骤3"]
    }
  ]
}"""


def build_project_prompt(transcript_text: str) -> str:
    """构建项目识别的 user message"""
    return f"课程转写文本：\n---\n{transcript_text}\n---"

# =============================================================================
# 知识点-项目关联分析
# =============================================================================

RELATION_SYSTEM_PROMPT = """\
你是一个AI课程知识图谱分析师。

请根据课程中的知识点和实战项目，分析它们之间的关联关系。

目标：
建立：
知识点 → 项目

的学习关联。


要求：

1. 每个关联包含：

   - knowledge_point:
     知识点名称

   - project:
     项目名称

   - reason:
     为什么该知识点应用于该项目
     （一句或两句话说明）


2. 只建立明确存在的关联。

3. 不要为了增加数量而强行关联。

4. 如果没有关联，返回空数组。


请严格按以下JSON格式返回
（不要包含markdown代码块标记）：

{
  "relations": [
    {
      "knowledge_point": "反向传播算法",
      "project": "手写数字识别项目",
      "reason": "项目训练神经网络时需要使用反向传播算法优化模型参数"
    }
  ]
}
"""


def build_relation_prompt(
    knowledge_points: list,
    projects: list,
) -> str:
    """
    构建知识点-项目关联分析输入
    """

    return f"""
请分析以下知识点和项目之间的关联：

知识点：

{knowledge_points}


项目：

{projects}
"""

# =============================================================================
# 文本拼接辅助
# =============================================================================
def format_transcript_context(segments: list) -> str:
    """
    将转录片段列表拼接为带时间戳的完整文本

    格式：
      [00:05] 大家好，今天我们来学习...
      [00:12] 这节课的主要内容是...

    Args:
        segments: Transcript ORM 对象列表（按 start_time 排序）
    """
    lines = []
    for seg in segments:
        minutes = int(seg.start_time // 60)
        seconds = int(seg.start_time % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        lines.append(f"{timestamp} {seg.text}")
    return "\n".join(lines)


def format_transcript_plain(segments: list) -> str:
    """
    将转录片段拼接为纯文本（无时间戳）

    用于节省 token 消耗，适合内容较短的课程。
    """
    return " ".join(seg.text for seg in segments)
