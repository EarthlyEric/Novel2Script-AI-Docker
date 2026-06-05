"""
剧本转换 API 路由模块

提供小说转剧本的核心 HTTP 接口，包括：
- POST /api/script/convert   — 小说文本转换为结构化YAML剧本
- GET  /api/script/schema    — 获取 YAML Schema 规范说明
- POST /api/script/validate  — 校验 YAML 内容是否符合 Schema
"""

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

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
        elif novel_text and novel_text.strip():
            raw_text = novel_text.strip()
        else:
            raise HTTPException(
                status_code=400,
                detail="请提供小说正文文本或上传 .txt 文件",
            )

        # 步骤2：文本预处理
        preprocess_result = preprocess_novel_text(raw_text)

        # 步骤3：构建AI配置（使用前端传入值覆盖默认值）
        config = AIConfig(
            api_key=api_key or "",
            base_url=base_url or "",
            model_name=model_name or "",
        )

        # 步骤4：AI解析转换
        script_data = parse_novel_to_script(
            novel_text=preprocess_result.clean_text,
            novel_title=novel_title,
            config=config,
        )

        # 步骤5：更新元数据中的章节范围信息
        script_data.script_meta.chapter_range = preprocess_result.chapter_range

        # 步骤6：渲染 YAML 文本
        yaml_text = render_script_yaml(script_data)

        return ConvertResponse(
            success=True,
            message=f"成功转换，共生成 {len(script_data.script_scenes)} 场戏、"
                    f"{len(script_data.global_characters)} 个角色",
            data=script_data,
            yaml_text=yaml_text,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


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
