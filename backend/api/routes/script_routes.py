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

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import StreamingResponse

from backend.config import AIConfig
from backend.schemas.script_schema import (
    ConvertRequest,
    ConvertResponse,
    ValidateRequest,
    ValidateResponse,
)
from backend.services.ai_parser_service import parse_novel_to_script
from backend.services.text_preprocessor import preprocess_novel_text
from backend.services.yaml_renderer import render_script_yaml

router = APIRouter(prefix="/script", tags=["剧本转换"])


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
):
    """
    SSE 流式转换接口 — 实时推送解析进度。

    返回 text/event-stream 格式，前端可通过 fetch ReadableStream 或 EventSource 接收。
    事件类型：
      - progress: 进度更新（含 stage/message/data）
      - result:   转换完成（含完整 data 和 yaml_text）
      - error:    错误信息
    """
    import asyncio

    def _sse_event(event: str, data: dict) -> str:
        """构造 SSE 格式事件行"""
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def event_generator():
        """异步生成器，逐步产出 SSE 事件"""
        try:
            # ---- 步骤1：获取原始文本 ----
            raw_text = ""
            if novel_file and novel_file.filename:
                content = await novel_file.read()
                raw_text = content.decode("utf-8", errors="ignore")
                log(f"[STREAM] 收到文件上传: {novel_file.filename}, 大小: {len(content)} 字节")
            elif novel_text and novel_text.strip():
                raw_text = novel_text.strip()
                log(f"[STREAM] 收到文本粘贴: {len(raw_text)} 字符")
            else:
                yield _sse_event("error", {"message": "请提供小说正文文本或上传文件"})
                return

            # 发送初始进度
            yield _sse_event("progress", {
                "stage": "preprocessing",
                "message": f"正在预处理文本（{len(raw_text)} 字符）...",
                "data": {"text_length": len(raw_text)},
            })

            # ---- 步骤2：文本预处理 ----
            log(f"[STREAM] 开始预处理，输入长度: {len(raw_text)} 字符")
            preprocess_result = preprocess_novel_text(raw_text)
            log(f"[STREAM] 预处理完成: 章节范围={preprocess_result.chapter_range}")
            yield _sse_event("progress", {
                "stage": "preprocessed",
                "message": f"预处理完成，章节范围: {preprocess_result.chapter_range}",
                "data": {
                    "chapter_range": preprocess_result.chapter_range,
                    "output_length": len(preprocess_result.clean_text),
                },
            })

            # ---- 步骤3：构建AI配置 ----
            config = AIConfig(
                api_key=api_key or "",
                base_url=base_url or "",
                model_name=model_name or "",
            )
            log(f"[STREAM] AI配置: model={config.model_name}")

            # ---- 步骤4：AI解析（带进度回调） ----
            final_result = [None]
            final_error = [None]

            def on_progress(event_type: str, data: dict) -> None:
                """
                AI 解析服务的进度回调。
                将同步回调转换为 async queue 消息供 event_generator 消费。
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
                    "chunk_fail": ("chunk_fail",
                                   f"第 {data.get('index', '?')}/{data.get('total', '?')} 片解析失败，跳过"),
                    "merging": ("merging",
                                f"正在合并 {data.get('completed_chunks', 0)}/{data.get('total_chunks', 0)} 个分片结果..."),
                    "refining_psy": ("refining_psy", "正在进行心理占比巡检与精简..."),
                    "done": ("done", "解析完成!"),
                    "error": ("error", data.get("message", "未知错误")),
                }
                stage, msg = stage_map.get(event_type, ("unknown", str(data)))
                # 将结果存入共享变量
                if event_type == "done":
                    final_result[0] = data
                elif event_type == "error":
                    final_error[0] = data

                # 使用线程安全的方式传递事件到异步生成器
                nonlocal _pending_events
                _pending_events.append({
                    "stage": stage,
                    "message": msg,
                    "data": data,
                })

            # 用于在线程和协程之间传递事件的列表
            _pending_events: list[dict] = []

            # 在线程池中运行同步的 AI 解析（避免阻塞事件循环）
            loop = asyncio.get_event_loop()

            def run_parse():
                try:
                    script_data = parse_novel_to_script(
                        novel_text=preprocess_result.clean_text,
                        novel_title=novel_title,
                        config=config,
                        progress_callback=on_progress,
                    )
                    # 更新章节范围
                    script_data.script_meta.chapter_range = preprocess_result.chapter_range
                    # 渲染 YAML
                    yaml_text = render_script_yaml(script_data)
                    final_result[0] = {
                        "scenes": len(script_data.script_scenes),
                        "characters": len(script_data.global_characters),
                        "script_data": script_data.model_dump(mode="python"),
                        "yaml_text": yaml_text,
                    }
                except Exception as e:
                    final_error[0] = {"type": type(e).__name__, "message": str(e)[:500]}
                    _pending_events.append({
                        "stage": "error",
                        "message": f"解析异常: [{type(e).__name__}] {str(e)[:200]}",
                        "data": {"type": type(e).__name__, "message": str(e)[:300]},
                    })

            # 启动后台任务
            parse_task = loop.run_in_executor(None, run_parse)

            # 轮询 pending_events 并发送给客户端
            last_tick = time.time()
            while not parse_task.done() or _pending_events:
                if _pending_events:
                    evt = _pending_events.pop(0)
                    yield _sse_event("progress", evt)
                    last_tick = time.time()

                if parse_task.done():
                    # 任务完成，发送剩余事件
                    while _pending_events:
                        evt = _pending_events.pop(0)
                        yield _sse_event("progress", evt)
                    break

                # 每 0.5s 轮询一次，避免忙等待
                await asyncio.sleep(0.5)

                # 心跳：每 15s 发一次 keepalive 防止超时
                if time.time() - last_tick > 15:
                    yield _sse_event("heartbeat", {})
                    last_tick = time.time()

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
            yield _sse_event("error", {
                "type": err_type,
                "message": f"服务器内部错误: {str(e)[:300]}",
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


@router.post("/test-connection")
async def test_llm_connection(
    api_key: str = Form(..., description="API Key"),
    base_url: str = Form(..., description="API Base URL"),
    model_name: str = Form(..., description="模型名称"),
):
    """
    测试 LLM 模型接口连通性。

    发送一条最简请求到 AI 接口，验证：
    - API Key 是否有效
    - Base URL 是否可达
    - 模型名称是否被支持
    - 接口是否正常响应

    Args:
        api_key: API 密钥
        base_url: API 地址
        model_name: 模型名称

    Returns:
        dict: 包含 success/message/latency/model 的测试结果
    """
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
