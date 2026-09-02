<template>
  <div class="home-view">
    <!-- Hero 区域 -->
    <section class="hero">
      <div class="hero-badge">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        AI-Powered
      </div>
      <h1 class="hero-title">
        小说<span class="title-accent"> → </span>剧本
      </h1>
      <p class="hero-desc">
        输入长篇小说文本，AI 自动解析场景、提取台词、结构化输出<br/>
        一键生成可编辑、可打磨的影视级 YAML 剧本初稿
      </p>
      <div class="hero-stats">
        <div class="stat-item">
          <span class="stat-num">3+</span>
          <span class="stat-label">章节批量</span>
        </div>
        <div class="stat-dot"></div>
        <div class="stat-item">
          <span class="stat-num">YAML</span>
          <span class="stat-label">标准输出</span>
        </div>
        <div class="stat-dot"></div>
        <div class="stat-item">
          <span class="stat-num">可编辑</span>
          <span class="stat-label">二次打磨</span>
        </div>
      </div>
    </section>

    <!-- 主表单卡片 -->
    <section class="form-section">
      <div class="form-card">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          class="convert-form"
        >
          <!-- 小说名称 -->
          <div class="form-group">
            <label class="form-label">
              <span class="label-icon">01</span> 原著名称
            </label>
            <el-input
              v-model="form.novel_title"
              placeholder="输入小说名称，如「晚风归期」"
              size="large"
              clearable
            />
          </div>

          <!-- 输入方式切换 -->
          <div class="input-mode-switch">
            <button
              type="button"
              class="mode-btn"
              :class="{ active: inputMode === 'text' }"
              @click="inputMode = 'text'"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
              粘贴文本
            </button>
            <button
              type="button"
              class="mode-btn"
              :class="{ active: inputMode === 'file' }"
              @click="inputMode = 'file'"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              上传文件
            </button>
          </div>

          <!-- 文本粘贴模式 -->
          <div v-show="inputMode === 'text'" class="form-group textarea-group">
            <label class="form-label">
              <span class="label-icon">02</span> 小说正文
              <span class="label-hint">支持多章节长文本，系统自动识别章节</span>
            </label>
            <el-input
              v-model="form.novel_text"
              type="textarea"
              :rows="10"
              placeholder="在此粘贴小说正文...&#10;&#10;提示：可直接复制整本小说的正文内容，支持 3 章及以上批量转换。&#10;系统会自动识别章节分隔符，保持剧情连贯性。"
              show-word-limit
              :maxlength="500000"
              class="novel-textarea"
            />
            <div class="textarea-footer">
              <span class="footer-hint">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                建议一次上传 3–20 章，最多 50 万字
              </span>
            </div>
          </div>

          <!-- 文件上传模式 -->
          <div v-show="inputMode === 'file'" class="form-group upload-group">
            <label class="form-label">
              <span class="label-icon">02</span> 选择文件
            </label>
            <el-upload
              ref="uploadRef"
              drag
              :auto-upload="false"
              :limit="1"
              accept=".txt,.md,.markdown,.epub"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
            >
              <div class="upload-area">
                <div class="upload-icon-wrap">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                </div>
                <p class="upload-text">拖放小说文件到此处，或 <em>点击选择</em></p>
                <p class="upload-tip">支持 .txt / .md / .epub · 最大 10MB</p>
              </div>
            </el-upload>
          </div>

          <!-- AI 配置（折叠） -->
          <details class="config-details">
            <summary class="config-summary">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001.51 1 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
              AI 模型配置
              <span v-if="serverConfigured" class="config-badge ok">服务器已配置</span>
              <span v-else class="config-badge warn">未配置 · 需填写</span>
              <span class="config-arrow">▾</span>
            </summary>
            <div class="config-body">
              <div v-if="serverConfigured" class="config-hint ok">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                将使用服务器默认配置（Key: {{ serverConfig?.api_key_masked }} · 模型: {{ serverConfig?.model_name }}），以下留空即可
              </div>
              <div v-else class="config-hint warn">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                服务器未配置默认 API，请填写下方信息
              </div>
              <div class="config-grid">
                <div class="config-field">
                  <label class="cfg-label">API Key</label>
                  <el-input
                    v-model="form.api_key"
                    :placeholder="serverConfigured ? `留空用默认 (${serverConfig?.api_key_masked})` : 'sk-...'"
                    show-password
                    type="password"
                    size="default"
                  />
                </div>
                <div class="config-field">
                  <label class="cfg-label">API 地址</label>
                  <el-input
                    v-model="form.base_url"
                    :placeholder="serverConfigured ? '留空使用服务器默认' : 'https://api.openai.com/v1'"
                    size="default"
                  />
                </div>
                <div class="config-field">
                  <label class="cfg-label">模型</label>
                  <el-select
                    v-model="form.model_name"
                    :placeholder="serverConfigured ? `默认: ${serverConfig?.model_name}` : '选择或输入模型'"
                    allow-create
                    filterable
                    clearable
                    style="width: 100%"
                  >
                    <el-option label="GPT-4o Mini" value="gpt-4o-mini" />
                    <el-option label="GPT-4o" value="gpt-4o" />
                    <el-option label="GPT-4 Turbo" value="gpt-4-turbo" />
                    <el-option label="Claude 3.5 Sonnet" value="claude-3-5-sonnet-20241022" />
                    <el-option label="通义千问-Max" value="qwen-max" />
                    <el-option label="DeepSeek-V3" value="deepseek-chat" />
                    <el-option label="Gemini 2.0 Flash" value="gemini-2.0-flash" />
                    <el-option
                      label="── 支持自定义 ──"
                      value=""
                      disabled
                      class="custom-divider"
                    />
                  </el-select>
                </div>
              </div>
              <!-- 测试连接按钮 -->
              <div class="test-conn-row">
                <button
                  type="button"
                  class="test-conn-btn"
                  :class="{ testing: testingConn }"
                  :disabled="testingConn || !canTestConnection"
                  @click="handleTestConnection"
                >
                  <span v-if="!testingConn" class="btn-inner">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    测试连接
                  </span>
                  <span v-else class="btn-inner spinning">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="32"><animate attributeName="stroke-dashoffset" values="32;0" dur="1s" repeatCount="indefinite"/></circle></svg>
                    测试中...
                  </span>
                </button>
                <span v-if="connResult" class="conn-result" :class="connResult.success ? 'ok' : 'err'">
                  {{ connResult.message }}
                  <span v-if="connResult.latency_ms" class="conn-latency">{{ connResult.latency_ms }}ms</span>
                </span>
              </div>
            </div>
          </details>

          <!-- 提交按钮 -->
          <div class="submit-row">
            <button
              class="submit-btn"
              :class="{ loading: converting }"
              :disabled="converting"
              @click="handleSubmit"
            >
              <span v-if="!converting" class="btn-content">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                开始转换
              </span>
              <span v-else class="btn-loading">
                <span class="spinner"></span>
                {{ currentStage || 'AI 正在解析中...' }}
              </span>
            </button>

            <!-- 取消按钮（转换进行中时显示） -->
            <button
              v-if="converting"
              class="cancel-btn"
              @click="handleCancelConvert"
            >
              取消转换
            </button>
          </div>

          <!-- 流式进度面板 -->
          <transition name="progress-fade">
            <div v-if="converting && (progressLogs.length > 0 || isStreaming)" class="progress-panel">
              <!-- 进度条 -->
              <div class="progress-bar-track" v-if="totalChunks > 0">
                <div
                  class="progress-bar-fill"
                  :style="{ width: progressPercent + '%' }"
                ></div>
                <span class="progress-bar-text">{{ completedChunks }}/{{ totalChunks }} 分片</span>
              </div>

              <!-- 流式输出区域（LLM 实时返回内容） -->
              <div v-if="isStreaming || streamText" class="stream-output">
                <div class="stream-header">
                  <span class="stream-label">AI 输出</span>
                  <span class="stream-stats">{{ streamLength }}B{{ streamTokens ? ' | ' + streamTokens + ' tokens' : '' }}</span>
                </div>
                <pre class="stream-body" ref="streamBodyRef"><code v-html="highlightedStreamText"></code></pre>
              </div>

              <!-- 实时日志 -->
              <div ref="logContainerRef" class="log-container">
                <div
                  v-for="(log, idx) in progressLogs"
                  :key="idx"
                  class="log-line"
                  :class="'log-' + log.stage"
                >
                  <span class="log-time">{{ log.time }}</span>
                  <span class="log-msg">{{ log.message }}</span>
                  <span v-if="log.extra" class="log-extra">{{ log.extra }}</span>
                </div>
                <!-- 动态活动行：显示当前阶段 + 已用时间 -->
                <div class="log-line log-active">
                  <span class="log-time">{{ getCurrentTime() }}</span>
                  <span class="log-msg">
                    <span v-if="currentStage" class="log-stage-text">{{ currentStage }}</span>
                    <span v-else class="log-blink">等待响应...</span>
                  </span>
                  <span class="log-extra log-elapsed">⏱ {{ elapsedSeconds }}s</span>
                </div>
              </div>
            </div>
          </transition>
        </el-form>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted, onUnmounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { convertNovelStream, testConnection, getConfigStatus } from '@/api/script'
import type { ConfigStatus } from '@/types/script'
import JSZip from 'jszip'

const router = useRouter()
const formRef = ref<FormInstance>()
const uploadRef = ref()
const logContainerRef = ref<HTMLElement | null>(null)
const inputMode = ref<'text' | 'file'>('text')
const converting = ref(false)
const testingConn = ref(false)
const connResult = ref<{ success: boolean; message: string; latency_ms?: number } | null>(null)

// 流式进度相关状态
interface ProgressLog {
  time: string
  stage: string
  message: string
  extra?: string
}
const progressLogs = ref<ProgressLog[]>([])
const currentStage = ref('')
const totalChunks = ref(0)
const completedChunks = ref(0)
const elapsedSeconds = ref(0)
// 流式输出相关状态
const isStreaming = ref(false)
const streamText = ref('')
const streamTokens = ref('')
let abortController: AbortController | null = null
let elapsedTimer: ReturnType<typeof window.setInterval> | null = null
const streamBodyRef = ref<HTMLElement | null>(null)

/** 流式文本累计字节数 */
const streamLength = computed(() => new TextEncoder().encode(streamText.value).length)

/** 流式文本语法高亮（YAML key/value 着色） */
const highlightedStreamText = computed(() => {
  const text = streamText.value
  if (!text) return ''
  // 转义 HTML 特殊字符
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  // YAML key: value 着色（冒号前的键名 + 冒号 → 青色，值保持白色）
  return escaped.replace(
    /^(\s*)([\w\u4e00-\u9fff_][\w\s\-\/\u4e00-\u9fff_]*)(\s*:\s*)/gm,
    '$1<span class="st-key">$2</span><span class="st-colon">$3</span>'
  )
})

/** 启动已用时间计时器 */
function startElapsedTimer() {
  elapsedSeconds.value = 0
  elapsedTimer = setInterval(() => {
    elapsedSeconds.value++
  }, 1000)
}

/** 停止计时器 */
function stopElapsedTimer() {
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
}

const form = reactive({
  novel_title: '',
  novel_text: '',
  api_key: '',
  base_url: '',
  model_name: '',
})

// 服务器端 AI 配置状态（env_file 注入的 OPENAI_* 环境变量）
const serverConfig = ref<ConfigStatus | null>(null)

/** 服务器是否已配置完整 AI 信息（可留空表单直接提交） */
const serverConfigured = computed(() => serverConfig.value?.configured === true)

/** 表单 AI 配置是否完整填写 */
const formConfigComplete = computed(() => !!(form.api_key && form.base_url && form.model_name))

/** 「测试连接」可用条件：表单填写完整，或服务器已配置默认值 */
const canTestConnection = computed(() => formConfigComplete.value || serverConfigured.value)

onMounted(async () => {
  try {
    serverConfig.value = await getConfigStatus()
  } catch {
    // 查询失败按未配置处理，不影响表单手动填写
    serverConfig.value = { configured: false, api_key_masked: '', base_url: '', model_name: '' }
  }
})

const rules: FormRules = {
  novel_title: [
    { required: true, message: '请输入小说名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' },
  ],
  novel_text: [
    { required: true, message: '请提供小说正文内容', trigger: 'change' },
    { min: 100, message: '正文内容至少需要 100 个字符', trigger: 'change' },
  ],
}

/**
 * 处理文件选择变化
 * 支持 .txt / .md / .markdown / .epub 四种格式
 * @param file - el-upload 传递的文件对象
 */
async function handleFileChange(file: any) {
  const raw = file.raw
  if (!raw) return

  const ext = raw.name.split('.').pop()?.toLowerCase()

  try {
    switch (ext) {
      case 'txt':
      case 'md':
      case 'markdown': {
        // 纯文本格式：直接读取
        form.novel_text = await readFileAsText(raw)
        break
      }
      case 'epub': {
        // EPUB 格式：解压后提取文本内容
        converting.value = true
        ElMessage.info('正在解析 EPUB 文件...')
        form.novel_text = await parseEpubText(raw)
        ElMessage.success('EPUB 解析完成')
        break
      }
      default:
        ElMessage.error(`不支持的文件格式：.${ext}`)
    }
  } catch (error: any) {
    console.error('文件读取失败:', error)
    ElMessage.error(error.message || '文件读取失败')
  } finally {
    converting.value = false
  }
}

/**
 * 将 File 对象读取为纯文本字符串
 * @param file - 要读取的文件对象
 * @returns 文件的文本内容
 */
function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve((e.target?.result as string) || '')
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsText(file, 'UTF-8')
  })
}

/**
 * 解析 EPUB 电子书，提取纯文本内容
 *
 * EPUB 本质是一个 ZIP 压缩包，内部包含：
 * - META-INF/container.xml：定位 OPF 文件路径
 * - *.opf（OEBPS Package Format）：定义书籍结构和章节清单
 * - *.html / *.xhtml：各章节的实际内容
 *
 * @param file - EPUB 文件对象
 * @returns 提取出的纯文本内容（按章节拼接）
 * @throws 当文件无法解压或无有效内容时抛出错误
 */
async function parseEpubText(file: File): Promise<string> {
  // 使用 JSZip 解压 EPUB（本质是 ZIP 包）
  const zip = await JSZip.loadAsync(file)

  // 1. 从 container.xml 中找到 OPF 文件路径
  const containerXml = await zip.file('META-INF/container.xml')?.async('text')
  if (!containerXml) throw new Error('无效的 EPUB 文件：缺少 container.xml')

  // 用正则提取 rootfile 的 full-path 属性值
  const opfMatch = containerXml.match(/full-path="([^"]+)"/)
  if (!opfMatch) throw new Error('无效的 EPUB 文件：无法定位 OPF 文件')
  const opfPath = opfMatch[1]

  // 2. 读取 OPF 文件，提取所有章节文件路径（spine 中引用的 idref 对应 manifest 中的 href）
  const opfContent = await zip.file(opfPath)?.async('text')
  if (!opfContent) throw new Error('无效的 EPUB 文件：无法读取 OPF 内容')

  // 提取 manifest 中所有 id -> href 映射
  const manifestMap: Record<string, string> = {}
  const manifestRegex = /<item\s+id="([^"]+)"\s+href="([^"]+)"/g
  let m: RegExpExecArray | null
  while ((m = manifestRegex.exec(opfContent)) !== null) {
    manifestMap[m[1]] = m[2]
  }

  // 按 spine 顺序收集章节 ID
  const spineIds: string[] = []
  const spineRegex = /<itemref\s+idref="([^"]+)"/g
  while ((m = spineRegex.exec(opfContent)) !== null) {
    spineIds.push(m[1])
  }

  // 3. 如果没有 spine，直接扫描所有 HTML/XHTML 文件作为备选
  let chapterPaths: string[] = []
  if (spineIds.length > 0) {
    const opfDir = opfPath.substring(0, opfPath.lastIndexOf('/') + 1)
    for (const id of spineIds) {
      if (manifestMap[id]) {
        chapterPaths.push(opfDir + manifestMap[id])
      }
    }
  }

  // 备选方案：当 spine 为空时，遍历 ZIP 中所有 HTML/XHTML 文件
  if (chapterPaths.length === 0) {
    const htmlRegex = /\.(x?html|xhtm)$/
    Object.keys(zip.files).forEach((filePath) => {
      if (htmlRegex.test(filePath) && !filePath.includes('toc')) {
        chapterPaths.push(filePath)
      }
    })
    // 按文件名排序确保章节顺序稳定
    chapterPaths.sort()
  }

  if (chapterPaths.length === 0) {
    throw new Error('EPUB 文件中未找到任何可读章节内容')
  }

  // 4. 逐章读取并提取纯文本
  const chapters: string[] = []
  for (const path of chapterPaths) {
    const content = await zip.file(path)?.async('text')
    if (!content) continue

    // 去除 HTML 标签、解码 HTML 实体、清理多余空白
    const text = stripHtmlTags(content).trim()
    if (text.length > 20) {  // 过滤过短的无关页面
      chapters.push(text)
    }
  }

  if (chapters.length === 0) {
    throw new Error('EPUB 文件中未提取到有效文本内容')
  }

  // 用双换行分隔章节，保持结构
  return chapters.join('\n\n\n')
}

/**
 * 去除 HTML 标签并清理文本
 * 处理常见 HTML 实体和多余空白字符
 * @param html - 含 HTML 标签的字符串
 * @returns 纯净的纯文本
 */
function stripHtmlTags(html: string): string {
  return html
    // 替换 <br> 和块级标签为换行
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div|h[1-6]|li|tr|section|article)[^>]*>/gi, '\n\n')
    // 移除所有剩余 HTML 标签
    .replace(/<[^>]+>/g, '')
    // 解码常见 HTML 实体
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&mdash;/g, '—')
    .replace(/&ndash;/g, '–')
    .replace(/&hellip;/g, '…')
    // 合并连续空白行（保留最多两个换行）
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function handleFileRemove() {
  form.novel_text = ''
}

/**
 * 测试 LLM 模型接口连通性
 * 发送最简请求验证 API Key / Base URL / 模型名是否有效
 */
async function handleTestConnection() {
  if (!formConfigComplete.value && !serverConfigured.value) {
    ElMessage.warning('请先填写完整的 AI 配置信息')
    return
  }

  testingConn.value = true
  connResult.value = null

  try {
    const result = await testConnection(form.api_key, form.base_url, form.model_name)
    connResult.value = result as any
    ElMessage.success(`连接成功 - ${result.model} (${result.latency_ms}ms)`)
  } catch (error: any) {
    // 区分网络超时和服务端返回的错误
    let msg = error.message || '连接测试失败'
    if (error.code === 'ECONNABORTED' || msg.includes('timeout')) {
      msg = '请求超时：API 响应时间过长（>35秒），请检查网络或更换响应更快的模型'
    }
    connResult.value = { success: false, message: msg }
    ElMessage.error(msg)
  } finally {
    testingConn.value = false
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    ElMessage.warning('请完善表单信息')
    return
  }

  converting.value = true
  progressLogs.value = []
  totalChunks.value = 0
  completedChunks.value = 0

  // 创建 AbortController 用于取消请求
  abortController = new AbortController()

  // 启动已用时间计时器
  startElapsedTimer()

  // 添加首条日志
  addLog('start', '提交转换请求...')

  try {
    const result = await convertNovelStream(
      {
        novel_title: form.novel_title,
        novel_text: form.novel_text,
        api_key: form.api_key || undefined,
        base_url: form.base_url || undefined,
        model_name: form.model_name || undefined,
      },
      // 进度回调
      (event) => {
        handleProgressEvent(event)
      },
      abortController.signal,
    )

    if (result.success && result.data) {
      addLog('done', `转换完成！共 ${result.message}`)
      sessionStorage.setItem('script_data', JSON.stringify(result.data))
      sessionStorage.setItem('yaml_text', result.yaml_text || '')
      ElMessage.success(result.message)
      router.push({ name: 'preview' })
    } else {
      ElMessage.error(result.message || '转换失败')
    }
  } catch (error: any) {
    // 区分不同错误类型给出明确提示
    let msg = error.message || '转换请求失败'
    if (error.name === 'AbortError') {
      msg = '用户取消了转换'
      addLog('cancelled', msg)
    } else if (msg.includes('timeout') || error.code === 'ECONNABORTED') {
      msg = '转换超时：文本较长时处理时间可能超过10分钟，请尝试缩短文本或使用更快的模型'
    } else if (msg.includes('429') || msg.includes('rate_limit')) {
      msg = 'API 频率限制：请求过于频繁，请稍后再试'
    } else if (msg.includes('401') || msg.includes('认证')) {
      msg = '认证失败：请检查 API Key 是否正确'
    } else if (msg.includes('400') && msg.includes('模型')) {
      msg = '模型不支持：当前模型名不被该 API 平台支持，请先测试连接确认'
    }
    addLog('error', msg)
    ElMessage.error(msg)
  } finally {
    converting.value = false
    abortController = null
    stopElapsedTimer()
  }
}

/**
 * 处理流式进度事件，更新UI状态和日志
 * @param event - 后端推送的进度事件对象
 */
function handleProgressEvent(event: { stage: string; message: string; data: Record<string, unknown> }) {
  const { stage, message, data } = event
  currentStage.value = message

  // === 流式输出事件处理 ===
  if (stage === 'stream_start') {
    isStreaming.value = true
    streamText.value = ''
    streamTokens.value = ''
    addLog('streaming', '[流式] 等待模型响应...')
    return // 不走通用日志流程
  }

  if (stage === 'stream_chunk') {
    const chunkText = data.text as string || ''
    if (chunkText) {
      streamText.value += chunkText
      // 自动滚动到流式输出底部
      nextTick(() => {
        if (streamBodyRef.value) {
          streamBodyRef.value.scrollTop = streamBodyRef.value.scrollHeight
        }
      })
    }
    currentStage.value = `[流式] 接收中... (${streamLength.value}B)`
    return // 不走通用日志流程（避免刷屏）
  }

  if (stage === 'stream_done') {
    isStreaming.value = false
    const totalTokens = data.total_tokens as number | undefined
    streamTokens.value = totalTokens ? String(totalTokens) : ''
    addLog('stream_done', `[流式完成] ${streamLength.value}B${totalTokens ? ' | ' + totalTokens + ' tokens' : ''}`)
    return
  }

  // === 常规进度事件处理 ===
  // 更新分片进度
  if (stage === 'chunks_ready' && data.total) {
    totalChunks.value = data.total as number
  }
  if (stage === 'chunk_done' && data.completed) {
    completedChunks.value = data.completed as number
  }

  // 构建额外信息
  let extra = ''
  if (stage === 'chunk_done' && data.scenes) {
    extra = `(+${data.scenes} 场)`
  }
  if (stage === 'chars_extracted' && data.char_count) {
    extra = `${data.char_count} 个角色`
  }

  addLog(stage, message, extra)

  // 自动滚动到底部
  nextTick(() => {
    if (logContainerRef.value) {
      logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
    }
  })
}

/**
 * 添加一条进度日志
 * @param stage - 阶段标识
 * @param message - 日志消息
 * @param extra - 额外信息（可选）
 */
function addLog(stage: string, message: string, extra?: string) {
  progressLogs.value.push({
    time: getCurrentTime(),
    stage,
    message,
    extra,
  })
  // 限制日志数量，防止内存溢出（保留最近200条）
  if (progressLogs.value.length > 200) {
    progressLogs.value = progressLogs.value.slice(-150)
  }
}

/** 获取当前时间字符串 HH:MM:SS */
function getCurrentTime(): string {
  const now = new Date()
  return [now.getHours(), now.getMinutes(), now.getSeconds()]
    .map((n) => String(n).padStart(2, '0'))
    .join(':')
}

/** 进度条百分比 */
const progressPercent = (): number => {
  if (totalChunks.value <= 0) return 0
  return Math.round((completedChunks.value / totalChunks.value) * 100)
}

/** 取消正在进行的转换 */
function handleCancelConvert() {
  if (abortController) {
    abortController.abort()
    addLog('cancelled', '用户取消转换请求')
  }
}

// 组件卸载时清理
onUnmounted(() => {
  if (abortController) {
    abortController.abort()
  }
  stopElapsedTimer()
})
</script>

<style scoped>
.home-view {
  animation: fadeInUp 0.6s var(--ease-out) both;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ====== Hero 区域 ====== */
.hero {
  text-align: center;
  margin-bottom: 48px;
  position: relative;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: 999px;
  background: var(--accent-dim);
  border: 1px solid rgba(201, 162, 39, 0.2);
  color: var(--accent-light);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 24px;
  animation: fadeInUp 0.5s var(--ease-out) 0.05s both;
}

.hero-title {
  font-family: var(--font-display);
  font-size: clamp(36px, 6vw, 52px);
  font-weight: 900;
  line-height: 1.15;
  color: var(--text-primary);
  margin-bottom: 18px;
  letter-spacing: 4px;
  animation: fadeInUp 0.5s var(--ease-out) 0.15s both;
}

.title-accent {
  color: var(--accent);
  font-style: italic;
}

.hero-desc {
  font-size: 15px;
  line-height: 1.85;
  color: var(--text-secondary);
  max-width: 520px;
  margin: 0 auto 30px;
  animation: fadeInUp 0.5s var(--ease-out) 0.25s both;
}

.hero-stats {
  display: inline-flex;
  align-items: center;
  gap: 20px;
  animation: fadeInUp 0.5s var(--ease-out) 0.35s both;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-num {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: var(--accent);
}

.stat-label {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.stat-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--border-medium);
}

/* ====== 表单区域 ====== */
.form-section {
  animation: fadeInUp 0.5s var(--ease-out) 0.4s both;
}

.form-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 36px 40px 40px;
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
}

.form-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    var(--accent-glow),
    transparent
  );
}

.convert-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
}

.label-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: var(--accent-dim);
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-ui);
}

.label-hint {
  font-weight: 400;
  color: var(--text-muted);
  font-size: 12px;
  margin-left: auto;
}

/* 输入方式切换 */
.input-mode-switch {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: var(--bg-base);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  width: fit-content;
}

.mode-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s var(--ease-out);
  font-family: var(--font-ui);
}
.mode-btn:hover {
  color: var(--text-secondary);
}
.mode-btn.active {
  background: var(--accent);
  color: #0a0a0c;
  font-weight: 600;
  box-shadow: 0 2px 12px var(--accent-glow);
}

/* Textarea 特殊样式 */
.novel-textarea :deep(.el-textarea__inner) {
  min-height: 240px !important;
  font-size: 14px;
  line-height: 1.8;
  resize: vertical;
}

.textarea-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-hint {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-muted);
}

/* Upload 区域 */
.upload-area {
  text-align: center;
  padding: 32px 0;
}
.upload-icon-wrap {
  color: var(--text-muted);
  margin-bottom: 12px;
}
.upload-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 4px;
}
.upload-text em {
  color: var(--accent);
  font-style: normal;
  font-weight: 600;
}
.upload-tip {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

/* AI 配置折叠面板 */
.config-details {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.config-details[open] .config-arrow {
  transform: rotate(180deg);
}

.config-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  list-style: none;
  user-select: none;
  transition: color 0.2s;
}
.config-summary::-webkit-details-marker {
  display: none;
}
.config-summary:hover {
  color: var(--text-secondary);
}

.config-arrow {
  margin-left: auto;
  font-size: 10px;
  transition: transform 0.25s var(--ease-out);
}

/* 配置状态徽章（折叠面板标题右侧） */
.config-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  letter-spacing: 0.5px;
  margin-left: auto;
}
.config-badge.ok {
  background: rgba(34, 197, 94, 0.12);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.25);
}
.config-badge.warn {
  background: rgba(245, 158, 11, 0.12);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.25);
}
.config-badge + .config-arrow {
  margin-left: 8px;
}

/* 配置提示行（服务器默认配置状态说明） */
.config-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 8px 12px;
  border-radius: var(--radius-sm, 6px);
  margin-bottom: 14px;
  line-height: 1.5;
}
.config-hint.ok {
  background: rgba(34, 197, 94, 0.08);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.18);
}
.config-hint.warn {
  background: rgba(245, 158, 11, 0.08);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.18);
}

.config-body {
  padding: 18px;
  border-top: 1px solid var(--border-subtle);
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.cfg-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

/* 提交按钮 */
.submit-row {
  display: flex;
  justify-content: center;
  padding-top: 8px;
}

.submit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px 48px;
  border: none;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--accent), var(--accent-light));
  color: #0a0a0c;
  font-size: 15px;
  font-weight: 700;
  font-family: var(--font-ui);
  cursor: pointer;
  transition: all 0.3s var(--ease-out);
  box-shadow: 0 4px 24px var(--accent-glow);
  letter-spacing: 1px;
  position: relative;
  overflow: hidden;
}
.submit-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(255,255,255,0.2) 50%, transparent 60%);
  transform: translateX(-100%);
  transition: transform 0.6s ease;
}
.submit-btn:hover:not(:disabled)::before {
  transform: translateX(100%);
}
.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 32px var(--accent-glow);
}
.submit-btn:disabled {
  opacity: 0.8;
  cursor: wait;
}

.btn-loading {
  display: flex;
  align-items: center;
  gap: 10px;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(10, 10, 12, 0.3);
  border-top-color: #0a0a0c;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 自定义模型分隔线 */
:deep(.custom-divider) {
  font-size: 11px !important;
  color: var(--text-muted) !important;
  cursor: default !important;
  letter-spacing: 1px;
}

/* 测试连接按钮行 */
.test-conn-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border-subtle);
}
.test-conn-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-elevated);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-ui);
  cursor: pointer;
  transition: all 0.25s var(--ease-out);
  white-space: nowrap;
}
.test-conn-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(201, 162, 39, 0.08);
}
.test-conn-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.test-conn-btn.testing {
  border-color: var(--accent-dim);
  color: var(--accent);
}
.btn-inner {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.spinning svg {
  animation: spin 1s linear infinite;
}

/* 连接测试结果 */
.conn-result {
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 320px;
}
.conn-result.ok {
  background: rgba(34, 197, 94, 0.12);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.2);
}
.conn-result.err {
  background: rgba(239, 68, 68, 0.12);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.2);
}
.conn-latency {
  margin-left: 6px;
  opacity: 0.7;
  font-weight: 400;
}

/* ====== 流式进度面板 ====== */
.cancel-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.25s;
}
.cancel-btn:hover {
  border-color: #f87171;
  color: #f87171;
  background: rgba(239, 68, 68, 0.08);
}

.progress-panel {
  margin-top: 20px;
  padding: 16px 18px;
  background: rgba(201, 162, 39, 0.04);
  border: 1px solid rgba(201, 162, 39, 0.15);
  border-radius: var(--radius-md);
  animation: panelSlideIn 0.4s var(--ease-out) both;
}

@keyframes panelSlideIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.progress-fade-enter-active { transition: all 0.4s var(--ease-out); }
.progress-fade-leave-active { transition: all 0.3s ease-in; }
.progress-fade-enter-from { opacity: 0; transform: translateY(10px); }
.progress-fade-leave-to { opacity: 0; }

/* 进度条 */
.progress-bar-track {
  position: relative;
  height: 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 14px;
}
.progress-bar-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent-light));
  border-radius: 3px;
  transition: width 0.5s ease;
  box-shadow: 0 0 8px var(--accent-glow);
}
.progress-bar-text {
  position: absolute;
  right: 0;
  top: -20px;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.5px;
}

/* 日志容器 */
.log-container {
  max-height: 240px;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 6px;
  padding: 10px 12px;
  /* 自定义滚动条 */
  scrollbar-width: thin;
  scrollbar-color: var(--border-color) transparent;
}
.log-container::-webkit-scrollbar { width: 4px; }
.log-container::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 2px; }

.log-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 3px 0;
  font-size: 12px;
  line-height: 1.6;
  animation: logFadeIn 0.25s ease both;
}
@keyframes logFadeIn {
  from { opacity: 0; transform: translateX(-6px); }
  to { opacity: 1; transform: translateX(0); }
}

.log-time {
  flex-shrink: 0;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 10px;
  color: var(--text-muted);
  opacity: 0.7;
  min-width: 48px;
}
.log-msg {
  color: var(--text-secondary);
}
.log-extra {
  margin-left: auto;
  flex-shrink: 0;
  font-size: 11px;
  color: var(--accent-dim);
  font-weight: 500;
}

/* 动态活动行 */
.log-stage-text {
  color: var(--accent);
  font-weight: 500;
}
.log-elapsed {
  color: var(--text-muted) !important;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  opacity: 0.8;
}

/* 各阶段颜色 */
.log-preprocessing .log-msg,
.log-parsed .log-msg,
.log-calling_llm .log-msg,
.log-chunking .log-msg,
.log-extracting_chars .log-msg { color: var(--text-secondary); }
.log-preprocessed .log-msg,
.log-chars_extracted .log-msg,
.log-chunks_ready .log-msg { color: #60a5fa; }
.log-chunk_start .log-msg,
.log-waiting .log-msg { color: var(--accent); }
.log-chunk_done .log-msg { color: #4ade80; }
.log-chunk_fail .log-msg { color: #fb923c; }
.log-merging .log-msg,
.log-refining_psy .log-msg { color: #c084fc; }
.log-done .log-msg { color: #4ade80; font-weight: 600; }
.log-error .log-msg,
.log-cancelled .log-msg { color: #f87171; font-weight: 500; }

.log-blink {
  animation: blink 1.2s ease infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ========== 流式输出区域（AI 实时返回内容）========== */
.stream-output {
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 6px;
  overflow: hidden;
}
.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  background: rgba(56, 189, 248, 0.08);
  border-bottom: 1px solid rgba(56, 189, 248, 0.15);
}
.stream-label {
  font-size: 11px;
  font-weight: 600;
  color: #38bdf8;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.stream-stats {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 10px;
  color: var(--text-muted);
}
.stream-body {
  margin: 0;
  padding: 10px 12px;
  max-height: 200px;
  overflow-y: auto;
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.65;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-all;
  scrollbar-width: thin;
  scrollbar-color: var(--border-color) transparent;
}
.stream-body::-webkit-scrollbar { width: 4px; }
.stream-body::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 2px; }
/* 流式输出语法高亮 */
.st-key {
  color: #38bdf8;   /* 青色 - YAML 键名 */
  font-weight: 500;
}
.st-colon {
  color: #f472b6;   /* 粉色 - 冒号分隔符 */
}

/* 流式阶段日志颜色 */
.log-streaming .log-msg { color: #38bdf8; }
.log-stream_done .log-msg { color: #4ade80; font-weight: 500; }
</style>
