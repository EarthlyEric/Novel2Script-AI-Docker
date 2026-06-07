"""
AI 解析服务模块

负责调用 OpenAI 兼容的大语言模型接口，将预处理后的小说文本
转换为符合 YAML Schema 规范的结构化剧本数据。

核心功能：
- 滑动分片：超长文本按6000字/片切割，章节边界优先，800字重叠
- 全局人物缓存：前置轻量LLM调用提取全文档人物，分片共用
- 摘要锚定：每片输出后提炼150字摘要，注入下一片上下文
- YAML三层防护：提示词强约束 + 语法校验修复 + 兜底补全
- 心理占比巡检：psy超过8%自动触发二次精简
- 智能限流：429速率限制自动指数退避重试 + 分片间调用间隔控制
- 后端汇总合并：多片YAML的ID全局重排去重
"""

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field

import yaml
from openai import OpenAI

from backend.config import AIConfig
from backend.schemas.script_schema import (
    GlobalCharacter,
    ScriptScene,
    ScriptYAML,
    SceneAttr,
    SceneContentUnit,
    ScriptMeta,
)

# ============================================================
# 常量配置
# ============================================================

# 单分片正文阈值（汉字数）
CHUNK_SIZE = 2500
# 相邻分片重叠区字数
CHUNK_OVERLAP = 500
# 摘要最大字数
SUMMARY_MAX_LENGTH = 150
# psy 占比阈值（超过则触发精简）
PSY_RATIO_THRESHOLD = 0.08
# 人物预提取最大输入字数（取全文前3000字 + 后1500字）
CHAR_EXTRACT_HEAD = 3000
CHAR_EXTRACT_TAIL = 1500

# ============================================================
# 限流控制配置
# ============================================================

# 分片间最小调用间隔（秒），防止连续请求触发速率限制
CHUNK_CALL_INTERVAL = 0.5
# 429 限流错误退避初始等待时间（秒）
RATE_LIMIT_BACKOFF_START = 5.0
# 429 限流错误退避最大等待时间（秒）
RATE_LIMIT_BACKOFF_MAX = 60.0
# 429 限流最大自动重试次数（独立于 max_retries，专门处理限流）
RATE_LIMIT_MAX_RETRIES = 3


def _log(msg: str) -> None:
    """
    立即刷新的日志输出函数（AI 解析服务专用）。

    解决 uvicorn 运行时 stdout 缓冲导致 _log() 不即时显示的问题。
    所有 [AI] 前缀日志通过此函数输出，确保在终端中实时可见。
    """
    print(msg, flush=True)
    sys.stdout.flush()


# ============================================================
# 数据类
# ============================================================


@dataclass
class CharacterCache:
    """
    全局人物缓存数据类，存储从全文档预提取的人物信息。

    Attributes:
        characters: 人物列表，每项包含标准名称、别名列表、人设描述
    """

    characters: list[dict] = field(default_factory=list)

    def to_prompt_text(self) -> str:
        """
        将人物缓存格式化为可注入提示词的文本。

        Returns:
            str: 格式化的人物列表文本，如「1. 林晓（别名：小晓）— 25岁设计师」
        """
        if not self.characters:
            return "暂无已提取人物信息"
        lines = []
        for i, char in enumerate(self.characters, 1):
            name = char.get("char_name", "未知")
            aliases = char.get("aliases", [])
            profile = char.get("char_profile", "")
            alias_str = f"（别名：{'、'.join(aliases)}）" if aliases else ""
            profile_str = f" — {profile}" if profile else ""
            lines.append(f"{i}. {name}{alias_str}{profile_str}")
        return "\n".join(lines)

    def get_all_names(self) -> set[str]:
        """
        获取所有人物名称（含别名）的集合，用于名称匹配。

        Returns:
            set[str]: 所有人物名称和别名的集合
        """
        names = set()
        for char in self.characters:
            names.add(char.get("char_name", ""))
            for alias in char.get("aliases", []):
                names.add(alias)
        return names


@dataclass
class ChunkContext:
    """
    分片上下文数据类，在分片处理链路中传递累积状态。

    Attributes:
        chunk_index: 当前分片序号（从1开始）
        total_chunks: 总分片数
        prev_summary: 上一分片的剧情摘要
        id_offset: 当前ID偏移量（确保全局ID不冲突）
        established_scenes: 已确定的场景信息列表
        established_characters: 已确定的人物名称列表
    """

    chunk_index: int = 1
    total_chunks: int = 1
    prev_summary: str = ""
    id_offset: int = 1
    established_scenes: list[str] = field(default_factory=list)
    established_characters: list[str] = field(default_factory=list)


# ============================================================
# 主入口函数
# ============================================================


def parse_novel_to_script(
    novel_text: str,
    novel_title: str,
    config: AIConfig | None = None,
    max_retries: int = 2,
    progress_callback=None,
) -> ScriptYAML:
    """
    调用 AI 大模型将小说文本转换为结构化剧本。

    完整处理流程：
    1. 判断文本长度，短文本直接单次调用，长文本走分片流程
    2. 长文本：前置人物预提取 → 滑动分片 → 逐片AI转换 → 摘要锚定 → 合并
    3. YAML三层防护：提取纯净YAML → 语法校验修复 → Schema校验
    4. 心理占比巡检：psy超标时触发二次精简
    5. 后端ID全局重排

    Args:
        novel_text: 预处理后的小说纯正文文本
        novel_title: 小说/原著名称
        config: AI模型配置实例，为 None 时使用默认配置
        max_retries: 最大重试次数，当 AI 返回格式不合法时触发
        progress_callback: 可选的进度回调函数，签名为 callback(event_type, data)
                         event_type 包括: start/preprocessing/preprocessed/
                         extracting_chars/chars_extracted/chunking/chunks_ready/
                         chunk_start/chunk_done/chunk_fail/merging/done/error

    Returns:
        ScriptYAML: 校验通过的结构化剧本数据

    Raises:
        ValueError: API Key 未配置时抛出
        ConnectionError: API 网络连接失败且重试耗尽时抛出
        RuntimeError: AI 返回数据始终无法通过 Schema 校验时抛出

    Note:
        - 短文本（≤3500字）走单次调用路径
        - 长文本走分片路径，含人物缓存和摘要锚定
    """
    if config is None:
        config = AIConfig()

    if not config.api_key:
        raise ValueError("API Key 未配置，请在设置中填写有效的 API Key")

    # 进度回调辅助函数
    def _emit(event_type: str, data: dict | None = None) -> None:
        """安全调用进度回调，忽略异常"""
        if progress_callback:
            try:
                progress_callback(event_type, data or {})
            except Exception:
                pass

    _emit("start", {"text_length": len(novel_text), "novel_title": novel_title})

    # 初始化 OpenAI 客户端
    client = OpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout,
    )

    text_length = len(novel_text)

    # 短文本：直接单次调用
    if text_length <= CHUNK_SIZE:
        _emit("parsing_single", {"text_length": text_length})
        result = _parse_single_chunk(
            novel_text, novel_title, config, client, max_retries, progress_callback
        )
        _emit("done", {
            "scenes": len(result.script_scenes),
            "characters": len(result.global_characters),
        })
        return result

    # 长文本：分片处理流程
    _log(f"[AI] 文本长度 {text_length} 字，进入分片处理模式（阈值: {CHUNK_SIZE}）")
    _log(f"[AI] AI配置: model={config.model_name}, base_url={config.base_url}, api_key={'***' if config.api_key else '(空)'}")
    _emit("parsing_chunks", {"text_length": text_length})
    result = _parse_with_chunking(
        novel_text, novel_title, config, client, max_retries, progress_callback
    )
    _emit("done", {
        "scenes": len(result.script_scenes),
        "characters": len(result.global_characters),
    })
    return result


# ============================================================
# 短文本单次调用
# ============================================================


def _parse_single_chunk(
    novel_text: str,
    novel_title: str,
    config: AIConfig,
    client: OpenAI,
    max_retries: int,
    progress_callback=None,
) -> ScriptYAML:
    """
    短文本单次调用路径，无需分片。

    Args:
        novel_text: 小说正文
        novel_title: 小说名称
        config: AI配置
        client: OpenAI客户端
        max_retries: 最大重试次数
        progress_callback: 进度回调函数

    Returns:
        ScriptYAML: 结构化剧本数据

    Raises:
        RuntimeError: AI解析失败且重试耗尽时抛出
    """
    def _emit(event_type: str, data: dict | None = None) -> None:
        if progress_callback:
            try:
                progress_callback(event_type, data or {})
            except Exception:
                pass

    _emit("calling_llm", {"mode": "single", "retries": max_retries})
    system_prompt = _load_prompt("system_prompt.txt")
    user_message = _build_user_message(novel_text, novel_title)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            ai_output = _call_llm(client, config, system_prompt, user_message)
            yaml_text = _extract_and_repair_yaml(ai_output)
            script_data = ScriptYAML.from_yaml(yaml_text)
            # 心理占比巡检
            script_data = _check_and_refine_psy(script_data, client, config)
            return script_data
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                continue
            raise RuntimeError(
                f"AI 解析失败（已重试 {max_retries} 次）: {str(last_error)}"
            ) from last_error

    raise RuntimeError(f"AI 解析失败: {last_error}")


# ============================================================
# 长文本分片处理
# ============================================================


def _parse_with_chunking(
    novel_text: str,
    novel_title: str,
    config: AIConfig,
    client: OpenAI,
    max_retries: int,
    progress_callback=None,
) -> ScriptYAML:
    """
    长文本分片处理主流程。

    步骤：
    1. 前置人物预提取（全局人物缓存）
    2. 滑动分片切割
    3. 逐片AI转换（注入人物缓存 + 上文摘要）
    4. 后端汇总合并（ID全局重排）
    5. 心理占比巡检

    Args:
        novel_text: 小说正文
        novel_title: 小说名称
        config: AI配置
        client: OpenAI客户端
        max_retries: 最大重试次数
        progress_callback: 进度回调函数

    Returns:
        ScriptYAML: 合并后的完整结构化剧本数据

    Raises:
        RuntimeError: 所有分片均解析失败时抛出
    """
    def _emit(event_type: str, data: dict | None = None) -> None:
        if progress_callback:
            try:
                progress_callback(event_type, data or {})
            except Exception:
                pass

    # 步骤1：前置人物预提取
    _emit("extracting_chars", {})
    char_cache = _extract_characters(novel_text, client, config)
    _emit("chars_extracted", {"char_count": len(char_cache.get_all_names())})

    # 步骤2：滑动分片
    _emit("chunking", {"text_length": len(novel_text)})
    chunks = _split_into_chunks(novel_text)
    total_chunks = len(chunks)
    _log(f"[AI] 共切割为 {total_chunks} 个分片")
    _emit("chunks_ready", {"total": total_chunks})

    # 步骤3：逐片AI转换
    chunk_results: list[ScriptYAML] = []
    prev_summary = ""
    id_offset = 1

    for i, chunk_text in enumerate(chunks):
        chunk_index = i + 1
        total_chunks = len(chunks)

        # 构建分片上下文
        ctx = ChunkContext(
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            prev_summary=prev_summary,
            id_offset=id_offset,
            established_scenes=[
                f"S{idx:02d}" for idx in range(1, id_offset)
            ],
            established_characters=list(char_cache.get_all_names()),
        )

        # 构建分片专用提示词
        system_prompt = _build_chunk_system_prompt(ctx, char_cache)
        user_message = _build_chunk_user_message(
            chunk_text, novel_title, chunk_index, total_chunks
        )

        # 调用AI前等待，避免连续请求触发速率限制
        if i > 0:
            _log(f"[AI] [WAIT] 等待 {CHUNK_CALL_INTERVAL}s 后处理分片 {chunk_index}/{total_chunks} ...")
            _emit("chunk_wait", {"index": chunk_index, "total": total_chunks, "wait_seconds": CHUNK_CALL_INTERVAL})
            time.sleep(CHUNK_CALL_INTERVAL)

        # 调用AI（带重试）
        _emit("chunk_start", {"index": chunk_index, "total": total_chunks})
        chunk_result = _parse_chunk_with_retry(
            system_prompt, user_message, config, client, max_retries
        )
        if chunk_result is None:
            _log(f"[AI] [FAIL] 分片 {chunk_index}/{total_chunks} 解析失败，跳过")
            _emit("chunk_fail", {"index": chunk_index, "total": total_chunks})
            continue

        scene_count = len(chunk_result.script_scenes)
        _log(f"[AI] [OK] 分片 {chunk_index}/{total_chunks} 解析成功（{scene_count} 场戏）")
        _emit("chunk_done", {
            "index": chunk_index, "total": total_chunks, "scenes": scene_count,
            "completed": len(chunk_results) + 1,
        })
        chunk_results.append(chunk_result)

        # 提取摘要锚点
        prev_summary = _summarize_chunk_output(chunk_result)
        # 更新ID偏移
        id_offset = _calc_next_id_offset(chunk_result, id_offset)

    if not chunk_results:
        _emit("error", {"message": "所有分片解析均失败"})
        raise RuntimeError(
            f"所有分片解析均失败，无法生成剧本（共 {len(chunks)} 个分片）。"
            f"请检查：1) API Key / Base URL 是否正确 2) 模型名称是否有效 "
            f"3) 后端终端日志中的 [AI] 详细错误信息"
        )

    # 步骤4：后端汇总合并
    _emit("merging", {"completed_chunks": len(chunk_results), "total_chunks": total_chunks})
    merged = _merge_chunk_results(chunk_results, novel_title, char_cache)

    # 步骤5：心理占比巡检
    _emit("refining_psy", {})
    merged = _check_and_refine_psy(merged, client, config)

    return merged


# ============================================================
# 滑动分片
# ============================================================


def _split_into_chunks(text: str) -> list[str]:
    """
    将长文本按滑动窗口策略切割为多个分片。

    切割规则：
    - 单片正文阈值 3500 汉字
    - 章节边界优先切分，不腰斩单章中间剧情
    - 相邻分片 600 字上下文重叠区

    Args:
        text: 预处理后的小说全文

    Returns:
        list[str]: 分片文本列表，每片不超过 CHUNK_SIZE 字

    Note:
        章节边界通过正则匹配「第X章」等标记识别
    """
    if len(text) <= CHUNK_SIZE:
        return [text]

    # 识别章节边界
    chapter_pattern = re.compile(
        r"^第[一二三四五六七八九十百千零〇\d]+[章节回][\s：:：]?.*?$",
        re.MULTILINE,
    )
    chapter_positions = [m.start() for m in chapter_pattern.finditer(text)]

    # 无章节标记时按固定字数切割
    if not chapter_positions:
        return _split_by_fixed_size(text)

    # 按章节边界切割
    chunks = []
    chapter_positions.append(len(text))  # 添加末尾位置

    current_chunk = ""
    for i in range(len(chapter_positions) - 1):
        chapter_start = chapter_positions[i]
        chapter_end = chapter_positions[i + 1]
        chapter_text = text[chapter_start:chapter_end]

        # 如果当前分片 + 本章仍不超过阈值，合并
        if len(current_chunk) + len(chapter_text) <= CHUNK_SIZE:
            current_chunk += chapter_text
        else:
            # 当前分片已满，先保存
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            # 如果单章超长，需要按固定大小再切
            if len(chapter_text) > CHUNK_SIZE:
                sub_chunks = _split_by_fixed_size(chapter_text)
                chunks.extend(sub_chunks[:-1])
                current_chunk = sub_chunks[-1] if sub_chunks else ""
            else:
                # 新分片 = 上一片末尾重叠区 + 本章
                overlap = current_chunk[-CHUNK_OVERLAP:] if len(current_chunk) > CHUNK_OVERLAP else current_chunk
                current_chunk = overlap + chapter_text

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _split_by_fixed_size(text: str) -> list[str]:
    """
    按固定字数切割文本，带重叠区。

    Args:
        text: 待切割文本

    Returns:
        list[str]: 切割后的文本片段列表

    Note:
        每片 CHUNK_SIZE 字，相邻片重叠 CHUNK_OVERLAP 字
    """
    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        chunks.append(chunk)
        # 下一片起始位置回退重叠区
        next_start = end - CHUNK_OVERLAP
        # 确保前进：下一片起始必须大于当前起始
        if next_start <= start:
            start = end
        else:
            start = next_start

    return chunks


# ============================================================
# 全局人物预提取
# ============================================================


def _extract_characters(
    novel_text: str, client: OpenAI, config: AIConfig
) -> CharacterCache:
    """
    前置轻量LLM调用，从全文档提取人物信息生成全局缓存。

    取全文前5000字 + 后2000字作为输入，调用低成本模型提取
    所有人物的标准名称、别名、人设描述。

    Args:
        novel_text: 小说全文
        client: OpenAI客户端
        config: AI配置

    Returns:
        CharacterCache: 全局人物缓存实例

    Note:
        - 提取失败时返回空缓存，不阻塞主流程
        - 使用低temperature确保提取稳定性
    """
    # 截取首尾文本作为输入
    head = novel_text[:CHAR_EXTRACT_HEAD]
    tail = novel_text[-CHAR_EXTRACT_TAIL:] if len(novel_text) > CHAR_EXTRACT_HEAD + CHAR_EXTRACT_TAIL else ""
    sample_text = head + "\n...\n" + tail if tail else head

    prompt = _load_prompt("character_extraction_prompt.txt")

    try:
        response = client.chat.completions.create(
            model=config.model_name,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"请从以下小说文本中提取人物信息：\n\n{sample_text}"},
            ],
            temperature=0.1,
            max_tokens=2048,
        )

        content = response.choices[0].message.content or ""
        # 提取JSON
        json_match = re.search(r"\[.*\]", content, re.DOTALL)
        if json_match:
            characters = json.loads(json_match.group())
            return CharacterCache(characters=characters)

    except (json.JSONDecodeError, Exception):
        pass  # 提取失败不阻塞主流程

    return CharacterCache()


# ============================================================
# 分片提示词构建
# ============================================================


def _build_chunk_system_prompt(ctx: ChunkContext, char_cache: CharacterCache) -> str:
    """
    构建分片专用的系统提示词，注入人物缓存和上文摘要。

    Args:
        ctx: 分片上下文信息
        char_cache: 全局人物缓存

    Returns:
        str: 填充完毕的分片系统提示词
    """
    template = _load_prompt("system_prompt_chunk.txt")

    # 构建已确定上下文
    established_context = "首次分片，暂无" if ctx.chunk_index == 1 else (
        f"已生成场景：{', '.join(ctx.established_scenes[-5:])}；"
        f"已确定人物：{', '.join(ctx.established_characters[:10])}"
    )

    return template.format(
        character_cache=char_cache.to_prompt_text(),
        prev_summary=ctx.prev_summary or "这是第一个分片，无上文摘要",
        established_context=established_context,
        chunk_index=ctx.chunk_index,
        total_chunks=ctx.total_chunks,
        id_offset=ctx.id_offset,
    )


def _build_chunk_user_message(
    chunk_text: str, novel_title: str, chunk_index: int, total_chunks: int
) -> str:
    """
    构建分片的用户消息。

    Args:
        chunk_text: 当前分片正文
        novel_title: 小说名称
        chunk_index: 当前分片序号
        total_chunks: 总分片数

    Returns:
        str: 拼接完成的用户消息文本
    """
    return (
        f"本次转换原著：【{novel_title}】\n"
        f"当前为第 {chunk_index}/{total_chunks} 个分片\n"
        f"小说正文内容：\n{chunk_text}"
    )


# ============================================================
# 分片AI调用（带重试）
# ============================================================


def _parse_chunk_with_retry(
    system_prompt: str,
    user_message: str,
    config: AIConfig,
    client: OpenAI,
    max_retries: int,
) -> ScriptYAML | None:
    """
    对单个分片执行AI调用，带重试机制。

    Args:
        system_prompt: 系统提示词
        user_message: 用户消息
        config: AI配置
        client: OpenAI客户端
        max_retries: 最大重试次数

    Returns:
        ScriptYAML | None: 解析成功的剧本数据，失败返回None

    Note:
        失败时打印详细错误日志供排查，返回None由上层决定是否继续
    """
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            ai_output = _call_llm(client, config, system_prompt, user_message)
            yaml_text = _extract_and_repair_yaml(ai_output)
            return ScriptYAML.from_yaml(yaml_text)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                _log(
                    f"[AI] 分片重试 {attempt + 1}/{max_retries}: "
                    f"{type(e).__name__}: {str(e)[:200]}"
                )
                continue
            # 最终失败，打印完整错误
            _log(
                f"[AI] 分片解析最终失败（已重试{max_retries}次）: "
                f"{type(e).__name__}: {str(e)[:500]}"
            )

    return None


# ============================================================
# 摘要锚定
# ============================================================


def _summarize_chunk_output(chunk_result: ScriptYAML) -> str:
    """
    从分片AI输出中提炼剧情摘要，供下一分片使用。

    提取规则：
    - 优先使用各场景的 scene_summary 拼接
    - 截断至 SUMMARY_MAX_LENGTH 字

    Args:
        chunk_result: 当前分片的剧本数据

    Returns:
        str: 150字以内的剧情摘要文本
    """
    summaries = []
    for scene in chunk_result.script_scenes:
        if scene.scene_summary:
            summaries.append(scene.scene_summary)

    combined = "；".join(summaries)
    if len(combined) > SUMMARY_MAX_LENGTH:
        combined = combined[:SUMMARY_MAX_LENGTH - 3] + "..."

    return combined or "暂无摘要"


# ============================================================
# 后端汇总合并
# ============================================================


def _calc_next_id_offset(chunk_result: ScriptYAML, current_offset: int) -> int:
    """
    计算下一个分片的ID起始偏移量。

    Args:
        chunk_result: 当前分片的剧本数据
        current_offset: 当前偏移量

    Returns:
        int: 下一个分片应使用的ID起始值
    """
    max_scene_id = max(
        (s.scene_id for s in chunk_result.script_scenes), default=0
    )
    max_unit_id = 0
    for scene in chunk_result.script_scenes:
        for unit in scene.scene_content:
            max_unit_id = max(max_unit_id, unit.unit_id)
    max_char_id = max(
        (c.char_id for c in chunk_result.global_characters), default=0
    )
    return current_offset + max(max_scene_id, max_unit_id, max_char_id)


def _merge_chunk_results(
    chunk_results: list[ScriptYAML],
    novel_title: str,
    char_cache: CharacterCache,
) -> ScriptYAML:
    """
    将多个分片的YAML结果合并为完整剧本，ID全局重排。

    合并规则：
    - scene_id、unit_id、char_id 全局自增重排
    - scene_serial 按合并顺序重编（S01、S02...）
    - global_characters 去重合并（同名人物只保留一条）
    - script_meta 取第一个分片的元数据，更新章节范围
    - adapt_rule_note 拼接所有分片的改编说明

    Args:
        chunk_results: 各分片的剧本数据列表
        novel_title: 小说名称
        char_cache: 全局人物缓存（用于补充人物库）

    Returns:
        ScriptYAML: 合并后的完整剧本数据
    """
    all_scenes: list[ScriptScene] = []
    all_characters: list[GlobalCharacter] = []
    all_notes: list[str] = []

    scene_id_counter = 1
    unit_id_counter = 1
    char_id_counter = 1
    char_name_map: dict[str, int] = {}  # 名称 -> char_id 映射，用于去重

    for chunk in chunk_results:
        # 合并人物库（去重）
        for char in chunk.global_characters:
            # 尝试匹配已有人物（标准名或别名）
            matched_id = _find_character_id(char.char_name, char_name_map, char_cache)
            if matched_id is not None:
                continue  # 已存在，跳过
            char_name_map[char.char_name] = char_id_counter
            all_characters.append(
                GlobalCharacter(
                    char_id=char_id_counter,
                    char_name=char.char_name,
                    char_profile=char.char_profile,
                )
            )
            char_id_counter += 1

        # 合并场景
        for scene in chunk.script_scenes:
            new_units = []
            for unit in scene.scene_content:
                new_units.append(
                    SceneContentUnit(
                        unit_id=unit_id_counter,
                        unit_type=unit.unit_type,
                        character=unit.character,
                        content=unit.content,
                    )
                )
                unit_id_counter += 1

            all_scenes.append(
                ScriptScene(
                    scene_id=scene_id_counter,
                    scene_serial=f"S{scene_id_counter:02d}",
                    scene_attr=scene.scene_attr,
                    scene_summary=scene.scene_summary,
                    scene_content=new_units,
                    scene_note=scene.scene_note,
                )
            )
            scene_id_counter += 1

        # 收集改编说明
        if chunk.adapt_rule_note:
            all_notes.append(chunk.adapt_rule_note)

    # 补充人物缓存中未出现在chunk结果中的人物
    for char_info in char_cache.characters:
        name = char_info.get("char_name", "")
        if name and name not in char_name_map:
            char_name_map[name] = char_id_counter
            all_characters.append(
                GlobalCharacter(
                    char_id=char_id_counter,
                    char_name=name,
                    char_profile=char_info.get("char_profile", ""),
                )
            )
            char_id_counter += 1

    # 构建元数据
    meta = chunk_results[0].script_meta.model_copy()
    meta.original_novel_title = novel_title

    return ScriptYAML(
        script_meta=meta,
        script_scenes=all_scenes,
        global_characters=all_characters,
        adapt_rule_note="\n".join(all_notes) if all_notes else "多分片合并生成",
    )


def _find_character_id(
    name: str, char_name_map: dict[str, int], char_cache: CharacterCache
) -> int | None:
    """
    在已有字符映射和缓存中查找人物ID，支持别名匹配。

    Args:
        name: 待查找的人物名称
        char_name_map: 已有人物名称到ID的映射
        char_cache: 全局人物缓存

    Returns:
        int | None: 匹配到的人物ID，未匹配返回None
    """
    # 直接匹配
    if name in char_name_map:
        return char_name_map[name]
    # 在缓存的别名中查找
    for char_info in char_cache.characters:
        aliases = char_info.get("aliases", [])
        std_name = char_info.get("char_name", "")
        if name in aliases and std_name in char_name_map:
            return char_name_map[std_name]
    return None


# ============================================================
# YAML 三层防护
# ============================================================


def _extract_and_repair_yaml(ai_output: str) -> str:
    """
    YAML 三层防护：提取 + 修复 + 校验。

    第一层：提示词强约束（在提示词中已实现）
    第二层：后置语法校验与自动修复
    第三层：兜底补全（在调用方重试逻辑中实现）

    Args:
        ai_output: AI 原始返回文本

    Returns:
        str: 修复后的纯净 YAML 文本

    Note:
        修复策略：
        1. 剥离 markdown 代码块包裹
        2. 剔除 YAML 前后的非 YAML 文本
        3. 修复常见缩进错误
        4. 验证 YAML 可解析性
    """
    text = ai_output.strip()

    # 步骤1：剥离 markdown 代码块
    code_block_pattern = r"```(?:ya?ml)?\s*\n?(.*?)\n?```"
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    # 步骤2：剔除 YAML 前后的非 YAML 文本
    # 匹配 script_meta: 开头到文档末尾的有效内容
    yaml_start = re.search(r"^script_meta\s*:", text, re.MULTILINE)
    if yaml_start:
        text = text[yaml_start.start():]

    # 步骤3：修复常见缩进问题
    text = _fix_yaml_indentation(text)

    # 步骤4：字段名自动映射 — 将 AI 返回的错误字段名替换为正确的 Schema 字段名
    text = _repair_field_names(text)

    # 步骤5：缺失必填字段自动注入
    text = _inject_missing_fields(text)

    # 步骤6：验证可解析性
    try:
        yaml.safe_load(text)
    except yaml.YAMLError:
        # 尝试更激进的修复：移除可能导致问题的行
        text = _aggressive_yaml_repair(text)

    return text


def _fix_yaml_indentation(text: str) -> str:
    """
    修复 YAML 中常见的缩进错误。

    Args:
        text: YAML 文本

    Returns:
        str: 修复缩进后的 YAML 文本

    Note:
        修复策略：
        - 将 Tab 替换为2空格
        - 移除行尾空白
        - 修正列表项缩进不一致
    """
    # Tab → 2空格
    text = text.replace("\t", "  ")
    # 移除行尾空白
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines)


def _repair_field_names(yaml_text: str) -> str:
    """
    字段名自动映射 — 将 AI 模型返回的错误字段名替换为 Schema 要求的正确字段名。

    某些模型（如 LongCat）不严格遵循提示词中的 Schema 定义，会使用自己的字段命名。
    此函数通过正则替换将常见错误映射到正确字段名。

    采用上下文感知策略：根据缩进层级判断字段所属区域，
    同一字段名在不同层级可能映射到不同目标（如 name 在 meta 下→script_title，
    在 character 下→char_name）。

    Args:
        yaml_text: AI 返回的原始 YAML 文本

    Returns:
        str: 字段名已修正的 YAML 文本
    """
    # ============================================================
    # 全局无歧义映射（任何层级都适用的映射）
    # 格式：(旧名, 新名) — 旧名和新名不同时才会替换
    # ============================================================
    global_mappings = [
        # === script_meta 层级（无歧义）===
        ("script_name", "script_title"),
        ("剧本名称", "script_title"),
        ("剧名", "script_title"),
        ("original_title", "original_novel_title"),
        ("原著名称", "original_novel_title"),
        ("小说原名", "original_novel_title"),
        ("novel_title", "original_novel_title"),
        ("章节范围", "chapter_range"),
        ("chapters", "chapter_range"),
        ("改编概要", "adapt_rule_note"),
        ("adapt_summary", "adapt_rule_note"),

        # === SceneAttr 层级（无歧义）===
        ("place", "location"),
        ("地点", "location"),

        # === SceneContentUnit 层级（无歧义）===
        ("speaker", "character"),
        ("character_name", "character"),
        ("角色", "character"),
        ("text", "content"),
        ("正文", "content"),
        ("对话内容", "content"),

        # === GlobalCharacter 层级（无歧义）===
        ("character_id", "char_id"),
        ("简介", "char_profile"),
        ("description", "char_profile"),
        ("人物描述", "char_profile"),
        ("profile", "char_profile"),
        ("角色名", "char_name"),
    ]

    # ============================================================
    # 上下文感知映射：根据缩进层级判断
    # 同名字段在不同层级映射到不同目标
    # ============================================================

    lines = yaml_text.split("\n")
    result_lines = []
    current_section = "root"  # root / meta / scenes / characters

    for line in result_lines if False else lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # 检测当前区域
        if stripped.startswith("script_meta:"):
            current_section = "meta"
        elif stripped.startswith("script_scenes:"):
            current_section = "scenes"
        elif stripped.startswith("global_characters:"):
            current_section = "characters"
        elif indent == 0 and stripped and not stripped.startswith("-") and stripped.endswith(":"):
            # 其他顶级键，退出当前区域
            if stripped.startswith("adapt_rule_note:"):
                current_section = "root"

        # 先应用全局无歧义映射
        modified_line = line
        for old_name, new_name in global_mappings:
            pattern = rf"^(\s*){re.escape(old_name)}\s*:"
            match = re.match(pattern, modified_line)
            if match:
                new_line = re.sub(pattern, rf"\g<1>{new_name}:", modified_line)
                if new_line != modified_line:
                    _log(f"[REPAIR] 字段映射: '{old_name}' → '{new_name}' (1 处)")
                    modified_line = new_line

        # 再应用上下文感知映射
        # title → script_title (meta层) 或 char_name (characters层)
        if re.match(r"^(\s*)title\s*:", modified_line):
            if current_section == "meta":
                new_line = re.sub(r"^(\s*)title\s*:", r"\g<1>script_title:", modified_line)
                if new_line != modified_line:
                    _log("[REPAIR] 字段映射: 'title' → 'script_title' (1 处)")
                    modified_line = new_line

        # name → script_title (meta层) 或 char_name (characters层)
        if re.match(r"^(\s*)name\s*:", modified_line):
            if current_section == "meta":
                new_line = re.sub(r"^(\s*)name\s*:", r"\g<1>script_title:", modified_line)
                _log("[REPAIR] 字段映射: 'name' → 'script_title' (1 处)")
                modified_line = new_line
            elif current_section == "characters":
                new_line = re.sub(r"^(\s*)name\s*:", r"\g<1>char_name:", modified_line)
                _log("[REPAIR] 字段映射: 'name' → 'char_name' (1 处)")
                modified_line = new_line

        # type → scene_type (scenes层, scene_attr内) 或 unit_type (scenes层, unit内)
        if re.match(r"^(\s*)type\s*:", modified_line):
            if current_section == "scenes":
                # 根据缩进判断：scene_attr内(6+空格) → scene_type, unit内(6+空格) → unit_type
                if indent >= 8:
                    new_line = re.sub(r"^(\s*)type\s*:", r"\g<1>unit_type:", modified_line)
                    _log("[REPAIR] 字段映射: 'type' → 'unit_type' (1 处)")
                    modified_line = new_line
                elif indent >= 4:
                    new_line = re.sub(r"^(\s*)type\s*:", r"\g<1>scene_type:", modified_line)
                    _log("[REPAIR] 字段映射: 'type' → 'scene_type' (1 处)")
                    modified_line = new_line

        # summary → scene_summary (scenes层) 或 adapt_rule_note (meta层)
        if re.match(r"^(\s*)summary\s*:", modified_line):
            if current_section == "scenes":
                new_line = re.sub(r"^(\s*)summary\s*:", r"\g<1>scene_summary:", modified_line)
                _log("[REPAIR] 字段映射: 'summary' → 'scene_summary' (1 处)")
                modified_line = new_line
            elif current_section == "meta":
                new_line = re.sub(r"^(\s*)summary\s*:", r"\g<1>adapt_rule_note:", modified_line)
                _log("[REPAIR] 字段映射: 'summary' → 'adapt_rule_note' (1 处)")
                modified_line = new_line

        # synopsis → scene_summary (scenes层)
        if re.match(r"^(\s*)synopsis\s*:", modified_line):
            if current_section == "scenes":
                new_line = re.sub(r"^(\s*)synopsis\s*:", r"\g<1>scene_summary:", modified_line)
                _log("[REPAIR] 字段映射: 'synopsis' → 'scene_summary' (1 处)")
                modified_line = new_line

        # time → time_type (scenes层, scene_attr内)
        if re.match(r"^(\s*)time\s*:", modified_line):
            if current_section == "scenes":
                new_line = re.sub(r"^(\s*)time\s*:", r"\g<1>time_type:", modified_line)
                _log("[REPAIR] 字段映射: 'time' → 'time_type' (1 处)")
                modified_line = new_line

        # id → scene_id (scenes层, 4空格) 或 unit_id (scenes层, 6+空格)
        if re.match(r"^(\s*)id\s*:", modified_line):
            if current_section == "scenes":
                if indent >= 6:
                    new_line = re.sub(r"^(\s*)id\s*:", r"\g<1>unit_id:", modified_line)
                    _log("[REPAIR] 字段映射: 'id' → 'unit_id' (1 处)")
                    modified_line = new_line
                elif indent >= 4:
                    new_line = re.sub(r"^(\s*)id\s*:", r"\g<1>scene_id:", modified_line)
                    _log("[REPAIR] 字段映射: 'id' → 'scene_id' (1 处)")
                    modified_line = new_line

        result_lines.append(modified_line)

    return "\n".join(result_lines)


def _inject_missing_fields(yaml_text: str) -> str:
    """
    自动注入 AI 输出中缺失的必填字段。

    某些模型会遗漏必填字段（如 original_novel_title、chapter_range、scene_serial），
    导致 Pydantic 校验失败。此函数在 YAML 文本中检测并注入这些缺失字段。

    Args:
        yaml_text: 经过字段名修复后的 YAML 文本

    Returns:
        str: 注入缺失字段后的 YAML 文本

    Note:
        注入的字段使用合理的默认值或空字符串，确保通过 Schema 校验。
    """
    lines = yaml_text.split("\n")
    result_lines = list(lines)

    # 检测 script_meta 中缺失的字段
    meta_fields_present = set()
    in_meta = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("script_meta:"):
            in_meta = True
            continue
        if in_meta:
            indent = len(line) - len(stripped)
            if indent == 0 and stripped and not stripped.startswith("#"):
                in_meta = False
                continue
            # 提取字段名
            field_match = re.match(r"^\s+(\w+)\s*:", stripped)
            if field_match:
                meta_fields_present.add(field_match.group(1))

    # 需要注入的 meta 字段（在 script_meta: 行之后插入）
    meta_injections = []
    if "original_novel_title" not in meta_fields_present:
        meta_injections.append("  original_novel_title: \"\"")
        _log("[REPAIR] 注入缺失字段: 'original_novel_title'")
    if "chapter_range" not in meta_fields_present:
        meta_injections.append("  chapter_range: \"\"")
        _log("[REPAIR] 注入缺失字段: 'chapter_range'")
    if "create_time" not in meta_fields_present:
        from datetime import datetime
        meta_injections.append(f"  create_time: \"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\"")
        _log("[REPAIR] 注入缺失字段: 'create_time'")

    # 在 script_meta: 行之后插入缺失字段
    if meta_injections:
        new_lines = []
        for line in result_lines:
            new_lines.append(line)
            if line.lstrip().startswith("script_meta:"):
                for injection in meta_injections:
                    new_lines.append(injection)
        result_lines = new_lines

    # 检测 script_scenes 中缺失的 scene_serial 字段
    # 为每个 scene 自动生成 scene_serial
    has_serial = any("scene_serial:" in line for line in result_lines)
    if not has_serial:
        new_lines = []
        scene_counter = 0
        for line in result_lines:
            stripped = line.lstrip()
            # 检测 scene 条目开始（如 "  - scene_id:"）
            if re.match(r"^\s+-\s+scene_id\s*:", stripped) or re.match(r"^\s+-\s+id\s*:", stripped):
                scene_counter += 1
                new_lines.append(line)
                # 在 scene_id 行之后插入 scene_serial
                indent_match = re.match(r"^(\s+)-", line)
                if indent_match:
                    base_indent = indent_match.group(1)
                    new_lines.append(f"{base_indent}  scene_serial: \"S{scene_counter:02d}\"")
                    _log(f"[REPAIR] 注入缺失字段: 'scene_serial' → S{scene_counter:02d}")
                else:
                    new_lines.append(f"    scene_serial: \"S{scene_counter:02d}\"")
            else:
                new_lines.append(line)
        result_lines = new_lines

    return "\n".join(result_lines)


def _aggressive_yaml_repair(text: str) -> str:
    """
    激进的 YAML 修复策略，处理 safe_load 仍失败的情况。

    Args:
        text: YAML 文本

    Returns:
        str: 修复后的 YAML 文本

    Note:
        策略：逐行尝试移除可能导致解析错误的行（如含特殊字符的注释行）
    """
    lines = text.split("\n")
    clean_lines = []
    for line in lines:
        # 移除 YAML 注释行（# 开头的独立注释）
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # 移除空注释
        if "#" in line and not line.strip().startswith("-"):
            line = re.sub(r"\s*#.*$", "", line)
        clean_lines.append(line)

    result = "\n".join(clean_lines)

    # 最终验证
    try:
        yaml.safe_load(result)
        return result
    except yaml.YAMLError:
        # 无法修复，返回原文让 Schema 校验报具体错误
        return text


# ============================================================
# 心理占比巡检
# ============================================================


def _check_and_refine_psy(
    script_data: ScriptYAML, client: OpenAI, config: AIConfig
) -> ScriptYAML:
    """
    检查 psy（心理）单元占比，超标时触发二次精简。

    巡检规则：
    - 统计全剧本四类单元数量
    - psy 占比超过 8% 时触发精简
    - 精简方式：调用 LLM 将部分 psy 转化为 action/narration 或删除

    Args:
        script_data: 待巡检的剧本数据
        client: OpenAI客户端
        config: AI配置

    Returns:
        ScriptYAML: 巡检后的剧本数据（可能已精简）

    Note:
        精简失败时返回原数据，不阻塞流程
    """
    total_units = 0
    psy_units = 0

    for scene in script_data.script_scenes:
        for unit in scene.scene_content:
            total_units += 1
            if unit.unit_type == "psy":
                psy_units += 1

    if total_units == 0:
        return script_data

    psy_ratio = psy_units / total_units
    if psy_ratio <= PSY_RATIO_THRESHOLD:
        return script_data

    # psy 超标，触发二次精简
    try:
        refinement_prompt = _load_prompt("psy_refinement_prompt.txt")
        yaml_text = script_data.to_yaml()

        response = client.chat.completions.create(
            model=config.model_name,
            messages=[
                {"role": "system", "content": refinement_prompt},
                {"role": "user", "content": yaml_text},
            ],
            temperature=0.3,
            max_tokens=config.max_tokens,
        )

        content = response.choices[0].message.content or ""
        refined_yaml = _extract_and_repair_yaml(content)
        refined_data = ScriptYAML.from_yaml(refined_yaml)

        # 验证精简后psy占比
        refined_psy = sum(
            1 for s in refined_data.script_scenes for u in s.scene_content if u.unit_type == "psy"
        )
        refined_total = sum(len(s.scene_content) for s in refined_data.script_scenes)
        if refined_total > 0 and refined_psy / refined_total <= PSY_RATIO_THRESHOLD:
            return refined_data

    except Exception:
        pass  # 精简失败返回原数据

    return script_data


# ============================================================
# 通用工具函数
# ============================================================


def _load_prompt(filename: str) -> str:
    """
    从提示词模板文件加载内容。

    按以下优先级查找文件：
    1. backend/prompts/{filename}（项目内嵌路径）
    2. prompts/{filename}（工作目录路径）

    Args:
        filename: 提示词文件名

    Returns:
        str: 提示词的完整文本内容

    Raises:
        FileNotFoundError: 提示词文件不存在时抛出
    """
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "prompts", filename),
        os.path.join("prompts", filename),
        os.path.join("backend", "prompts", filename),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()

    raise FileNotFoundError(
        f"提示词文件 prompts/{filename} 不存在，请确认项目文件完整性"
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
    chapter_matches = re.findall(
        r"第[一二三四五六七八九十百千零〇\d]+章", novel_text
    )
    chapter_hint = f"第1-{len(chapter_matches)}章" if chapter_matches else "全文"

    return (
        f"本次转换原著：【{novel_title}】\n"
        f"本次转换章节：【{chapter_hint}】\n"
        f"小说正文内容：\n{novel_text}"
    )


def _call_llm(
    client: OpenAI, config: AIConfig, system_prompt: str, user_message: str
) -> str:
    """
    调用大语言模型 API 并返回原始文本输出。

    内置 429 速率限制自动退避重试机制：
    - 检测到 RateLimitError 时按指数退避等待后自动重试
    - 退避间隔从 5s 开始，每次翻倍，最大 60s
    - 最多退避重试 3 次（独立于外层 max_retries）

    Args:
        client: OpenAI客户端实例
        config: AI配置参数
        system_prompt: 系统提示词
        user_message: 用户消息

    Returns:
        str: AI 返回的原始文本内容

    Raises:
        RuntimeError: AI 返回空内容或限流重试耗尽时抛出
    """
    # 导入 openai 的 RateLimitError 用于精确捕获
    from openai import RateLimitError

    for retry in range(RATE_LIMIT_MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=config.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("AI 返回了空内容")

            return content

        except RateLimitError as e:
            if retry < RATE_LIMIT_MAX_RETRIES:
                # 指数退避：5s → 10s → 20s ...
                wait_time = min(
                    RATE_LIMIT_BACKOFF_START * (2 ** retry),
                    RATE_LIMIT_BACKOFF_MAX,
                )
                _log(
                    f"[AI] [429-BACKOFF] 触发 429 速率限制，等待 {wait_time:.0f}s 后重试 "
                    f"({retry + 1}/{RATE_LIMIT_MAX_RETRIES})"
                )
                time.sleep(wait_time)
                continue
            else:
                raise RuntimeError(
                    f"API 速率限制，已退避重试 {RATE_LIMIT_MAX_RETRIES} 次仍失败: {str(e)[:200]}"
                ) from e
