<template>
  <div class="yaml-editor">
    <div class="editor-header" v-if="showHeader">
      <span class="header-title">YAML 源码预览</span>
      <el-button size="small" text @click="copyToClipboard">
        <el-icon><CopyDocument /></el-icon> 复制
      </el-button>
    </div>
    <pre class="editor-content"><code>{{ yamlText }}</code></pre>
  </div>
</template>

<script setup lang="ts">
import { CopyDocument } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

/** 组件属性定义 */
withDefaults(defineProps<{
  /** YAML 文本内容 */
  yamlText: string
  /** 是否显示头部工具栏 */
  showHeader?: boolean
}>(), {
  showHeader: true,
})

/**
 * 复制 YAML 内容到系统剪贴板
 */
async function copyToClipboard() {
  // 通过事件获取实际文本内容（由父组件传入）
  const content = document.querySelector('.editor-content code')?.textContent || ''
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('已复制到剪贴板')
  } catch {
    // 降级方案：使用 execCommand
    const textarea = document.createElement('textarea')
    textarea.value = content
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('已复制到剪贴板')
  }
}
</script>

<style scoped>
.yaml-editor {
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background: #2d2d30;
  border-bottom: 1px solid #3e3e42;
}

.header-title {
  font-size: 12px;
  color: #cccccc;
  font-family: monospace;
}

.editor-content {
  margin: 0;
  padding: 16px 18px;
  max-height: 400px;
  overflow: auto;
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.7;
  color: #d4d4d4;
  tab-size: 2;
}

.editor-content::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.editor-content::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

.editor-content::-webkit-scrollbar-track {
  background: transparent;
}
</style>
