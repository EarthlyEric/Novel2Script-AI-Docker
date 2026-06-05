<template>
  <div id="app-container">
    <!-- 背景装饰层：胶片穿孔 + 光晕 -->
    <div class="bg-layer">
      <div class="film-perforation left"></div>
      <div class="film-perforation right"></div>
      <div class="glow-orb glow-1"></div>
      <div class="glow-orb glow-2"></div>
    </div>

    <!-- 顶部导航 -->
    <header class="app-header">
      <div class="header-inner">
        <div class="brand" @click="$router.push('/')">
          <div class="brand-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <h1 class="brand-name">文剧智转</h1>
          <span class="brand-divider"></span>
          <span class="brand-sub">Novel to Script</span>
        </div>

        <!-- 面包屑 / 状态 -->
        <nav class="nav-status">
          <span
            v-for="(crumb, i) in breadcrumbs"
            :key="crumb.path"
            class="crumb"
            :class="{ active: $route.name === crumb.name }"
            @click="$router.push(crumb.path)"
          >
            {{ crumb.label }}
            <span v-if="i < breadcrumbs.length - 1" class="crumb-sep">/</span>
          </span>
        </nav>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

/** 动态面包屑 */
const breadcrumbs = computed(() => [
  { label: '上传', path: '/', name: 'home' },
  { label: '预览', path: '/preview', name: 'preview' },
  { label: '编辑', path: '/edit', name: 'edit' },
])
</script>

<style>
/* ============================================================
   全局设计变量 — 电影制片厂暗色主题
   ============================================================ */
:root {
  /* 核心色彩 */
  --bg-deep: #0a0a0c;
  --bg-base: #101014;
  --bg-elevated: #18181d;
  --bg-card: rgba(255, 255, 255, 0.03);
  --bg-card-hover: rgba(255, 255, 255, 0.06);
  --bg-glass: rgba(18, 18, 22, 0.75);

  /* 暖金色调色板 */
  --accent: #c9a227;
  --accent-light: #e8c547;
  --accent-dim: rgba(201, 162, 39, 0.15);
  --accent-glow: rgba(201, 162, 39, 0.25);

  /* 文字 */
  --text-primary: #ebeae6;
  --text-secondary: #9a9590;
  --text-muted: #605c58;

  /* 边框 & 分割 */
  --border-subtle: rgba(255, 255, 255, 0.06);
  --border-medium: rgba(255, 255, 255, 0.1);

  /* 单元类型色 */
  --color-action: #6b9fff;
  --color-dialogue: #7ecf99;
  --color-narration: #8b92a0;
  --color-psy: #d4a574;

  /* 场景类型 */
  --color-int: #e8a84c;
  --color-ext: #5eb8b8;

  /* 字体 */
  --font-display: 'Noto Serif SC', 'Songti SC', serif;
  --font-ui: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;

  /* 圆角 */
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 18px;

  /* 过渡 */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

/* 全局重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-ui);
  background-color: var(--bg-deep);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;
}

/* Element Plus 暗色覆盖 — 仅覆盖关键组件 */
.el-input__wrapper,
.el-textarea__inner {
  background-color: var(--bg-elevated) !important;
  box-shadow: 0 0 0 1px var(--border-medium) inset !important;
  color: var(--text-primary) !important;
  font-family: var(--font-ui) !important;
}
.el-input__wrapper:hover,
.el-textarea__inner:focus {
  box-shadow: 0 0 0 1px var(--accent) inset !important;
}
.el-input__inner::placeholder,
.el-textarea__inner::placeholder {
  color: var(--text-muted) !important;
}
.el-select .el-input__wrapper {
  background-color: var(--bg-elevated) !important;
}
.el-select-dropdown {
  background-color: var(--bg-elevated) !important;
  border: 1px solid var(--border-medium) !important;
}
.el-select-dropdown__item {
  color: var(--text-primary) !important;
}
.el-select-dropdown__item.hover,
.el-select-dropdown__item:hover {
  background-color: var(--accent-dim) !important;
}
.el-radio__label {
  color: var(--text-secondary) !important;
}
.el-radio__input.is-checked .el-radio__inner {
  background-color: var(--accent);
  border-color: var(--accent);
}
.el-divider__text {
  color: var(--text-secondary) !important;
  background-color: transparent !important;
}
.el-collapse-item__header {
  color: var(--text-secondary) !important;
  background: transparent !important;
  border-bottom: 1px solid var(--border-subtle) !important;
}
.el-collapse-item__content {
  background: transparent !important;
  color: var(--text-primary) !important;
}
.el-upload-dragger {
  background: var(--bg-card) !important;
  border: 1px dashed var(--border-medium) !important;
  color: var(--text-secondary) !important;
}
.el-upload-dragger:hover {
  border-color: var(--accent) !important;
}
.el-form-item__label {
  color: var(--text-secondary) !important;
  font-weight: 500 !important;
}
.el-descriptions__label {
  color: var(--text-muted) !important;
  background: var(--bg-card) !important;
}
.el-descriptions__content {
  color: var(--text-primary) !important;
  background: var(--bg-base) !important;
}
.el-button--primary {
  --el-button-bg-color: var(--accent) !important;
  --el-button-border-color: var(--accent) !important;
  --el-button-hover-bg-color: var(--accent-light) !important;
  --el-button-hover-border-color: var(--accent-light) !important;
  --el-button-text-color: #0a0a0c !important;
  font-weight: 600 !important;
}
.el-empty__description p {
  color: var(--text-muted) !important;
}
.el-card {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-primary) !important;
}
.el-card__header {
  border-bottom: 1px solid var(--border-subtle) !important;
  color: var(--text-primary) !important;
}
/* 页面切换动画 */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.35s var(--ease-out), transform 0.35s var(--ease-out);
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

<style scoped>
#app-container {
  min-height: 100vh;
  position: relative;
}

/* ====== 背景装饰层 ====== */
.bg-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.film-perforation {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 32px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 20px 0;
  justify-content: flex-start;
  align-content: center;
}
.film-perforation.left {
  left: 10px;
}
.film-perforation.right {
  right: 10px;
}
.film-perforation::before,
.film-perforation::after {
  content: '';
  display: block;
  width: 14px;
  height: 14px;
  margin: 0 auto;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.04);
  box-shadow:
    0 36px 0 rgba(255, 255, 255, 0.04),
    0 72px 0 rgba(255, 255, 255, 0.04),
    0 108px 0 rgba(255, 255, 255, 0.04),
    0 144px 0 rgba(255, 255, 255, 0.04),
    0 180px 0 rgba(255, 255, 255, 0.04),
    0 216px 0 rgba(255, 255, 255, 0.04),
    0 252px 0 rgba(255, 255, 255, 0.04),
    0 288px 0 rgba(255, 255, 255, 0.04),
    0 324px 0 rgba(255, 255, 255, 0.04),
    0 360px 0 rgba(255, 255, 255, 0.04),
    0 396px 0 rgba(255, 255, 255, 0.04),
    0 432px 0 rgba(255, 255, 255, 0.04),
    0 468px 0 rgba(255, 255, 255, 0.04),
    0 504px 0 rgba(255, 255, 255, 0.04),
    0 540px 0 rgba(255, 255, 255, 0.04),
    0 576px 0 rgba(255, 255, 255, 0.04),
    0 612px 0 rgba(255, 255, 255, 0.04),
    0 648px 0 rgba(255, 255, 255, 0.04),
    0 684px 0 rgba(255, 255, 255, 0.04),
    0 720px 0 rgba(255, 255, 255, 0.04),
    0 756px 0 rgba(255, 255, 255, 0.04);
}

.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.15;
}
.glow-1 {
  width: 500px;
  height: 500px;
  top: -150px;
  right: -100px;
  background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
}
.glow-2 {
  width: 400px;
  height: 400px;
  bottom: -100px;
  left: -80px;
  background: radial-gradient(circle, #3a5a80 0%, transparent 70%);
}

/* ====== 顶部导航栏 ====== */
.app-header {
  position: relative;
  z-index: 50;
  backdrop-filter: blur(20px) saturate(1.4);
  background: rgba(10, 10, 12, 0.75);
  border-bottom: 1px solid var(--border-subtle);
}

.header-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 56px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: opacity 0.2s;
}
.brand:hover {
  opacity: 0.85;
}

.brand-icon {
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-name {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--text-primary);
}

.brand-divider {
  width: 1px;
  height: 18px;
  background: linear-gradient(to bottom, transparent, var(--border-medium), transparent);
}

.brand-sub {
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--text-muted);
}

.nav-status {
  display: flex;
  gap: 4px;
  font-size: 13px;
}

.crumb {
  cursor: pointer;
  color: var(--text-muted);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}
.crumb:hover {
  color: var(--text-secondary);
  background: var(--bg-card);
}
.crumb.active {
  color: var(--accent);
  font-weight: 600;
}
.crumb-sep {
  color: var(--border-medium);
  margin: 0 2px;
  font-size: 10px;
}

/* ====== 主内容区域 ====== */
.app-main {
  position: relative;
  z-index: 1;
  max-width: 1100px;
  margin: 0 auto;
  padding: 40px 56px 80px;
}
</style>
