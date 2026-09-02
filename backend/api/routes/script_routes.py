"""
剧本转换 API 路由模块

提供小说转剧本的核心 HTTP 接口，包括：
- POST /api/script/convert        — 小说文本转换为结构化YAML剧本（同步）
- POST /api/script/convert-stream — 小说文本转换为结构化YAML剧本（SSE流式）
- POST /api/script/test-connection — 测试LLM模型连通性
- GET  /api/script/schema         — 获取 YAML Schema 规范说明
- POST /api/script/validate       — 校验 YAML 内容是否符合 Schema
"""

import json
import sys
import time
import asyncio

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import StreamingResponse

from backend.config import AIConfig
from backend.schemas.script_schema import (
    ConvertRequest,
    ConvertResponse,
    ScriptYAML,
    ValidateRequest,
    ValidateResponse,
)
from backend.services.ai_parser_service import (
    JobCancelled,
    parse_novel_to_script,
)
from backend.services.job_store import (
    STATUS_COMPLETED,
    STATUS_RUNNING,
    compute_fingerprint,
    get_job_store,
)
from backend.services.text_preprocessor import preprocess_novel_text
from backend.services.yaml_renderer import render_script_yaml

router = APIRouter(prefix="/script", tags=["剧本转换"])


def _mask_api_key(api_key: str) -> str:
    """
    遮罩 API Key，仅保留前5个字符用于界面提示。

    Args:
        api_key: 完整 API Key

    Returns:
        str: 遮罩后的形式，如 "sk-T6..."；空 Key 返回空字符串
    """
    if not api_key:
        return ""
    return f"{api_key[:5]}..."


def _resolve_ai_params(
    api_key: str | None,
    base_url: str | None,
    model_name: str | None,
) -> tuple[str, str, str]:
    """
    将前端可选参数与环境变量默认值合并。

    优先级：前端传入值 > OPENAI_* 环境变量 > 空字符串。

    Args:
        api_key: 前端传入的 API Key（可为空）
        base_url: 前端传入的 API 地址（可为空）
        model_name: 前端传入的模型名称（可为空）

    Returns:
        tuple[str, str, str]: (api_key, base_url, model_name) 合并后的有效配置
    """
    default_config = AIConfig()
    return (
        api_key or default_config.api_key,
        base_url or default_config.base_url,
        model_name or default_config.model_name,
    )


@router.get("/config-status")
async def get_config_status():
    """
    查询服务器端 AI 配置状态。

    用于前端判断是否可以留空 AI 配置（使用服务器默认值）。
    安全性：绝不返回完整 API Key，仅返回前5个字符的遮罩形式。

    Returns:
        dict: 包含 configured/api_key_masked/base_url/model_name 的配置状态
    """
    config = AIConfig()
    configured = bool(config.api_key and config.base_url and config.model_name)
    return {
        "configured": configured,
        "api_key_masked": _mask_api_key(config.api_key),
        "base_url": config.base_url,
        "model_name": config.model_name,
    }


def log(msg: str) -> None:
    """
    立即刷新的日志输出函数。

    解决 uvicorn 运行时 stdout 缓冲导致 log() 不即时显示的问题。
    所有日志通过此函数输出，确保在终端中实时可见。
    """
    print(msg, flush=True)
    sys.stdout.flush()


@router.post("/convert", response_model=ConvertResponse)
async def convert_novel_to_script(
    novel_title: str = Form(..., description="小说名称"),
    novel_text: str = Form(default="", description="小说正文文本（与文件二选一）"),
    novel_file: UploadFile | None = File(None, description="小说文件（.txt）"),
    api_key: str | None = Form(None, description="可选：API Key"),
    base_url: str | None = Form(None, description="可选：API Base URL"),
    model_name: str | None = Form(None, description="可选：模型名称"),
):
    """
    核心转换接口：将小说文本转换为结构化 YAML 剧本。

    支持两种输入方式（二选一）：
    - 直接粘贴小说正文文本（novel_text 字段）
    - 上传 .txt 文件（novel_file 字段）

    完整处理流程：
    1. 接收并读取输入文本
    2. 文本预处理（章节识别、内容清洗）
    3. AI 语义解析（调用大模型转换为剧本结构）
    4. Schema 校验与 YAML 渲染
    5. 返回结构化数据 + 纯 YAML 文本

    Args:
        novel_title: 小说/原著名称
        novel_text: 直接粘贴的文本内容
        novel_file: 上传的文本文件
        api_key: 可选自定义 API Key
        base_url: 可选自定义 API 地址
        model_name: 可选自定义模型名称

    Returns:
        ConvertResponse: 包含 success/data/yaml_text 的响应对象

    Raises:
        HTTPException 400: 输入参数无效时
        HTTPException 500: AI 解析或内部处理失败时
    """
    try:
        # 步骤1：获取原始文本（文件优先于文本字段）
        raw_text = ""
        if novel_file and novel_file.filename:
            content = await novel_file.read()
            raw_text = content.decode("utf-8", errors="ignore")
            log(f"[CONVERT] 收到文件上传: {novel_file.filename}, 大小: {len(content)} 字节")
        elif novel_text and novel_text.strip():
            raw_text = novel_text.strip()
            log(f"[CONVERT] 收到文本粘贴: {len(raw_text)} 字符")
        else:
            raise HTTPException(
                status_code=400,
                detail="请提供小说正文文本或上传 .txt 文件",
            )

        # 步骤2：文本预处理
        log(f"[CONVERT] 开始预处理，输入长度: {len(raw_text)} 字符")
        preprocess_result = preprocess_novel_text(raw_text)
        log(f"[CONVERT] 预处理完成: 章节范围={preprocess_result.chapter_range}, "
              f"输出长度={len(preprocess_result.clean_text)} 字符")

        # 步骤3：构建AI配置（使用前端传入值覆盖默认值）
        config = AIConfig(
            api_key=api_key or "",
            base_url=base_url or "",
            model_name=model_name or "",
        )
        log(f"[CONVERT] AI配置: model={config.model_name}, base_url={config.base_url}, "
              f"timeout={config.timeout}s")

        # 步骤4：AI解析转换
        start_time = time.time()
        script_data = parse_novel_to_script(
            novel_text=preprocess_result.clean_text,
            novel_title=novel_title,
            config=config,
        )
        elapsed = round(time.time() - start_time, 1)
        log(f"[CONVERT] AI解析完成! 耗时: {elapsed}s, 场景数: {len(script_data.script_scenes)}, "
              f"角色数: {len(script_data.global_characters)}")

        # 步骤5：更新元数据中的章节范围信息
        script_data.script_meta.chapter_range = preprocess_result.chapter_range

        # 步骤6：渲染 YAML 文本
        yaml_text = render_script_yaml(script_data)

        return ConvertResponse(
            success=True,
            message=f"成功转换，共生成 {len(script_data.script_scenes)} 场戏、"
                    f"{len(script_data.global_characters)} 个角色（耗时 {elapsed}s）",
            data=script_data,
            yaml_text=yaml_text,
        )

    except ValueError as e:
        log(f"[CONVERT] 参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        err_type = type(e).__name__
        err_str = str(e)
        log(f"[CONVERT] 异常({err_type}): {err_str[:500]}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误 [{err_type}]: {err_str[:300]}")


@router.post("/convert-stream")
async def convert_novel_to_script_stream(
    novel_title: str = Form(..., description="小说/原著名称"),
    novel_text: str = Form(default="", description="小说正文文本"),
    novel_file: UploadFile | None = File(None, description="上传的文本文件"),
    api_key: str = Form(default="", description="可选：自定义API Key"),
    base_url: str = Form(default="", description="可选：自定义API地址"),
    model_name: str = Form(default="", description="可选：自定义模型名称"),
    force: bool = Form(default=False, description="可选：忽略缓存结果强制重新转换"),
):
    """
    SSE 流式转换接口 — 实时推送解析进度（任务制）。

    任务在后台线程运行并实时落盘（job_store），即使客户端断线 /
    刷新页面 / 服务重启前的中断，已完成分片都不会丢失：
    - 防重复：相同指纹任务进行中时返回 duplicate 错误（含 job_id）
    - 缓存直返：相同指纹任务已完成且未指定 force 时，直接返回缓存结果
    - 断点续跑：相同指纹的历史失败/取消任务，已完成分片自动复用

    返回 text/event-stream 格式，事件类型：
      - progress: 进度更新（含 stage/message/data）
      - result:   转换完成（含完整 data 和 yaml_text 及 job_id）
      - error:    错误信息（含 code: duplicate 等）
    """
    import asyncio

    def _sse_event(event: str, data: dict) -> str:
        """构造 SSE 格式事件行"""
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def event_generator():
        """异步生成器，通过 asyncio.Queue 实时产出 SSE 事件"""
        store = get_job_store()
        job_id: str | None = None

        try:
            # ---- 步骤1：获取原始文本 ----
            raw_text = ""
            file_content = ""
            if novel_file and novel_file.filename:
                content = await novel_file.read()
                file_content = content.decode("utf-8", errors="ignore")
                raw_text = file_content
                log(f"[STREAM] 收到文件上传: {novel_file.filename}, 大小: {len(content)} 字节")
            elif novel_text and novel_text.strip():
                raw_text = novel_text.strip()
                log(f"[STREAM] 收到文本粘贴: {len(raw_text)} 字符")
            else:
                yield _sse_event("error", {"message": "请提供小说正文文本或上传文件"})
                return

            # ---- 步骤2：AI配置与文本指纹 ----
            config = AIConfig(
                api_key=api_key or "",
                base_url=base_url or "",
                model_name=model_name or "",
            )
            fingerprint = compute_fingerprint(raw_text, config.model_name, config.base_url)
            log(f"[STREAM] 文本指纹: {fingerprint[:16]}... model={config.model_name}")

            # ---- 防重复提交：相同指纹任务进行中时拒绝 ----
            running = store.find_running_job(fingerprint)
            if running:
                log(f"[STREAM] 检测到相同任务进行中: {running['job_id']}，拒绝重复提交")
                yield _sse_event("error", {
                    "code": "duplicate",
                    "job_id": running["job_id"],
                    "message": f"相同文本的转换任务正在进行中（{running['job_id']}），"
                               f"请等待其完成或取消后再试",
                })
                return

            # ---- 缓存直返：相同指纹已完成且未强制重跑 ----
            if not force:
                completed = store.find_resumable_job(fingerprint)
                if completed and completed.get("status") == STATUS_COMPLETED:
                    cached = store.load_result(completed["job_id"])
                    if cached:
                        log(f"[STREAM] 命中已完成任务缓存: {completed['job_id']}，直接返回")
                        yield _sse_event("result", cached)
                        return

            # ---- 断点续跑：从最近一次同指纹任务加载已完成分片 ----
            resume_chunks: dict[int, ScriptYAML] = {}
            resumable = store.find_resumable_job(fingerprint)
            if resumable:
                prev_job_id = resumable["job_id"]
                for idx in store.list_chunk_indices(prev_job_id):
                    yaml_text_prev = store.get_chunk_yaml(prev_job_id, idx)
                    if not yaml_text_prev:
                        continue
                    try:
                        resume_chunks[idx] = ScriptYAML.from_yaml(yaml_text_prev)
                    except Exception:
                        continue  # 历史分片损坏时丢弃，重新解析该分片
                if resume_chunks:
                    log(f"[STREAM] 断点续跑: 复用任务 {prev_job_id} 的 "
                        f"{len(resume_chunks)} 个已完成分片")

            # ---- 步骤3：创建任务并持久化 ----
            job = store.create_job(
                novel_title=novel_title,
                novel_text=novel_text,
                novel_file_content=file_content,
                api_key=config.api_key,
                base_url=config.base_url,
                model_name=config.model_name,
                fingerprint=fingerprint,
            )
            job_id = job["job_id"]
            log(f"[STREAM] 任务已创建: {job_id}")

            # 使用 asyncio.Queue 实现线程→协程的高效事件传递
            event_queue: asyncio.Queue[dict | None] = asyncio.Queue()

            def on_progress(event_type: str, data: dict) -> None:
                """
                AI 解析服务的进度回调。
                通过 put_nowait 将事件推入异步队列（非阻塞），同时写入任务日志。
                """
                stage_map = {
                    "start": ("parsing", f"开始AI解析... (文本长度: {data.get('text_length', '?')} 字)"),
                    "parsing_single": ("calling_llm", "正在调用 AI 模型进行单次解析..."),
                    "parsing_chunks": ("parsing_chunks", f"进入分片模式（{data.get('text_length', '?')} 字符）"),
                    "extracting_chars": ("extracting_chars", "正在预提取人物信息..."),
                    "chars_extracted": ("chars_extracted",
                                        f"人物提取完成，共 {data.get('char_count', 0)} 个角色"),
                    "chunking": ("chunking", "正在切割文本为分片..."),
                    "chunks_ready": ("chunks_ready",
                                     f"文本已切割为 {data.get('total', 0)} 个分片"),
                    "chunk_wait": ("waiting",
                                    f"等待速率限制冷却 ({data.get('wait_seconds', 2)}s)..."),
                    "chunk_start": ("chunk_start",
                                    f"正在解析第 {data.get('index', '?')}/{data.get('total', '?')} 片..."),
                    "chunk_done": ("chunk_done",
                                   f"第 {data.get('index', '?')}/{data.get('total', '?')} 片解析完成 "
                                   f"(+{data.get('scenes', 0)} 场戏)"),
                    "chunk_resumed": ("chunk_resumed",
                                      f"第 {data.get('index', '?')}/{data.get('total', '?')} 片复用历史结果 "
                                      f"(+{data.get('scenes', 0)} 场戏)"),
                    "chunk_fail": ("chunk_fail",
                                   f"第 {data.get('index', '?')}/{data.get('total', '?')} 片解析失败，跳过"),
                    "merging": ("merging",
                                f"正在合并 {data.get('completed_chunks', 0)}/{data.get('total_chunks', 0)} 个分片结果..."),
                    "refining_psy": ("refining_psy", "正在进行心理占比巡检与精简..."),
                    "done": ("done", "解析完成!"),
                    "error": ("error", data.get("message", "未知错误")),
                    # === 流式输出事件（LLM 返回内容实时推送）===
                    "stream_start": ("streaming", "[流式] 等待模型响应..."),
                    "stream_chunk": ("stream_chunk", data.get("text", "")),
                    "stream_done": ("stream_done",
                                     f"[流式完成] 响应体={data.get('response_length', '?')}B"
                                     f" | tokens={data.get('total_tokens', 'N/A')}"),
                }
                stage, msg = stage_map.get(event_type, ("unknown", str(data)))

                # 关键进度事件写入任务日志（断线重连后可见；流式chunk不记录避免刷盘）
                if event_type not in ("stream_chunk",):
                    try:
                        store.append_log(job_id, stage, msg)
                    except Exception:
                        pass

                # 分片切割完成时记录总数（前端轮询进度条需要）
                if event_type == "chunks_ready":
                    try:
                        store.set_total_chunks(job_id, int(data.get("total", 0)))
                    except Exception:
                        pass

                try:
                    event_queue.put_nowait({
                        "stage": stage,
                        "message": msg,
                        "data": data,
                        "event_type": event_type,
                    })
                except Exception:
                    pass

            def chunk_sink(index: int, yaml_text: str | None = None, failed: bool = False) -> None:
                """分片结果实时落盘 / 记录失败分片（断点续跑数据源）"""
                if failed:
                    store.mark_chunk_failed(job_id, index)
                elif yaml_text:
                    store.save_chunk(job_id, index, yaml_text)

            def cancel_check() -> bool:
                """分片间协作式取消检查"""
                return store.is_cancel_requested(job_id)

            # 发送初始进度（携带 job_id 供前端断线重连）
            yield _sse_event("progress", {
                "stage": "preprocessing",
                "message": f"正在预处理文本（{len(raw_text)} 字符）...",
                "data": {"text_length": len(raw_text), "job_id": job_id,
                         "resumed_chunks": len(resume_chunks)},
            })

            # ---- 步骤4：文本预处理 ----
            log(f"[STREAM] 开始预处理，输入长度: {len(raw_text)} 字符")
            preprocess_result = preprocess_novel_text(raw_text)
            log(f"[STREAM] 预处理完成: 章节范围={preprocess_result.chapter_range}")
            yield _sse_event("progress", {
                "stage": "preprocessed",
                "message": f"预处理完成，章节范围: {preprocess_result.chapter_range}",
                "data": {
                    "chapter_range": preprocess_result.chapter_range,
                    "output_length": len(preprocess_result.clean_text),
                    "job_id": job_id,
                },
            })

            # ---- 步骤5：在线程池中运行同步 AI 解析 ----
            final_result: list[dict | None] = [None]
            final_error: list[dict | None] = [None]
            loop = asyncio.get_event_loop()

            def run_parse():
                """在独立线程中运行同步 AI 解析（结果实时落盘）"""
                try:
                    script_data = parse_novel_to_script(
                        novel_text=preprocess_result.clean_text,
                        novel_title=novel_title,
                        config=config,
                        progress_callback=on_progress,
                        chunk_sink=chunk_sink,
                        resume_chunks=resume_chunks or None,
                        cancel_check=cancel_check,
                    )
                    script_data.script_meta.chapter_range = preprocess_result.chapter_range
                    yaml_text = render_script_yaml(script_data)
                    result_payload = {
                        "job_id": job_id,
                        "scenes": len(script_data.script_scenes),
                        "characters": len(script_data.global_characters),
                        "script_data": script_data.model_dump(mode="python"),
                        "yaml_text": yaml_text,
                        "message": f"成功转换，共生成 {len(script_data.script_scenes)} 场戏、"
                                   f"{len(script_data.global_characters)} 个角色",
                    }
                    # 完整结果落盘（预览页可从后端读取）
                    store.finalize_result(job_id, result_payload, yaml_text)
                    final_result[0] = result_payload
                except JobCancelled:
                    store.mark_cancelled(job_id)
                    final_error[0] = {"type": "JobCancelled", "message": "任务已取消", "cancelled": True}
                    try:
                        event_queue.put_nowait({
                            "stage": "cancelled",
                            "message": "任务已取消",
                            "data": {"job_id": job_id},
                            "event_type": "cancelled",
                        })
                    except Exception:
                        pass
                except Exception as e:
                    store.mark_failed(job_id, f"[{type(e).__name__}] {str(e)}")
                    final_error[0] = {"type": type(e).__name__, "message": str(e)[:500]}
                    try:
                        event_queue.put_nowait({
                            "stage": "error",
                            "message": f"解析异常: [{type(e).__name__}] {str(e)[:200]}",
                            "data": {"type": type(e).__name__, "message": str(e)[:300],
                                     "job_id": job_id},
                        })
                    except Exception:
                        pass

            # 启动后台线程执行解析（客户端断线后线程继续运行，结果已落盘）
            parse_task = loop.run_in_executor(None, run_parse)

            # 从队列读取事件并推送给客户端（实时、低延迟）
            last_heartbeat = time.time()
            while True:
                try:
                    # 短超时等待队列事件（150ms 轮询间隔）
                    evt = await asyncio.wait_for(event_queue.get(), timeout=0.15)
                    if evt is None:
                        break
                    yield _sse_event("progress", evt)
                    last_heartbeat = time.time()
                except asyncio.TimeoutError:
                    # 队列为空，检查任务是否完成
                    if parse_task.done():
                        # 任务完成，排空剩余事件
                        remaining = []
                        while not event_queue.empty():
                            try:
                                item = event_queue.get_nowait()
                                if item is not None:
                                    remaining.append(item)
                            except asyncio.QueueEmpty:
                                break
                        for evt in remaining:
                            yield _sse_event("progress", evt)
                        break

                    # 心跳：每 5s 发一次 keepalive（比之前 15s 更频繁）
                    if time.time() - last_heartbeat > 5:
                        yield _sse_event("heartbeat", {"job_id": job_id})
                        last_heartbeat = time.time()

            # 等待任务完成确保无遗漏
            await parse_task

            # 发送最终结果或错误
            if final_error[0]:
                yield _sse_event("error", final_error[0])
            elif final_result[0]:
                yield _sse_event("result", final_result[0])
            else:
                yield _sse_event("error", {"message": "未获取到解析结果"})

        except Exception as e:
            err_type = type(e).__name__
            log(f"[STREAM] 异常({err_type}): {str(e)[:500]}")
            # 任务已在后台线程负责标记状态；此处仅向前端报告
            yield _sse_event("error", {
                "type": err_type,
                "message": f"服务器内部错误: {str(e)[:300]}",
                "job_id": job_id,
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# 任务查询与管理接口
# ============================================================


def _job_meta_response(meta: dict, include_result: bool = False) -> dict:
    """
    组装任务 meta 的对外响应。

    Args:
        meta: job_store 的 meta dict
        include_result: 是否附带已完成任务的完整结果

    Returns:
        dict: 对外响应（脱敏：不含 api_key）
    """
    resp = {
        "job_id": meta.get("job_id"),
        "status": meta.get("status"),
        "novel_title": meta.get("novel_title"),
        "model_name": meta.get("model_name"),
        "created_at": meta.get("created_at"),
        "updated_at": meta.get("updated_at"),
        "total_chunks": meta.get("total_chunks", 0),
        "completed_chunks": meta.get("completed_chunks", 0),
        "failed_chunks": meta.get("failed_chunks", []),
        "resumed_chunks": meta.get("resumed_chunks", []),
        "error": meta.get("error"),
        "message": meta.get("message", ""),
        "logs": meta.get("logs", []),
    }
    if include_result:
        result = get_job_store().load_result(meta.get("job_id", ""))
        resp["result"] = result
    return resp


@router.get("/jobs")
async def list_jobs():
    """列出最近的转换任务（按创建时间倒序，最多20条，不含结果正文）"""
    return {"jobs": [_job_meta_response(m) for m in get_job_store().list_jobs(limit=20)]}


@router.get("/jobs/latest")
async def get_latest_job(include_result: bool = True):
    """
    获取最近一个任务的状态（可选附带结果）。

    Args:
        include_result: 任务已完成时是否附带完整结果（script_data + yaml_text）

    Returns:
        dict: 任务 meta（无任务时 jobs 为空）
    """
    meta = get_job_store().latest_job()
    if not meta:
        return {"job": None}
    return {"job": _job_meta_response(meta, include_result=include_result)}


@router.get("/jobs/{job_id}")
async def get_job_detail(job_id: str, include_result: bool = False):
    """
    查询单个任务详情（可选附带结果）。

    Raises:
        HTTPException 404: 任务不存在
    """
    meta = get_job_store().get_job(job_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")
    return {"job": _job_meta_response(meta, include_result=include_result)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    请求取消任务（协作式：解析线程在分片间检查取消标记）。

    Raises:
        HTTPException 404: 任务不存在
        HTTPException 409: 任务已结束（非 running 状态）
    """
    ok = get_job_store().request_cancel(job_id)
    if not ok:
        meta = get_job_store().get_job(job_id)
        if not meta:
            raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")
        raise HTTPException(
            status_code=409,
            detail=f"任务 {job_id} 已结束（{meta.get('status')}），无需取消",
        )
    log(f"[STREAM] 任务取消请求已受理: {job_id}")
    return {"success": True, "message": f"任务 {job_id} 取消请求已受理，将在当前分片完成后停止"}


@router.post("/test-connection")
async def test_llm_connection(
    api_key: str = Form(default="", description="可选：API Key，留空使用服务器配置"),
    base_url: str = Form(default="", description="可选：API Base URL，留空使用服务器配置"),
    model_name: str = Form(default="", description="可选：模型名称，留空使用服务器配置"),
):
    """
    测试 LLM 模型接口连通性。

    发送一条最简请求到 AI 接口，验证：
    - API Key 是否有效
    - Base URL 是否可达
    - 模型名称是否被支持
    - 接口是否正常响应

    Args:
        api_key: API 密钥（留空时使用服务器 OPENAI_API_KEY 环境变量）
        base_url: API 地址（留空时使用服务器 OPENAI_BASE_URL 环境变量）
        model_name: 模型名称（留空时使用服务器 OPENAI_MODEL_NAME 环境变量）

    Returns:
        dict: 包含 success/message/latency/model 的测试结果
    """
    # 合并服务器默认配置；三项均缺失时直接拒绝（避免被下方异常处理器吞掉）
    api_key, base_url, model_name = _resolve_ai_params(api_key, base_url, model_name)
    if not api_key or not base_url or not model_name:
        log("[TEST] 服务器未配置 API 且前端未填写，拒绝测试")
        raise HTTPException(
            status_code=400,
            detail="服务器未配置 API（缺少 OPENAI_* 环境变量），请填写完整的 AI 配置",
        )

    from openai import (
        OpenAI,
        AuthenticationError,
        NotFoundError,
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        APIStatusError,
    )

    try:
        # 测试连接给 30 秒超时，比正式转换更宽松
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=30)
        start_time = time.time()

        log(f"[TEST] 开始测试连接: base_url={base_url}, model={model_name}")

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": "Hi, reply with only: OK"},
            ],
            max_tokens=5,
            temperature=0,
        )

        latency_ms = round((time.time() - start_time) * 1000, 0)

        # 安全解析响应，兼容不同平台的返回格式差异
        content = ""
        try:
            if response.choices and len(response.choices) > 0:
                msg = response.choices[0].message
                if msg:
                    content = (msg.content or "").strip()
            if not content:
                content = "(空回复)"
        except Exception as parse_err:
            log(f"[TEST] 响应解析警告: {parse_err}")
            content = f"(解析异常: {str(parse_err)[:50]})"

        log(f"[TEST] 连接成功: model={model_name}, latency={latency_ms}ms, reply={content[:30]}")

        return {
            "success": True,
            "message": "连接成功",
            "latency_ms": latency_ms,
            "model": model_name,
            "reply_preview": content[:50],
        }

    except AuthenticationError as e:
        err_msg = f"认证失败: API Key 无效 - {str(e)[:100]}"
        log(f"[TEST] {err_msg}")
        raise HTTPException(status_code=401, detail=err_msg)

    except NotFoundError as e:
        err_msg = f"模型不支持: {model_name} 不存在于此平台 - {str(e)[:150]}"
        log(f"[TEST] {err_msg}")
        raise HTTPException(status_code=400, detail=err_msg)

    except APITimeoutError as e:
        err_msg = f"请求超时(>30s): {base_url} 响应过慢，请检查网络或更换区域 - {str(e)[:100]}"
        log(f"[TEST] {err_msg}")
        raise HTTPException(status_code=504, detail=err_msg)

    except APIConnectionError as e:
        err_msg = f"无法连接: 无法访问 {base_url}，请检查地址是否正确 - {str(e)[:150]}"
        log(f"[TEST] {err_msg}")
        raise HTTPException(status_code=502, detail=err_msg)

    except RateLimitError as e:
        err_msg = f"频率限制: 请求过于频繁，请稍后再试 - {str(e)[:150]}"
        log(f"[TEST] {err_msg}")
        raise HTTPException(status_code=429, detail=err_msg)

    except APIStatusError as e:
        # 处理其他 HTTP 错误（400/500 等），提取详细原因
        status = e.status_code
        err_body = ""
        if hasattr(e, 'body') and e.body:
            try:
                import json
                if isinstance(e.body, dict):
                    err_body = json.dumps(e.body, ensure_ascii=False)[:200]
                else:
                    err_body = str(e.body)[:200]
            except Exception:
                err_body = str(e.body)[:200]

        # 特殊处理：模型不支持的错误可能在 400 中以 body 形式返回
        if status == 400 and ("model" in str(e).lower() or "Unsupported" in str(e) or "invalid_parameter" in str(e)):
            err_msg = f"模型不支持: {model_name} 不存在于此平台 - {err_body or str(e)[:200]}"
        elif status == 400:
            err_msg = f"请求参数错误 - {err_body or str(e)[:200]}"
        else:
            err_msg = f"API 返回错误(HTTP {status}) - {err_body or str(e)[:200]}"

        log(f"[TEST] {err_msg}")
        raise HTTPException(status_code=status, detail=err_msg)

    except Exception as e:
        err_str = str(e)
        log(f"[TEST] 未预期异常 ({type(e).__name__}): {err_str[:300]}")
        raise HTTPException(status_code=500, detail=f"未知错误({type(e).__name__}): {err_str[:200]}")


@router.get("/schema")
async def get_schema_info():
    """
    获取 YAML Schema 规范说明文档。

    返回项目定义的完整剧本 YAML Schema 信息，
    包括字段定义、类型约束、设计原因等。

    Returns:
        dict: Schema 规范说明的结构化数据
    """
    return {
        "schema_name": "Novel2Script-AI 剧本 YAML Schema",
        "version": "1.0",
        "description": "小说改编影视剧本通用结构化规范",
        "top_level_fields": {
            "script_meta": {
                "type": "object",
                "required": True,
                "description": "剧本全局元数据",
                "fields": {
                    "script_title": {"type": "string", "desc": "剧本名称"},
                    "original_novel_title": {"type": "string", "desc": "原著小说名"},
                    "chapter_range": {"type": "string", "desc": "转换章节范围"},
                    "create_time": {"type": "string", "desc": "生成时间"},
                    "script_type": {"type": "string", "desc": "剧本类型：短剧/长剧/电影"},
                    "version": {"type": "string", "desc": "版本号"},
                },
            },
            "script_scenes": {
                "type": "array[object]",
                "required": True,
                "description": "剧本场次列表（多场景有序排列）",
            },
            "global_characters": {
                "type": "array[object]",
                "required": True,
                "description": "全局人物库（整剧统一）",
            },
            "adapt_rule_note": {
                "type": "string",
                "required": True,
                "description": "本次AI改编规则说明",
            },
        },
        "unit_types": ["action", "dialogue", "narration", "psy"],
        "scene_types": ["内景", "外景"],
        "time_types": ["日", "夜", "黄昏", "凌晨"],
    }


@router.post("/validate", response_model=ValidateResponse)
async def validate_yaml_content(request: ValidateRequest):
    """
    校验 YAML 内容是否符合剧本 Schema 规范。

    用于前端实时校验用户编辑后的 YAML 内容是否合法，
    或验证外部导入的 YAML 文件格式是否正确。

    Args:
        request: 包含 yaml_text 字段的请求体

    Returns:
        ValidateResponse: 包含 valid/message/errors 的校验结果
    """
    errors = []

    try:
        from backend.schemas.script_schema import ScriptYAML

        script = ScriptYAML.from_yaml(request.yaml_text)
        return ValidateResponse(
            valid=True,
            message=f"校验通过：共 {len(script.script_scenes)} 场戏、"
                     f"{len(script.global_characters)} 个角色",
            errors=None,
        )
    except Exception as e:
        error_msg = str(e)
        # 提取关键错误信息
        if "Validation" in type(e).__name__:
            # Pydantic 校验错误，提取字段级错误详情
            if hasattr(e, "errors"):
                for err in e.errors():
                    loc = " -> ".join(str(l) for l in err.get("loc", []))
                    errors.append(f"[{loc}] {err.get('msg', '未知错误')}")
            else:
                errors.append(error_msg)
        else:
            errors.append(error_msg)

        return ValidateResponse(
            valid=False,
            message="YAML 格式不符合 Schema 规范",
            errors=errors,
        )
