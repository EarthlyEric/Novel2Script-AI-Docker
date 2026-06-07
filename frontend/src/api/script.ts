/**
 * 后端 API 封装模块
 *
 * 基于 axios 封装所有后端接口调用，提供统一的错误处理、
 * 请求拦截和响应拦截机制。
 *
 * 接口列表：
 * - POST /api/script/convert   — 小说转剧本
 * - GET  /api/script/schema    — 获取Schema信息
 * - POST /api/script/validate  — 校验YAML内容
 */
import axios from 'axios'
import type { ConvertParams, ConvertResult, ValidateResult } from '@/types/script'

/**
 * axios 实例，配置基础URL、超时时间和拦截器
 */
const request = axios.create({
  baseURL: '/api',
  timeout: 180000, // AI转换可能耗时较长，设置3分钟超时
})

/**
 * 请求拦截器：可在此添加 token 等认证信息
 */
request.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

/**
 * 响应拦截器：统一处理 HTTP 错误码
 */
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.message ||
      '网络请求失败'
    return Promise.reject(new Error(message))
  }
)

/**
 * 调用小说转剧本接口
 *
 * 将小说文本发送给后端进行AI解析，返回结构化剧本数据和YAML文本
 *
 * @param params - 转换请求参数（小说名、正文、可选AI配置）
 * @returns 转换结果，包含结构化数据和纯YAML文本
 * @throws 当请求失败或服务端返回错误时抛出异常
 */
export async function convertNovel(params: ConvertParams): Promise<ConvertResult> {
  const formData = new FormData()
  formData.append('novel_title', params.novel_title)
  formData.append('novel_text', params.novel_text)

  if (params.api_key) formData.append('api_key', params.api_key)
  if (params.base_url) formData.append('base_url', params.base_url)
  if (params.model_name) formData.append('model_name', params.model_name)

  return request.post('/script/convert', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600000, // 转换请求10分钟超时（长文本分片处理可能耗时较长）
  })
}

/**
 * 获取 YAML Schema 规范说明
 *
 * @returns Schema 规范的结构化信息
 */
export async function getSchemaInfo(): Promise<unknown> {
  return request.get('/script/schema')
}

/**
 * 测试 LLM 模型接口连通性
 *
 * 发送最简请求验证 API Key、Base URL、模型名是否有效
 *
 * @param apiKey - API 密钥
 * @param baseUrl - API 地址
 * @param modelName - 模型名称
 * @returns 测试结果，包含 success/message/latency_ms 等
 */
export async function testConnection(
  apiKey: string,
  baseUrl: string,
  modelName: string,
): Promise<{ success: boolean; message: string; latency_ms?: number; model?: string; reply_preview?: string }> {
  const formData = new FormData()
  formData.append('api_key', apiKey)
  formData.append('base_url', baseUrl)
  formData.append('model_name', modelName)

  return request.post('/script/test-connection', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 35000, // 连接测试35秒超时（后端30s + 网络缓冲）
  })
}

/**
 * 校验 YAML 内容是否符合 Schema 规范
 *
 * 用于编辑页面实时校验用户修改后的YAML内容合法性
 *
 * @param yamlText - 待校验的YAML文本内容
 * @returns 校验结果，包含是否通过和错误详情
 */
export async function validateYaml(yamlText: string): Promise<ValidateResult> {
  return request.post('/script/validate', { yaml_text: yamlText })
}
