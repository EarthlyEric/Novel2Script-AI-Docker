"""
剧本 YAML Schema 模型定义模块

基于项目设计文档定义的标准化剧本YAML规范，使用Pydantic v2实现数据校验、
序列化/反序列化、YAML格式转换等核心功能。

模型层级关系：
    ScriptYAML (根)
    ├── ScriptMeta (全局元数据)
    ├── ScriptScene[] (场次列表)
    │   ├── SceneAttr (场景属性)
    │   └── SceneContentUnit[] (剧情单元列表)
    ├── GlobalCharacter[] (全局人物库)
    └── adapt_rule_note (改编规则说明)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class ScriptMeta(BaseModel):
    """
    剧本全局元数据模型，记录剧本的基本溯源信息和版本管理字段。

    Attributes:
        script_title: 剧本名称，通常由原著名称衍生
        original_novel_title: 原著小说原始标题
        chapter_range: 转换章节范围描述（如"第1-5章"）
        create_time: 剧本生成时间戳，ISO 8601格式
        script_type: 剧本类型分类：短剧/长剧/电影
        version: 剧本版本号，用于迭代管理

    Note:
        所有字段均为必填，create_time 默认使用当前时间
    """

    script_title: str = Field(..., description="剧本名称")
    original_novel_title: str = Field(..., description="原著小说名")
    chapter_range: str = Field(..., description="转换章节范围（如：第1-5章）")
    create_time: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="生成时间",
    )
    script_type: str = Field(default="短剧", description="剧本类型：短剧/长剧/电影")
    version: str = Field(default="v1.0", description="版本号")


class SceneAttr(BaseModel):
    """
    场景时空属性模型，定义单场戏的基础拍摄属性。

    Attributes:
        location: 场景地点描述（如"城南老街茶馆"）
        scene_type: 场景类型分类：内景(INT) / 外景(EXT)
        time_type: 时间段分类：日/夜/黄昏/凌晨

    Note:
        字段值需符合影视剧本行业标准术语
    """

    location: str = Field(..., description="场景地点")
    scene_type: str = Field(..., description="场景类型：内景/外景")
    time_type: str = Field(..., description="时间：日/夜/黄昏/凌晨")

    @field_validator("scene_type")
    @classmethod
    def validate_scene_type(cls, v: str) -> str:
        """
        校验场景类型是否为合法值。
        对于不在枚举范围内的值，尝试模糊匹配到最接近的合法值。

        Args:
            v: 待校验的场景类型字符串

        Returns:
            str: 校验通过后的场景类型值

        Raises:
            ValueError: 场景类型不在允许范围内且无法匹配时抛出
        """
        allowed = {"内景", "外景", "INT", "EXT"}
        if v in allowed:
            return v

        # 模糊匹配
        fuzzy_map = {
            "int": "INT", "内": "内景", "室内": "内景",
            "ext": "EXT", "外": "外景", "室外": "外景",
            "inside": "INT", "interior": "INT",
            "outside": "EXT", "exterior": "EXT",
        }
        v_lower = v.strip().lower()
        if v_lower in fuzzy_map:
            return fuzzy_map[v_lower]

        # 关键词包含匹配
        for keyword, target in [("内", "内景"), ("INT", "INT"), ("int", "INT"),
                                 ("外", "外景"), ("EXT", "EXT"), ("ext", "EXT")]:
            if keyword in v:
                return target

        raise ValueError(f"scene_type 必须为 {allowed} 之一（已尝试模糊匹配），当前值: {v}")

    @field_validator("time_type")
    @classmethod
    def validate_time_type(cls, v: str) -> str:
        """
        校验时间段是否为合法值。
        对于不在枚举范围内的值，尝试模糊匹配到最接近的合法值。

        Args:
            v: 待校验的时间类型字符串

        Returns:
            str: 校验通过后的时间类型值

        Raises:
            ValueError: 无法匹配任何合法时间段时抛出
        """
        allowed = {"日", "夜", "黄昏", "凌晨", "DAY", "NIGHT", "DUSK", "DAWN"}
        if v in allowed:
            return v

        # 模糊匹配：AI 可能返回组合词或近似表达，尝试自动修正
        fuzzy_map = {
            "凌晨至黎明": "凌晨",
            "黎明": "凌晨",
            "清晨": "日",
            "早晨": "日",
            "上午": "日",
            "中午": "日",
            "下午": "日",
            "傍晚": "黄昏",
            "傍晚至夜间": "黄昏",
            "晚间": "夜",
            "深夜": "夜",
            "午夜": "夜",
            "深夜至凌晨": "凌晨",
            "白天": "日",
            "黑夜": "夜",
            "白天至夜晚": "日",
            "dawn": "DAWN",
            "morning": "DAY",
            "afternoon": "DAY",
            "evening": "DUSK",
            "night": "NIGHT",
            "midnight": "NIGHT",
        }
        v_lower = v.strip()
        if v_lower in fuzzy_map:
            return fuzzy_map[v_lower]

        # 关键词包含匹配
        for keyword, target in [
            ("凌晨", "凌晨"), ("黎明", "凌晨"), ("DAWN", "DAWN"), ("dawn", "DAWN"),
            ("黄昏", "黄昏"), ("傍晚", "黄昏"), ("DUSK", "DUSK"), ("dusk", "DUSK"),
            ("夜", "夜"), ("夜晚", "夜"), ("NIGHT", "NIGHT"), ("night", "NIGHT"),
            ("日", "日"), ("白天", "日"), ("DAY", "DAY"), ("day", "DAY"),
        ]:
            if keyword in v_lower:
                return target

        raise ValueError(f"time_type 必须为 {allowed} 之一（已尝试模糊匹配），当前值: {v}")


class SceneContentUnit(BaseModel):
    """
    剧情单元模型，表示单场戏中最小的内容原子。

    每个单元代表一个独立的视听元素（动作/台词/旁白/心理），
    在同一场次内按剧情时间线严格有序排列。

    Attributes:
        unit_id: 单元唯一编号（本场内自增）
        unit_type: 单元类型分类：
                   - action: 人物肢体动作、神态、行为表现（可镜头拍摄）
                   - dialogue: 人物对话、口语表达
                   - narration: 剧情旁白、场景补充、过渡解说
                   - psy: 关键人物心理活动（仅保留核心剧情所需）
        character: 对应人物名称，无关联人物时为空字符串
        content: 具体内容文本

    Note:
        unit_type 决定了前端渲染样式和后续制片工具的处理方式
    """

    unit_id: int = Field(..., description="剧情单元ID")
    unit_type: str = Field(
        ...,
        description="单元类型：action(动作)/dialogue(台词)/narration(旁白)/psy(心理活动)",
    )
    character: str = Field(default="", description="对应人物（无则为空）")
    content: str = Field(..., description="具体内容")

    @field_validator("unit_type")
    @classmethod
    def validate_unit_type(cls, v: str) -> str:
        """
        校验单元类型是否为合法的四类之一。

        Args:
            v: 待校验的单元类型字符串

        Returns:
            str: 校验通过的单元类型值

        Raises:
            ValueError: 单元类型不在四种允许范围内时抛出
        """
        allowed = {"action", "dialogue", "narration", "psy"}
        if v not in allowed:
            raise ValueError(f"unit_type 必须为 {allowed} 之一，当前值: {v}")
        return v


class ScriptScene(BaseModel):
    """
    单场剧本模型，包含一场戏的全部结构化信息。

    一场戏由场景切换触发分割（地点/时间/人物阵容/剧情段落变化），
    是剧本结构化的基本组织单位。

    Attributes:
        scene_id: 全局唯一场次编号（自增整数）
        scene_serial: 场次标识符（如"S01"、"S02"），用于人工阅读和引用
        scene_attr: 场景基础属性（地点、内外景、时间）
        scene_summary: 本场剧情概要，一句话概括本场核心事件
        scene_content: 本场详细剧情单元列表，按时间线有序排列
        scene_note: 本场改编备注，记录AI优化说明和人工适配建议

    Note:
        scene_id 全局唯一，scene_serial 用于展示，两者一一对应
    """

    scene_id: int = Field(..., description="场次唯一编号（自增）")
    scene_serial: str = Field(..., description="场次标识（如：S01、S02）")
    scene_attr: SceneAttr = Field(..., description="场景基础属性")
    scene_summary: str = Field(..., description="本场剧情概要")
    scene_content: list[SceneContentUnit] = Field(
        default_factory=list, description="本场详细剧情单元（有序）"
    )
    scene_note: str = Field(default="", description="本场改编备注")


class GlobalCharacter(BaseModel):
    """
    全局人物库模型，统一管理整部剧本中出现的所有角色。

    通过集中式人物管理解决小说中别名、昵称、代称混乱问题，
    保证全剧本人物名称一致性和人设连贯性。

    Attributes:
        char_id: 人物唯一编号（全局自增）
        char_name: 人物标准名称（全剧统一使用的正式名称）
        char_profile: 人物简要人设描述，从小说原文提取的性格/身份/特征信息

    Note:
        同一人物在小说中可能有多个称呼（昵称、代称），此处统一为标准名
    """

    char_id: int = Field(..., description="人物编号")
    char_name: str = Field(..., description="人物名称")
    char_profile: str = Field(default="", description="人物简要人设（从小说提取）")


class ScriptYAML(BaseModel):
    """
    剧本 YAML 根模型，是整个 Schema 的顶层容器。

    包含完整的结构化剧本数据，支持序列化为标准 YAML 格式输出，
    也支持从 YAML 文本反序列化并进行数据校验。

    Attributes:
        script_meta: 剧本全局元数据（标题、章节范围、版本等）
        script_scenes: 核心场次列表，按剧情时间线有序排列
        global_characters: 全局人物库，整剧统一角色管理
        adapt_rule_note: 本次AI改编的规则说明和逻辑记录

    Example:
        >>> data = {
        ...     "script_meta": {"script_title": "测试剧本", ...},
        ...     "script_scenes": [...],
        ...     "global_characters": [...],
        ...     "adapt_rule_note": "基于原著改编"
        ... }
        >>> script = ScriptYAML(**data)
        >>> yaml_text = script.to_yaml()
    """

    script_meta: ScriptMeta = Field(..., description="剧本全局元数据")
    script_scenes: list[ScriptScene] = Field(
        default_factory=list, description="剧本场次列表（多场景有序排列）"
    )
    global_characters: list[GlobalCharacter] = Field(
        default_factory=list, description="全局人物库（整剧统一）"
    )
    adapt_rule_note: str = Field(default="", description="本次AI改编规则说明")

    def to_yaml(self) -> str:
        """
        将结构化剧本数据渲染为标准 YAML 格式字符串。

        使用自定义缩进和排序策略确保输出符合项目设计文档规范的
        可读性要求，生成的 YAML 可直接用于文件存储或前端展示。

        Returns:
            str: 格式化的 YAML 文本，字段完整、层级清晰、可读性强

        Note:
            输出的 YAML 为纯净文本，不含 markdown 标记或多余说明文字。
            空列表会输出为空数组 [] 而非省略。
        """
        import yaml

        data = self.model_dump(mode="python")
        return yaml.dump(
            data,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
            indent=2,
        )

    @classmethod
    def from_yaml(cls, yaml_text: str) -> ScriptYAML:
        """
        从 YAML 文本反序列化并校验为 ScriptYAML 实例。

        解析 YAML 字符串并通过 Pydantic 模型进行严格的数据校验，
        确保字段完整性、类型正确性和枚举值合法性。

        Args:
            yaml_text: 待解析的 YAML 格式文本字符串

        Returns:
            ScriptYAML: 校验通过的剧本实例，可直接用于业务逻辑处理

        Raises:
            yaml.YAMLError: YAML 格式语法错误时抛出
            pydantic.ValidationError: 数据不符合 Schema 定义时抛出

        Example:
            >>> with open("script.yaml") as f:
            ...     script = ScriptYAML.from_yaml(f.read())
        """
        import yaml

        data = yaml.safe_load(yaml_text)
        if not isinstance(data, dict):
            raise ValueError("YAML 根节点必须为对象（字典）类型")
        return cls.model_validate(data)


# ============================================================
# API 请求/响应模型（用于接口层）
# ============================================================



class ConvertRequest(BaseModel):
    """
    小说转剧本API请求模型。

    Attributes:
        novel_title: 小说/原著名称
        novel_text: 小说正文文本（多章节内容）
        api_key: 可选的自定义API Key（覆盖默认配置）
        base_url: 可选的自定义API Base URL
        model_name: 可选的自定义模型名称
    """

    model_config = ConfigDict(protected_namespaces=())

    novel_title: str = Field(..., description="小说名称")
    novel_text: str = Field(..., min_length=100, description="小说正文内容（至少100字）")
    api_key: Optional[str] = Field(None, description="可选：自定义API Key")
    base_url: Optional[str] = Field(None, description="可选：自定义API地址")
    model_name: Optional[str] = Field(None, description="可选：自定义模型名称")


class ConvertResponse(BaseModel):
    """
    小说转剧本API响应模型。

    Attributes:
        success: 操作是否成功
        message: 结果消息描述
        data: 结构化剧本数据（成功时有值）
        yaml_text: 纯 YAML 文本（成功时有值，用于直接下载）
    """

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="结果消息")
    data: Optional[ScriptYAML] = Field(None, description="结构化剧本数据")
    yaml_text: Optional[str] = Field(None, description="纯YAML文本")


class ValidateRequest(BaseModel):
    """
    YAML校验API请求模型。

    Attributes:
        yaml_text: 待校验的 YAML 文本内容
    """

    yaml_text: str = Field(..., description="待校验的YAML文本")


class ValidateResponse(BaseModel):
    """
    YAML校验API响应模型。

    Attributes:
        valid: 是否通过校验
        message: 校验结果详情
        errors: 校验失败时的错误信息列表
    """

    valid: bool = Field(..., description="是否通过校验")
    message: str = Field(..., description="校验结果详情")
    errors: Optional[list[str]] = Field(default=None, description="错误信息列表")
