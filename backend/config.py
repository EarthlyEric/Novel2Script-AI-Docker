"""
配置管理模块 - 管理AI模型参数、应用配置等

支持环境变量读取与默认值回退，用于控制AI解析服务的行为参数。
"""

import os


class AIConfig:
    """
    AI模型配置类，封装OpenAI兼容接口所需的全部连接参数。

    Attributes:
        base_url (str): OpenAI兼容API的基础URL，默认为OpenAI官方地址
        api_key (str): API密钥，用于身份认证
        model_name (str): 使用的模型名称，默认gpt-4o-mini
        temperature (float): 生成温度参数，值越低输出越确定性
        max_tokens (int): 最大生成token数限制
        timeout (int): API请求超时时间（秒）
    """

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str = "",
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 16384,
        timeout: int = 300,
    ):
        """
        初始化AI配置，优先使用传入参数，否则从环境变量读取，最后使用默认值。

        Args:
            base_url: API基础地址
            api_key: API密钥
            model_name: 模型名称
            temperature: 生成温度（0-2之间）
            max_tokens: 最大token数
            timeout: 请求超时秒数
        """
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model_name = model_name or os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout


class AppConfig:
    """
    应用全局配置类，管理非AI相关的应用级参数。

    Attributes:
        cors_origins (list[str]): 允许的跨域来源列表
        upload_max_size (MB): 上传文件最大大小限制
        max_chapters (int): 支持的最大章节数
    """

    CORS_ORIGINS = ["*"]
    UPLOAD_MAX_SIZE_MB = 10
    MAX_CHAPTERS = 100
