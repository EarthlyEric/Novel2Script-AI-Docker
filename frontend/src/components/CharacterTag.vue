<template>
  <span class="char-tag" :class="[sizeClass]">
    <span class="char-name">{{ name }}</span>
    <span v-if="profile" class="char-info-trigger" :title="profile">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  name: string
  profile?: string
  size?: 'default' | 'small'
}>(), {
  profile: '',
  size: 'default',
})

const sizeClass = computed(() => props.size === 'small' ? 'size-small' : 'size-default')
</script>

<style scoped>
.char-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 14px 5px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-ui);
  letter-spacing: 0.3px;
  white-space: nowrap;
  position: relative;
  transition: all 0.2s var(--ease-out);
  /* 默认渐变背景 — 根据名称哈希生成微妙色彩变化 */
  background: linear-gradient(
    135deg,
    rgba(201, 162, 39, 0.08) 0%,
    rgba(107, 159, 255, 0.06) 50%,
    rgba(126, 207, 153, 0.07) 100%
  );
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}

.char-tag:hover {
  background: linear-gradient(
    135deg,
    rgba(201, 162, 39, 0.14) 0%,
    rgba(107, 159, 255, 0.1) 50%,
    rgba(126, 207, 153, 0.12) 100%
  );
  border-color: var(--border-medium);
  color: var(--text-primary);
  transform: scale(1.03);
}

.char-name {
  font-weight: 600;
  color: inherit;
}

.char-info-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-muted);
  cursor: help;
  transition: all 0.2s;
  opacity: 0.5;
}
.char-tag:hover .char-info-trigger {
  opacity: 1;
  color: var(--accent);
  background: var(--accent-dim);
}

/* 小尺寸 */
.size-small {
  padding: 2px 9px 2px 8px;
  font-size: 11px;
  border-radius: 99px;
}
.size-small .char-info-trigger {
  width: 13px;
  height: 13px;
}
</style>
