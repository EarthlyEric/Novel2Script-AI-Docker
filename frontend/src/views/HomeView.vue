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
              accept=".txt"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
            >
              <div class="upload-area">
                <div class="upload-icon-wrap">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                </div>
                <p class="upload-text">拖放 .txt 文件到此处，或 <em>点击选择</em></p>
                <p class="upload-tip">最大 10MB · UTF-8 编码</p>
              </div>
            </el-upload>
          </div>

          <!-- AI 配置（折叠） -->
          <details class="config-details">
            <summary class="config-summary">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
              AI 模型配置
              <span class="config-arrow">▾</span>
            </summary>
            <div class="config-body">
              <div class="config-grid">
                <div class="config-field">
                  <label class="cfg-label">API Key</label>
                  <el-input
                    v-model="form.api_key"
                    placeholder="sk-..."
                    show-password
                    type="password"
                    size="default"
                  />
                </div>
                <div class="config-field">
                  <label class="cfg-label">API 地址</label>
                  <el-input
                    v-model="form.base_url"
                    placeholder="https://api.openai.com/v1"
                    size="default"
                  />
                </div>
                <div class="config-field">
                  <label class="cfg-label">模型</label>
                  <el-select
                    v-model="form.model_name"
                    placeholder="选择或输入模型"
                    allow-create
                    filterable
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
                AI 正在解析中...
              </span>
            </button>
          </div>
        </el-form>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { convertNovel } from '@/api/script'

const router = useRouter()
const formRef = ref<FormInstance>()
const uploadRef = ref()
const inputMode = ref<'text' | 'file'>('text')
const converting = ref(false)

const form = reactive({
  novel_title: '',
  novel_text: '',
  api_key: '',
  base_url: '',
  model_name: 'gpt-4o-mini',
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

function handleFileChange(file: any) {
  const reader = new FileReader()
  reader.onload = (e) => {
    form.novel_text = (e.target?.result as string) || ''
  }
  reader.readAsText(file.raw)
}

function handleFileRemove() {
  form.novel_text = ''
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

  try {
    const result = await convertNovel({
      novel_title: form.novel_title,
      novel_text: form.novel_text,
      api_key: form.api_key || undefined,
      base_url: form.base_url || undefined,
      model_name: form.model_name || undefined,
    })

    if (result.success && result.data) {
      sessionStorage.setItem('script_data', JSON.stringify(result.data))
      sessionStorage.setItem('yaml_text', result.yaml_text || '')
      ElMessage.success(result.message)
      router.push({ name: 'preview' })
    } else {
      ElMessage.error(result.message || '转换失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '转换请求失败')
  } finally {
    converting.value = false
  }
}
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
</style>
