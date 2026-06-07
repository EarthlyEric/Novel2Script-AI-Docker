/**
 * 后端 API 封装模块
 *
 * 基于 axios 封装所有后端接口调用，提供统一的错误处理、
 * 请求拦截和响应拦截机制。
 *
 * 接口列表：
 * - POST /api/script/convert        — 小说转剧本（同步）
 * - POST /api/script/convert-stream — 小说转剧本（SSE流式）
 * - GET  /api/script/schema          — 获取Schema信息
 * - POST /api/script/test-connection — 测试LLM连通性
 * - POST /api/script/validate        — 校验YAML内容
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
 * SSE 流式转换接口 — 实时接收解析进度
 *
 * 使用 fetch + ReadableStream 接收后端 SSE 事件流，
 * 通过回调函数实时推送进度更新、最终结果或错误信息。
 *
 * @param params - 转换请求参数
 * @param onProgress - 进度回调，每次收到 progress 事件时调用
 * @param signal - 可选 AbortSignal 用于取消请求
 * @returns Promise<ConvertResult> 最终转换结果
 * @throws 当收到 error 事件或网络错误时抛出异常
 */
export async function convertNovelStream(
  params: ConvertParams,
  onProgress?: (event: {
    stage: string
    message: string
    data: Record<string, unknown>
  }) => void,
  signal?: AbortSignal,
): Promise<ConvertResult> {
  const formData = new FormData()
  formData.append('novel_title', params.novel_title)
  formData.append('novel_text', params.novel_text)

  if (params.api_key) formData.append('api_key', params.api_key)
  if (params.base_url) formData.append('base_url', params.base_url)
  if (params.model_name) formData.append('model_name', params.model_name)

  const response = await fetch('/api/script/convert-stream', {
    method: 'POST',
    body: formData,
    headers: {},
    signal,
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  if (!response.body) {
    throw new Error('浏览器不支持流式读取')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let resultData: ConvertResult | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // 按双换行分割 SSE 事件
    const events = buffer.split('\n\n')
    // 最后一个可能是不完整的，保留在 buffer 中
    buffer = events.pop() || ''

    for (const event of events) {
      // 解析 event: xxx \n data: yyy 格式
      const lines = event.trim().split('\n')
      let eventType = 'message'
      let dataStr = ''

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
          dataStr = line.slice(5).trim()
        }
      }

      if (!dataStr) continue

      try {
        const data = JSON.parse(dataStr)

        switch (eventType) {
          case 'progress':
            onProgress?.({
              stage: data.stage || 'unknown',
              message: data.message || '',
              data: data.data || {},
            })
            break

          case 'result':
            resultData = {
              success: true,
              message: `成功转换，共生成 ${data.scenes} 场戏、${data.characters} 个角色`,
              data: data.script_data as ConvertResult['data'],
              yaml_text: data.yaml_text || '',
            }
            break

          case 'error':
            throw new Error(data.message || '转换过程中发生错误')

          case 'heartbeat':
            // 心跳包，忽略
            break
        }
      } catch (e) {
        // JSON 解析失败时忽略（可能是非标准数据）
        if ((e as Error).name !== 'SyntaxError') throw e
      }
    }
  }

  // 处理 buffer 中剩余数据
  if (buffer.trim()) {
    try {
      const data = JSON.parse(buffer.replace(/^data:\s*/m, '').trim())
      if (data.yaml_text && !resultData) {
        resultData = {
          success: true,
          message: `成功转换，共生成 ${data.scenes} 场戏、${data.characters} 个角色`,
          data: data.script_data as ConvertResult['data'],
          yaml_text: data.yaml_text || '',
        }
      }
    } catch {
      // 忽略剩余 buffer 解析错误
    }
  }

  if (!resultData) {
    throw new Error('未收到转换结果')
  }

  return resultData
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
