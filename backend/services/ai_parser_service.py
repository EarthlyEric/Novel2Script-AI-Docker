"""
AI 解析服务模块

负责调用 OpenAI 兼容的大语言模型接口，将预处理后的小说文本
转换为符合 YAML Schema 规范的结构化剧本数据。

核心功能：
- 加载系统提示词模板
- 拼接用户输入（小说正文 + 元信息）
- 调用 LLM API 并获取结构化 YAML 输出
- 解析校验 AI 返回的 YAML 数据
- 异常处理与重试机制
"""

import os
import re

from openai import OpenAI

from backend.config import AIConfig
from backend.schemas.script_schema import ScriptYAML


def parse_novel_to_script(
    novel_text: str,
    novel_title: str,
    config: AIConfig | None = None,
    max_retries: int = 2,
) -> ScriptYAML:
    """
    调用 AI 大模型将小说文本转换为结构化剧本。

    完整处理流程：
    1. 加载系统提示词模板文件
    2. 拼接用户输入模板（小说名 + 章节信息 + 正文）
    3. 调用 OpenAI 兼容 API 发送请求
    4. 从响应中提取纯 YAML 文本
    5. 通过 Pydantic Schema 校验解析为结构化数据
    6. 解析失败时自动重试（最多 max_retries 次）

    Args:
        novel_text: 预处理后的小说纯正文文本
        novel_title: 小说/原著名称
        config: AI模型配置实例，为 None 时使用默认配置
        max_retries: 最大重试次数，当 AI 返回格式不合法时触发

    Returns:
        ScriptYAML: 校验通过的结构化剧本数据，包含完整的
                   元数据、场次列表、人物库和改编说明

    Raises:
        ValueError: API Key 未配置时抛出
        ConnectionError: API 网络连接失败且重试耗尽时抛出
        RuntimeError: AI 返回数据始终无法通过 Schema 校验时抛出

    Note:
        - 系统提示词从 prompts/system_prompt.txt 加载
        - AI 要求仅输出纯净 YAML，无 markdown 标记
        - 函数会自动剥离可能包裹在 ```yaml 代码块中的内容
    """
    if config is None:
        config = AIConfig()

    if not config.api_key:
        raise ValueError("API Key 未配置，请在设置中填写有效的 API Key")

    # 加载系统提示词
    system_prompt = _load_system_prompt()

    # 构建用户消息
    user_message = _build_user_message(novel_text, novel_title)

    # 初始化 OpenAI 客户端
    client = OpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout,
    )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            # 调用大模型 API
            response = client.chat.completions.create(
                model=config.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

            # 提取 AI 返回文本
            ai_output = response.choices[0].message.content
            if not ai_output:
                raise RuntimeError("AI 返回了空内容")

            # 清理可能的 markdown 包裹，提取纯净 YAML
            yaml_text = _extract_yaml_from_response(ai_output)

            # 通过 Schema 校验解析
            script_data = ScriptYAML.from_yaml(yaml_text)
            return script_data

        except Exception as e:
            last_error = e
            if attempt < max_retries:
                continue
            raise RuntimeError(
                f"AI 解析失败（已重试 {max_retries} 次）: {str(last_error)}"
            ) from last_error

    # 不应到达此处，但为了类型安全
    raise RuntimeError(f"AI 解析失败: {last_error}")


def _load_system_prompt() -> str:
    """
    从提示词模板文件加载系统提示词内容。

    按以下优先级查找文件：
    1. backend/prompts/system_prompt.txt（项目内嵌路径）
    2. prompts/system_prompt.txt（工作目录路径）

    Returns:
        str: 系统提示词的完整文本内容

    Raises:
        FileNotFoundError: 提示词文件不存在时抛出

    Note:
        文件不存在时会给出明确的错误引导信息
    """
    # 可能的文件路径（按优先级排序）
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "prompts", "system_prompt.txt"),
        os.path.join("prompts", "system_prompt.txt"),
        os.path.join("backend", "prompts", "system_prompt.txt"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()

    raise FileNotFoundError(
        "系统提示词文件 prompts/system_prompt.txt 不存在，"
        "请确认项目文件完整性"
    )


def _build_user_message(novel_text: str, novel_title: str) -> str:
    """
    按照设计文档规范的用户输入模板拼接请求内容。

    模板格式：
        本次转换原著：【小说名称】
        本次转换章节：【X-X章】
        小说正文内容：【用户上传多章节正文】

    Args:
        novel_text: 预处理后的小说纯正文
        novel_title: 小说名称

    Returns:
        str: 拼接完成的用户消息文本
    """
    # 尝试从文本中粗略估算章节数（用于显示）
    chapter_hint = ""
    import re as _re

    chapter_matches = _re.findall(
        r"第[一二三四五六七八九十百千零〇\d]+章", novel_text
    )
    if chapter_matches:
        chapter_hint = f"第1-{len(chapter_matches)}章"
    else:
        chapter_hint = "全文"

    return (
        f"本次转换原著：【{novel_title}】\n"
        f"本次转换章节：【{chapter_hint}】\n"
        f"小说正文内容：\n{novel_text}"
    )


def _extract_yaml_from_response(ai_output: str) -> str:
    """
    从 AI 返回文本中提取纯净的 YAML 内容。

    AI 有时会在 YAML 外层包裹 markdown 代码块标记（```yaml ... ```），
    此函数负责检测并剥离这些包裹，保留纯净 YAML 文本。

    Args:
        ai_output: AI 原始返回文本

    Returns:
        str: 剔除 markdown 标记后的纯净 YAML 文本

    Note:
        - 支持 ```yaml 和 ``` 两种代码块标记
        - 若无代码块标记则原样返回
        - 自动去除首尾空白
    """
    text = ai_output.strip()

    # 匹配 ```yaml ... ``` 或 ``` ... ``` 代码块
    pattern = r"```(?:ya?ml)?\s*\n?(.*?)\n?```"
    match = re.search(pattern, text, re.DOTALL)

    if match:
        return match.group(1).strip()

    # 无代码块包裹，直接返回
    return text
