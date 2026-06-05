"""
文本预处理服务模块

负责对用户上传的多章节小说原始文本进行清洗和标准化处理，
为AI解析阶段提供干净、连续、结构化的输入文本。

核心功能：
- 识别并拆分章节分隔符（支持多种中文章节格式）
- 过滤广告、留白、冗余标题等无效内容
- 保留正文剧情文本，拼接为连续输入
- 提取章节范围信息供元数据使用
"""

import re
from dataclasses import dataclass


@dataclass
class PreprocessResult:
    """
    文本预处理结果数据类，封装清理后的文本和提取的元信息。

    Attributes:
        clean_text: 清理后的纯正文文本（多章拼接）
        chapter_range: 章节范围描述字符串（如"第1-5章"）
        chapter_count: 检测到的章节数量
    """

    clean_text: str
    chapter_range: str
    chapter_count: int


# 支持的中文章节分隔符正则模式列表
# 覆盖常见格式：第X章/第x章/Chapter X/第X节/数字编号 等
CHAPTER_PATTERNS = [
    r"^第[一二三四五六七八九十百千零〇\d]+章[\s：:：]?.*?$",  # 第一章 / 第一百二十三章
    r"^第[一二三四五六七八九十百千零〇\d]+节[\s：:：]?.*?$",  # 第一节
    r"^Chapter\s*\d+[\s：:：]?.*?$",  # Chapter 1 / Chapter 12
    r"^第[一二三四五六七八九十百千零〇\d]+回[\s：:：]?.*?$",  # 第一回（古典小说）
    r"^\d+[\.\、\s][\s\S]*?$",  # 1. 标题 / 1、标题
]

# 合并后的复合正则表达式
CHAPTER_RE = re.compile("|".join(f"({p})" for p in CHAPTER_PATTERNS), re.MULTILINE)

# 需要过滤的垃圾内容正则模式
FILTER_PATTERNS = [
    r"(https?://\S+)",  # URL链接
    r"(微信|QQ|公众号|扫码|关注)[\s\S]{0,30}?(\n|$)",  # 推广引流
    r"(未完待续|敬请期待|下期再见)",  # 结尾套话
    r"[^\S\n]{4,}",  # 连续4个以上空格（异常空白）
]


def preprocess_novel_text(raw_text: str) -> PreprocessResult:
    """
    对原始小说文本进行完整的预处理流程。

    处理步骤：
    1. 基础清洗：去除BOM头、统一换行符、去除首尾空白
    2. 章节识别：使用正则匹配章节标题行
    3. 内容过滤：删除广告、URL、推广等无效内容
    4. 文本拼接：将有效正文合并为连续文本

    Args:
        raw_text: 用户上传的原始小说文本（可能包含多章节）

    Returns:
        PreprocessResult: 包含清理后文本、章节范围描述、章节数量的结果对象

    Note:
        - 最少需要100字符的有效文本才能通过预处理
        - 未检测到章节标记时返回原始清理文本，chapter_count 为 0
        - 章节范围格式如 "第1-5章"，单章节时为 "第3章"

    Example:
        >>> result = preprocess_novel_text("第一章 开端\\n正文内容...\\n第二章 发展\\n...")
        >>> print(result.chapter_range)  # "第1-2章"
        >>> print(result.clean_text)     # 清理后的正文
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("输入文本不能为空")

    # 步骤1：基础清洗
    text = _basic_clean(raw_text)

    # 步骤2：识别章节分割点
    chapter_positions, chapter_titles = _find_chapters(text)

    # 步骤3：按章节拆分并过滤每章内容
    clean_chapters = _split_and_filter(text, chapter_positions)

    # 步骤4：拼接为连续文本
    clean_text = "\n\n".join(clean_chapters)
    clean_text = _final_clean(clean_text)

    # 构建章节范围信息
    chapter_count = len(chapter_titles)
    chapter_range = _build_chapter_range(chapter_titles, chapter_count)

    return PreprocessResult(
        clean_text=clean_text,
        chapter_range=chapter_range,
        chapter_count=chapter_count,
    )


def _basic_clean(text: str) -> str:
    """
    执行基础文本清洗操作。

    Args:
        text: 原始文本

    Returns:
        str: 清洗后的文本（去BOM、统一换行符、去首尾空白）
    """
    # 移除 UTF-8 BOM
    if text.startswith("\ufeff"):
        text = text[1:]
    # 统一换行符为 \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 去除首尾空白
    return text.strip()


def _find_chapters(text: str) -> tuple[list[tuple[int, int]], list[str]]:
    """
    在文本中定位所有章节标题的位置和名称。

    Args:
        text: 已完成基础清洗的文本

    Returns:
        tuple: (章节位置列表, 章节标题列表)
            - 章节位置列表: [(start_pos, end_pos), ...]
            - 章节标题列表: ["第一章 xxx", ...]
    """
    positions = []
    titles = []

    for match in CHAPTER_RE.finditer(text):
        title = match.group(0).strip()
        positions.append((match.start(), match.end()))
        titles.append(title)

    return positions, titles


def _split_and_filter(
    text: str, chapter_positions: list[tuple[int, int]]
) -> list[str]:
    """
    根据章节位置拆分文本，并对每段内容进行过滤清洗。

    Args:
        text: 完整文本
        chapter_positions: 章节位置列表 [(start, end), ...]

    Returns:
        list[str]: 过滤后的各章节正文列表
    """
    if not chapter_positions:
        # 无章节标记时，整体作为一段处理
        return [_filter_content(text)]

    chapters = []

    for i, (start, end) in enumerate(chapter_positions):
        # 当前章节的结束位置 = 下章开始 或 文本末尾
        if i + 1 < len(chapter_positions):
            next_start = chapter_positions[i + 1][0]
            content = text[end:next_start]
        else:
            content = text[end:]

        filtered = _filter_content(content)
        if filtered.strip():  # 只保留非空章节
            chapters.append(filtered)

    return chapters


def _filter_content(content: str) -> str:
    """
    对单段内容进行广告、URL、推广等无效信息的过滤。

    Args:
        content: 待过滤的文本段落

    Returns:
        str: 过滤后的干净文本
    """
    for pattern in FILTER_PATTERNS:
        content = re.sub(pattern, "", content, flags=re.IGNORECASE)
    # 去除多余空行（保留最多一个空行）
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def _final_clean(text: str) -> str:
    """
    对最终拼接文本进行收尾清洗。

    Args:
        text: 拼接后的完整文本

    Returns:
        str: 最终清洗结果
    """
    # 去除首尾空行
    text = text.strip()
    # 确保不为极短文本
    if len(text) < 50:
        raise ValueError("预处理后有效文本过短（<50字），请检查上传内容是否为有效小说正文")
    return text


def _build_chapter_range(titles: list[str], count: int) -> str:
    """
    根据检测到的章节标题构建章节范围描述字符串。

    Args:
        titles: 章节标题列表
        count: 章节数量

    Returns:
        str: 章节范围描述，如 "第1-5章"、"第3章"、"未知章节(共2段)"
    """
    if count == 0:
        return "未知章节"
    elif count == 1:
        return titles[0] if titles else f"共{count}段"
    else:
        return f"第1-{count}章"
