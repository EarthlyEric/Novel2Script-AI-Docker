"""
YAML 渲染输出服务模块

负责将 AI 解析生成的结构化剧本数据（ScriptYAML）渲染为标准 YAML 格式，
确保输出的 YAML 文本字段完整、格式规范、可直接下载和二次编辑。
"""

from backend.schemas.script_schema import ScriptYAML


def render_script_yaml(script_data: ScriptYAML) -> str:
    """
    将结构化剧本数据渲染为标准 YAML 格式字符串。

    该函数是对 ScriptYAML.to_yaml() 的封装，提供统一的渲染入口，
    并在渲染前进行必要的数据完整性检查。

    Args:
        script_data: 已填充数据的 ScriptYAML 实例

    Returns:
        str: 格式化的标准 YAML 文本，具有以下特征：
             - 使用中文友好编码（allow_unicode=True）
             - 不使用流式语法（default_flow_style=False），保证可读性
             - 保持字段定义顺序（sort_keys=False），与 Schema 一致
             - 行宽限制120字符（width=120）

    Raises:
        ValueError: script_data 为 None 时抛出

    Note:
        输出的 YAML 可直接用于：
        1. 前端展示和预览
        2. 文件下载（.yaml 格式）
        3. 二次编辑后重新解析入库
        4. 导入制片系统或其它工具链

    Example:
        >>> from backend.schemas.script_schema import ScriptYAML, ScriptMeta
        >>> meta = ScriptMeta(script_title="测试", original_novel_title="原著", ...)
        >>> script = ScriptYAML(script_meta=meta, ...)
        >>> yaml_text = render_script_yaml(script)
        >>> print(yaml_text)  # 输出标准YAML文本
    """
    if script_data is None:
        raise ValueError("剧本数据不能为 None")

    return script_data.to_yaml()
