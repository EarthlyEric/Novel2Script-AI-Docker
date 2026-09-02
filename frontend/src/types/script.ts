/**
 * 剧本数据类型定义模块
 *
 * 与后端 Pydantic Schema 模型一一对应的 TypeScript 接口定义，
 * 用于前端数据的类型约束和 IDE 智能提示。
 */

/** 剧本全局元数据 */
export interface ScriptMeta {
  /** 剧本名称 */
  script_title: string
  /** 原著小说名 */
  original_novel_title: string
  /** 转换章节范围（如：第1-5章） */
  chapter_range: string
  /** 生成时间 */
  create_time: string
  /** 剧本类型：短剧/长剧/电影 */
  script_type: string
  /** 版本号 */
  version: string
}

/** 场景时空属性 */
export interface SceneAttr {
  /** 场景地点 */
  location: string
  /** 场景类型：内景/外景 */
  scene_type: string
  /** 时间：日/夜/黄昏/凌晨 */
  time_type: string
}

/** 剧情单元 - 单场戏中最小的内容原子 */
export interface SceneContentUnit {
  /** 剧情单元ID */
  unit_id: number
  /**
   * 单元类型：
   * - action: 动作（人物肢体动作、神态、行为表现）
   * - dialogue: 台词（人物对话、口语表达）
   * - narration: 旁白（剧情旁白、场景补充、过渡解说）
   * - psy: 心理活动（关键人物心理活动）
   */
  unit_type: 'action' | 'dialogue' | 'narration' | 'psy'
  /** 对应人物名称（无则为空字符串） */
  character: string
  /** 具体内容文本 */
  content: string
}

/** 单场剧本 */
export interface ScriptScene {
  /** 全局唯一场次编号（自增） */
  scene_id: number
  /** 场次标识（如：S01、S02） */
  scene_serial: string
  /** 场景基础属性 */
  scene_attr: SceneAttr
  /** 本场剧情概要 */
  scene_summary: string
  /** 本场详细剧情单元列表（有序） */
  scene_content: SceneContentUnit[]
  /** 本场改编备注 */
  scene_note: string
}

/** 全局人物库角色 */
export interface GlobalCharacter {
  /** 人物编号 */
  char_id: number
  /** 人物标准名称 */
  char_name: string
  /** 人物简要人设 */
  char_profile: string
}

/** 剧本 YAML 根数据结构 */
export interface ScriptYAML {
  /** 剧本全局元数据 */
  script_meta: ScriptMeta
  /** 剧本场次列表（多场景有序排列） */
  script_scenes: ScriptScene[]
  /** 全局人物库（整剧统一） */
  global_characters: GlobalCharacter[]
  /** 本次AI改编规则说明 */
  adapt_rule_note: string
}

/** 转换API请求参数 */
export interface ConvertParams {
  /** 小说名称 */
  novel_title: string
  /** 小说正文文本 */
  novel_text: string
  /** 可选：自定义API Key */
  api_key?: string
  /** 可选：自定义API Base URL */
  base_url?: string
  /** 可选：自定义模型名称 */
  model_name?: string
}

/** 转换API响应数据 */
export interface ConvertResult {
  /** 操作是否成功 */
  success: boolean
  /** 结果消息 */
  message: string
  /** 结构化剧本数据 */
  data: ScriptYAML | null
  /** 纯YAML文本 */
  yaml_text: string | null
}

/** YAML校验响应数据 */
export interface ValidateResult {
  /** 是否通过校验 */
  valid: boolean
  /** 校验结果详情 */
  message: string
  /** 错误信息列表 */
  errors: string[] | null
}

/** 服务器端 AI 配置状态 */
export interface ConfigStatus {
  /** 服务器是否已配置完整的 AI 连接信息 */
  configured: boolean
  /** 遮罩后的 API Key（如 "sk-T6..."，未配置为空字符串） */
  api_key_masked: string
  /** 服务器默认 API Base URL */
  base_url: string
  /** 服务器默认模型名称 */
  model_name: string
}

/** 任务状态：running 转换中 / completed 已完成 / failed 失败 / cancelled 已取消 */
export type JobStatus = 'running' | 'completed' | 'failed' | 'cancelled'

/** 任务进度日志条目 */
export interface JobLogEntry {
  time: string
  stage: string
  message: string
}

/** 转换任务元数据（后端落盘任务的状态快照） */
export interface JobMeta {
  job_id: string
  status: JobStatus
  novel_title: string
  model_name: string
  created_at: number
  updated_at: number
  total_chunks: number
  completed_chunks: number
  failed_chunks: number[]
  resumed_chunks: number[]
  error: string | null
  message: string
  logs: JobLogEntry[]
  /** 任务已完成且请求附带结果时存在 */
  result?: JobResultPayload | null
}

/** 任务缓存结果载荷（result.json / SSE result 事件） */
export interface JobResultPayload {
  job_id: string
  scenes: number
  characters: number
  script_data: ScriptYAML
  yaml_text: string
  message: string
}

/** 单元类型到中文标签的映射 */
export const UNIT_TYPE_LABELS: Record<SceneContentUnit['unit_type'], string> = {
  action: '动作',
  dialogue: '台词',
  narration: '旁白',
  psy: '心理',
}

/** 单元类型到颜色值的映射（用于视觉区分） */
export const UNIT_TYPE_COLORS: Record<SceneContentUnit['unit_type'], string> = {
  action: '#409EFF',   // 蓝色
  dialogue: '#67C23A', // 绿色
  narration: '#909399', // 灰色
  psy: '#E6A23C',      // 橙色/紫色
}
