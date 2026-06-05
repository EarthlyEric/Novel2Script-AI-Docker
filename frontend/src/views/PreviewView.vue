<template>
  <div class="preview-view" v-if="scriptData">
    <!-- 顶部操作条 -->
    <div class="top-bar">
      <div class="bar-left">
        <button class="nav-back" @click="$router.push('/')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
          返回修改
        </button>
      </div>
      <div class="bar-right">
        <button class="action-btn primary" @click="goToEdit">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          进入编辑
        </button>
        <button class="action-btn success" @click="downloadYaml">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          下载 YAML
        </button>
      </div>
    </div>

    <!-- 剧本标题卡 -->
    <div class="script-title-block">
      <div class="title-decoration">
        <span class="deco-line"></span>
        <span class="deco-dot"></span>
        <span class="deco-line"></span>
      </div>
      <h2 class="script-title">{{ scriptData.script_meta.script_title }}</h2>
      <p class="script-subtitle">{{ scriptData.script_meta.original_novel_title }} · {{ scriptData.script_meta.chapter_range }} · {{ scriptData.script_meta.script_type }}</p>
    </div>

    <!-- 元数据网格 -->
    <div class="meta-grid">
      <div class="meta-cell">
        <span class="meta-label">版本</span>
        <span class="meta-value">{{ scriptData.script_meta.version }}</span>
      </div>
      <div class="meta-cell">
        <span class="meta-label">生成时间</span>
        <span class="meta-value">{{ scriptData.script_meta.create_time }}</span>
      </div>
      <div class="meta-cell">
        <span class="meta-label">场次总数</span>
        <span class="meta-value accent">{{ scriptData.script_scenes.length }} 场</span>
      </div>
      <div class="meta-cell">
        <span class="meta-label">登场人物</span>
        <span class="meta-value accent">{{ scriptData.global_characters.length }} 人</span>
      </div>
    </div>

    <!-- 人物库 -->
    <div class="cast-section" v-if="scriptData.global_characters.length > 0">
      <div class="section-head">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
        <span>人物库</span>
      </div>
      <div class="cast-list">
        <CharacterTag
          v-for="char in scriptData.global_characters"
          :key="char.char_id"
          :name="char.char_name"
          :profile="char.char_profile"
        />
      </div>
    </div>

    <!-- 场次列表 -->
    <div class="scenes-section">
      <div class="section-head">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/></svg>
        <span>剧本场次</span>
        <span class="scene-count-tag">{{ scriptData.script_scenes.length }} 场</span>
      </div>

      <div class="scenes-list">
        <SceneCard
          v-for="(scene, index) in scriptData.script_scenes"
          :key="scene.scene_id"
          :scene="scene"
          :index="index"
        />
      </div>
    </div>

    <!-- 改编说明 -->
    <div class="adapt-note" v-if="scriptData.adapt_rule_note">
      <div class="note-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2a7 7 0 017 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 01-2 2H10a2 2 0 01-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 017-7z"/><line x1="9" y1="22" x2="15" y2="22"/></svg>
      </div>
      <div class="note-body">
        <strong>改编说明</strong>
        <p>{{ scriptData.adapt_rule_note }}</p>
      </div>
    </div>

    <!-- 底部固定操作栏 -->
    <div class="bottom-bar">
      <button class="bar-btn ghost" @click="$router.push('/')">返回修改</button>
      <button class="bar-btn primary" @click="goToEdit">进入编辑</button>
      <button class="bar-btn success" @click="downloadYaml">下载 YAML</button>
    </div>
  </div>

  <!-- 无数据状态 -->
  <div class="empty-state" v-else>
    <div class="empty-icon">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
    </div>
    <h3>暂无剧本数据</h3>
    <p>请先上传小说文本进行 AI 转换</p>
    <button class="empty-action" @click="$router.push('/')">去上传</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { ScriptYAML } from '@/types/script'
import SceneCard from '@/components/SceneCard.vue'
import CharacterTag from '@/components/CharacterTag.vue'

const router = useRouter()
const scriptData = ref<ScriptYAML | null>(null)
const yamlText = ref('')

onMounted(() => {
  const stored = sessionStorage.getItem('script_data')
  if (stored) {
    try {
      scriptData.value = JSON.parse(stored)
      yamlText.value = sessionStorage.getItem('yaml_text') || ''
    } catch {
      ElMessage.error('数据格式异常，请重新转换')
    }
  }
})

function goToEdit() {
  router.push({ name: 'edit' })
}

function downloadYaml() {
  if (!yamlText.value) {
    ElMessage.warning('无可下载的内容')
    return
  }
  const title = scriptData.value?.script_meta.script_title || 'script'
  const blob = new Blob([yamlText.value], { type: 'text/yaml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${title}.yaml`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('文件已开始下载')
}
</script>

<style scoped>
.preview-view {
  animation: fadeInUp 0.5s var(--ease-out) both;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ====== 顶部操作条 ====== */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.nav-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-family: var(--font-ui);
  cursor: pointer;
  transition: all 0.2s;
}
.nav-back:hover {
  color: var(--text-primary);
  border-color: var(--border-medium);
  background: var(--bg-card);
}

.bar-right {
  display: flex;
  gap: 10px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-ui);
  cursor: pointer;
  transition: all 0.25s var(--ease-out);
}
.action-btn:hover {
  border-color: var(--border-medium);
  color: var(--text-primary);
}
.action-btn.primary {
  border-color: var(--accent);
  color: var(--accent);
}
.action-btn.primary:hover {
  background: var(--accent-dim);
}
.action-btn.success {
  border-color: var(--color-dialogue);
  color: var(--color-dialogue);
}
.action-btn.success:hover {
  background: rgba(126, 207, 153, 0.08);
}

/* ====== 剧本标题块 ====== */
.script-title-block {
  text-align: center;
  margin-bottom: 32px;
  padding: 32px 0 24px;
  position: relative;
}

.title-decoration {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 20px;
}
.deco-line {
  width: 48px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent));
}
.deco-line:last-child {
  background: linear-gradient(90deg, var(--accent), transparent);
}
.deco-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent-glow);
}

.script-title {
  font-family: var(--font-display);
  font-size: clamp(26px, 4vw, 36px);
  font-weight: 900;
  color: var(--text-primary);
  letter-spacing: 4px;
  margin-bottom: 8px;
}

.script-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  letter-spacing: 2px;
}

/* ====== 元数据网格 ====== */
.meta-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-bottom: 32px;
}

.meta-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 18px 12px;
  background: var(--bg-base);
}

.meta-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.meta-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  font-family: var(--font-ui);
}
.meta-value.accent {
  color: var(--accent);
}

/* ====== 人物库 ====== */
.cast-section {
  margin-bottom: 32px;
}

.section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 1px;
}

.scene-count-tag {
  margin-left: auto;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--accent-dim);
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
}

.cast-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

/* ====== 场次列表 ====== */
.scenes-section {
  margin-bottom: 32px;
}

.scenes-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ====== 改编说明 ====== */
.adapt-note {
  display: flex;
  gap: 14px;
  padding: 20px 24px;
  background: rgba(232, 168, 76, 0.05);
  border: 1px solid rgba(232, 168, 76, 0.12);
  border-radius: var(--radius-md);
  margin-bottom: 32px;
}

.note-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--accent-dim);
  color: var(--accent);
}

.note-body strong {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-light);
  margin-bottom: 6px;
}

.note-body p {
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-secondary);
  margin: 0;
  white-space: pre-wrap;
}

/* ====== 底部操作栏 ====== */
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  gap: 10px;
  padding: 14px 24px;
  background: rgba(10, 10, 12, 0.88);
  backdrop-filter: blur(16px);
  border-top: 1px solid var(--border-subtle);
  z-index: 100;
}

.bar-btn {
  padding: 8px 22px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-ui);
  cursor: pointer;
  transition: all 0.2s;
}
.bar-btn:hover {
  border-color: var(--border-medium);
  color: var(--text-primary);
}
.bar-btn.primary {
  border-color: var(--accent);
  color: var(--accent);
}
.bar-btn.primary:hover {
  background: var(--accent-dim);
}
.bar-btn.success {
  border-color: var(--color-dialogue);
  color: var(--color-dialogue);
}
.bar-btn.success:hover {
  background: rgba(126, 207, 153, 0.08);
}

/* ====== 空状态 ====== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120px 0;
  text-align: center;
}

.empty-icon {
  color: var(--text-muted);
  opacity: 0.3;
  margin-bottom: 20px;
}

.empty-state h3 {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.empty-state p {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 24px;
}

.empty-action {
  padding: 10px 28px;
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--accent);
  font-size: 14px;
  font-weight: 600;
  font-family: var(--font-ui);
  cursor: pointer;
  transition: all 0.25s;
}
.empty-action:hover {
  background: var(--accent-dim);
}
</style>
