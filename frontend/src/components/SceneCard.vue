<template>
  <div class="scene-card" :class="{ expanded: isExpanded }">
    <!-- 胶片条装饰顶部 -->
    <div class="film-strip-top"></div>

    <!-- 场次头部 -->
    <div class="scene-header" @click="toggleExpand">
      <div class="header-left">
        <span class="serial-number">{{ scene.scene_serial }}</span>
        <div class="attr-badges">
          <span class="badge int" v-if="scene.scene_attr.scene_type === '内景'">INT.</span>
          <span class="badge ext" v-else>EXT.</span>
          <span class="badge time">{{ scene.scene_attr.time_type }}</span>
        </div>
        <span class="location-name">{{ scene.scene_attr.location }}</span>
      </div>
      <div class="header-right">
        <span class="unit-count-label">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/></svg>
          {{ scene.scene_content.length }}
        </span>
        <span class="expand-chevron" :class="{ open: isExpanded }">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
        </span>
      </div>
    </div>

    <!-- 场次概要（始终显示） -->
    <p class="scene-summary">{{ scene.scene_summary }}</p>

    <!-- 展开内容 -->
    <transition name="scene-expand">
      <div v-show="isExpanded" class="scene-body">
        <div class="body-divider"></div>

        <div class="units-container">
          <UnitItem
            v-for="(unit, idx) in scene.scene_content"
            :key="unit.unit_id"
            :unit="unit"
            :index="idx"
          />

          <div v-if="!scene.scene_content.length" class="empty-units">
            <span>暂无剧情单元</span>
          </div>
        </div>

        <!-- 场次备注 -->
        <div v-if="scene.scene_note" class="scene-note">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          {{ scene.scene_note }}
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ScriptScene } from '@/types/script'
import UnitItem from '@/components/UnitItem.vue'

const props = defineProps<{
  scene: ScriptScene
  index?: number
}>()

const isExpanded = ref(true)

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}
</script>

<style scoped>
.scene-card {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: box-shadow 0.35s var(--ease-out), transform 0.25s var(--ease-out);
  animation: cardReveal 0.45s var(--ease-out) both;
  animation-delay: calc((props.index || 0) * 0.06s);
}
@keyframes cardReveal {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.scene-card:hover {
  box-shadow:
    0 4px 24px rgba(0, 0, 0, 0.2),
    0 0 60px -20px var(--accent-glow);
  transform: translateY(-2px);
}

/* 胶片条装饰 */
.film-strip-top {
  height: 3px;
  background: linear-gradient(
    90deg,
    var(--color-int) 0%,
    var(--color-dialogue) 33%,
    var(--color-action) 66%,
    var(--color-psy) 100%
  );
  opacity: 0.6;
}

/* 头部 */
.scene-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px 14px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}
.scene-header:hover {
  background: var(--bg-card-hover);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.serial-number {
  font-family: var(--font-ui);
  font-size: 15px;
  font-weight: 900;
  color: var(--accent);
  letter-spacing: -0.5px;
  padding: 3px 12px;
  background: var(--accent-dim);
  border-radius: 6px;
  line-height: 1;
}

.attr-badges {
  display: flex;
  gap: 5px;
}

.badge {
  font-family: var(--font-ui);
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
}
.badge.int { background: rgba(232, 168, 76, 0.12); color: var(--color-int); }
.badge.ext { background: rgba(94, 184, 184, 0.12); color: var(--color-ext); }
.badge.time { background: var(--bg-elevated); color: var(--text-muted); }

.location-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.5px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-muted);
}

.unit-count-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-ui);
}

.expand-chevron {
  display: flex;
  align-items: center;
  transition: transform 0.3s var(--ease-out);
}
.expand-chevron.open {
  transform: rotate(180deg);
}

/* 概要 */
.scene-summary {
  margin: 0 22px 0;
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary);
  border-left: 2px solid var(--border-medium);
}

/* 展开/收起动画 */
.scene-expand-enter-active {
  transition: all 0.35s var(--ease-out);
  overflow: hidden;
}
.scene-expand-leave-active {
  transition: all 0.25s ease-in;
  overflow: hidden;
}
.scene-expand-enter-from,
.scene-expand-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.scene-body {
  padding: 0 22px 18px;
}

.body-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-medium), transparent);
  margin-bottom: 16px;
}

.units-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.empty-units {
  text-align: center;
  padding: 16px 0;
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
}

/* 备注 */
.scene-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 16px;
  background: rgba(232, 168, 76, 0.04);
  border: 1px solid rgba(232, 168, 76, 0.1);
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.7;
  color: var(--accent-light);
  opacity: 0.85;
}
.scene-note svg {
  flex-shrink: 0;
  margin-top: 2px;
  opacity: 0.6;
}
</style>
