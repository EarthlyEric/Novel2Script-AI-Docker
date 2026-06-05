<template>
  <div class="unit-item" :class="[`unit-${unit.unit_type}`]">
    <div class="unit-header">
      <span class="type-indicator" :class="'ti-' + unit.unit_type">
        {{ typeLabel }}
      </span>
      <CharacterTag
        v-if="unit.character"
        :name="unit.character"
        size="small"
      />
    </div>
    <div class="unit-body" v-html="formattedContent"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SceneContentUnit } from '@/types/script'
import { UNIT_TYPE_LABELS } from '@/types/script'
import CharacterTag from '@/components/CharacterTag.vue'

const props = defineProps<{
  unit: SceneContentUnit
  index?: number
}>()

/** 单元类型中文标签 */
const typeLabel = computed(() => UNIT_TYPE_LABELS[props.unit.unit_type])

/**
 * 格式化内容文本，根据类型应用不同视觉样式
 *
 * - dialogue: 引号包裹，绿色强调
 * - action: 斜体显示，蓝色调
 * - narration: 缩进灰色显示
 * - psy: 斜体缩进，暖色调
 */
const formattedContent = computed(() => {
  const text = escapeHtml(props.unit.content)
  switch (props.unit.unit_type) {
    case 'dialogue':
      return `<span class="dl-text"><span class="dl-q">&ldquo;</span>${text}<span class="dl-q">&rdquo;</span></span>`
    case 'action':
      return `<em class="ac-text">${text}</em>`
    case 'narration':
      return `<span class="nr-text">${text}</span>`
    case 'psy':
      return `<em class="psy-text">${text}</em>`
    default:
      return text
  }
})

/**
 * 转义 HTML 特殊字符防止 XSS
 */
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
</script>

<style scoped>
.unit-item {
  padding: 10px 14px 10px 16px;
  border-radius: var(--radius-sm);
  transition: background 0.2s;
  position: relative;
  animation: unitIn 0.3s var(--ease-out) both;
  animation-delay: calc((props.index || 0) * 0.04s);
}
@keyframes unitIn {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}

.unit-item:hover {
  background: var(--bg-card-hover);
}

/* 类型左侧色条 */
.unit-action { border-left: 2.5px solid var(--color-action); }
.unit-dialogue { border-left: 2.5px solid var(--color-dialogue); }
.unit-narration { border-left: 2.5px solid var(--color-narration); }
.unit-psy { border-left: 2.5px solid var(--color-psy); }

/* 头部 */
.unit-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.type-indicator {
  font-family: var(--font-ui);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 2px 9px;
  border-radius: 4px;
}
.ti-action { background: rgba(107, 159, 255, 0.1); color: var(--color-action); }
.ti-dialogue { background: rgba(126, 207, 153, 0.1); color: var(--color-dialogue); }
.ti-narration { background: rgba(139, 146, 160, 0.1); color: var(--color-narration); }
.ti-psy { background: rgba(212, 165, 116, 0.1); color: var(--color-psy); }

/* 内容区 */
.unit-body {
  font-size: 14px;
  line-height: 1.85;
  color: var(--text-primary);
  padding-left: 2px;
}

/* 台词样式 */
:deep(.dl-text) {
  color: var(--color-dialogue);
  font-weight: 500;
}
:deep(.dl-q) {
  font-family: Georgia, 'Noto Serif SC', serif;
  font-style: italic;
  font-size: 1.05em;
  color: rgba(126, 207, 153, 0.4);
}

/* 动作样式 */
:deep(.ac-text) {
  color: #9fc0ff;
  font-style: italic;
}

/* 旁白样式 */
:deep(.nr-text) {
  display: block;
  padding-left: 20px;
  color: var(--color-narration);
  font-size: 13px;
  position: relative;
}
:deep(.nr-text)::before {
  content: 'V.O.';
  position: absolute;
  left: 0;
  top: 0;
  font-size: 9px;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 1px;
  font-family: var(--font-ui);
}

/* 心理样式 */
:deep(.psy-text) {
  display: block;
  padding-left: 20px;
  color: var(--color-psy);
  font-style: italic;
  font-size: 13px;
  position: relative;
}
:deep(.psy-text)::before {
  content: '(内心)';
  position: absolute;
  left: 0;
  top: 0;
  font-size: 9px;
  font-weight: 700;
  color: rgba(212, 165, 116, 0.4);
  letter-spacing: 0.5px;
  font-family: var(--font-ui);
}
</style>
