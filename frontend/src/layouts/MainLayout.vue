<template>
  <el-container class="main-layout" :style="layoutVars">
    <el-aside :width="isCollapse ? '72px' : '236px'" class="sidebar">
      <div class="logo">
        <img v-if="!isCollapse" src="@/assets/logo.svg" alt="logo" class="logo-img" />
        <div v-if="!isCollapse" class="logo-copy">
          <span class="logo-text">校园AI教务助手</span>
          <span class="logo-role">{{ roleUi.name }}端</span>
        </div>
        <span v-else class="logo-mini">AI</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        class="sidebar-menu"
      >
        <template v-for="item in menuList" :key="item.path">
          <el-sub-menu
            v-if="item.children && item.children.length > 0"
            :index="resolveMenuPath(item.path)"
          >
            <template #title>
              <el-icon><component :is="resolveMenuIcon(item.meta?.icon)" /></el-icon>
              <span>{{ item.meta?.title }}</span>
            </template>
            <el-menu-item
              v-for="child in item.children"
              :key="child.path"
              :index="resolveMenuPath(item.path, child.path)"
              v-show="!child.meta?.hidden"
            >
              <el-icon><component :is="resolveMenuIcon(child.meta?.icon)" /></el-icon>
              <span>{{ child.meta?.title }}</span>
            </el-menu-item>
          </el-sub-menu>

          <el-menu-item v-else :index="resolveMenuPath(item.path)">
            <el-icon><component :is="resolveMenuIcon(item.meta?.icon)" /></el-icon>
            <span>{{ item.meta?.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <button type="button" class="collapse-btn" @click="toggleCollapse">
            <el-icon>
              <Fold v-if="!isCollapse" />
              <Expand v-else />
            </el-icon>
          </button>

          <div class="breadcrumb-box">
            <span class="breadcrumb-kicker">{{ roleUi.name }}端工作台</span>
            <el-breadcrumb separator="/">
              <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
                {{ item.title }}
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </div>

        <div class="header-right">
          <div class="header-tip">欢迎回来，{{ roleUi.name }}</div>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="36" :icon="UserFilled" />
              <span class="username">{{ userStore.name || userStore.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>个人中心
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
      <AssistantWidget />
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Avatar,
  Calendar,
  ChatDotSquare,
  CollectionTag,
  Document,
  DocumentCopy,
  EditPen,
  Expand,
  Fold,
  Grid,
  HomeFilled,
  MagicStick,
  Menu,
  Microphone,
  Notebook,
  QuestionFilled,
  School,
  SwitchButton,
  TrendCharts,
  User,
  UserFilled
} from '@element-plus/icons-vue'
import AssistantWidget from '@/components/assistant/AssistantWidget.vue'
import { useUserStore } from '@/stores/user'
import { getRoleUi } from '@/utils/role-ui'
import routes from '@/router/routes'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const iconMap = {
  HomeFilled,
  User,
  Avatar,
  School,
  Document,
  MagicStick,
  EditPen,
  ChatDotSquare,
  CollectionTag,
  DocumentCopy,
  QuestionFilled,
  TrendCharts,
  Calendar,
  Microphone,
  Grid,
  Notebook
}

const isCollapse = ref(false)

const roleUi = computed(() => getRoleUi(userStore.role))

const layoutVars = computed(() => ({
  '--layout-shell-start': roleUi.value.layout.shellStart,
  '--layout-shell-end': roleUi.value.layout.shellEnd,
  '--layout-sidebar-start': roleUi.value.layout.sidebarStart,
  '--layout-sidebar-end': roleUi.value.layout.sidebarEnd,
  '--layout-sidebar-overlay': roleUi.value.layout.sidebarOverlay,
  '--layout-accent-soft': roleUi.value.layout.accentSoft,
  '--layout-accent-strong': roleUi.value.layout.accentStrong,
  '--layout-accent-text': roleUi.value.layout.accentText,
  '--layout-icon-color': roleUi.value.layout.iconColor
}))

const activeMenu = computed(() => route.path)

const breadcrumbs = computed(() =>
  route.matched
    .filter((item) => item.meta?.title)
    .map((item) => ({
      path: item.path,
      title: item.meta?.title
    }))
)

const menuList = computed(() => {
  const userRole = userStore.role

  const filterMenus = (menus) =>
    menus
      .filter((menu) => {
        if (menu.meta?.hidden) return false

        const requiredRoles = menu.meta?.requiredRoles
        if (!requiredRoles || requiredRoles.length === 0) return true
        return requiredRoles.includes(userRole)
      })
      .map((menu) => ({
        ...menu,
        children: menu.children ? filterMenus(menu.children) : menu.children
      }))
      .filter((menu) => !(menu.children && menu.children.length === 0))

  const mainRoute = routes.find((item) => item.path === '/')
  return mainRoute ? filterMenus(mainRoute.children || []) : []
})

function resolveMenuIcon(name) {
  return iconMap[name] || Menu
}

function resolveMenuPath(parentPath, childPath = '') {
  const segments = [parentPath, childPath]
    .filter(Boolean)
    .flatMap((segment) => String(segment).split('/'))
    .map((segment) => segment.trim())
    .filter(Boolean)

  return `/${segments.join('/')}`
}

function toggleCollapse() {
  isCollapse.value = !isCollapse.value
}

function handleCommand(command) {
  if (command === 'profile') {
    router.push('/profile')
  }

  if (command === 'logout') {
    userStore.logout()
  }
}
</script>

<style scoped lang="scss">
.main-layout {
  height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.66), transparent 20%),
    linear-gradient(180deg, var(--layout-shell-start) 0%, var(--layout-shell-end) 100%);
}

.sidebar {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  background:
    linear-gradient(180deg, var(--layout-sidebar-start) 0%, var(--layout-sidebar-end) 100%);
  border-right: 1px solid rgba(117, 152, 196, 0.14);
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.45);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 74px;
  padding: 0 18px;
  background: var(--layout-sidebar-overlay);
  border-bottom: 1px solid rgba(117, 152, 196, 0.12);
  backdrop-filter: blur(14px);
}

.logo-img {
  width: 38px;
  height: 38px;
  padding: 7px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--layout-accent-strong), color-mix(in srgb, var(--layout-accent-strong) 50%, white));
  box-shadow: 0 14px 28px color-mix(in srgb, var(--layout-accent-strong) 20%, transparent);
}

.logo-copy {
  display: flex;
  flex-direction: column;
}

.logo-text {
  color: var(--layout-accent-text);
  font-size: 17px;
  font-weight: 700;
}

.logo-role {
  margin-top: 4px;
  color: rgba(38, 61, 92, 0.58);
  font-size: 12px;
  font-weight: 600;
}

.logo-mini {
  color: var(--layout-accent-text);
  font-size: 22px;
  font-weight: 700;
  margin: 0 auto;
}

.sidebar-menu {
  padding: 16px 10px 18px;
  border-right: none;
  background: transparent;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;

  &:not(.el-menu--collapse) {
    width: 236px;
  }
}

.sidebar :deep(.el-menu) {
  background: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: #4f6680;
  --el-menu-hover-bg-color: var(--layout-accent-soft);
  --el-menu-active-color: var(--layout-accent-strong);
  --el-menu-hover-text-color: var(--layout-accent-text);
}

.sidebar :deep(.el-menu-item),
.sidebar :deep(.el-sub-menu__title) {
  height: 48px;
  margin-bottom: 8px;
  border-radius: 16px;
  font-weight: 600;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.sidebar :deep(.el-menu-item:hover),
.sidebar :deep(.el-sub-menu__title:hover) {
  transform: translateX(2px);
  background: var(--layout-accent-soft);
  color: var(--layout-accent-text);
}

.sidebar :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, var(--layout-accent-soft), rgba(255, 255, 255, 0.6));
  color: var(--layout-accent-strong);
  box-shadow: 0 14px 28px color-mix(in srgb, var(--layout-accent-strong) 10%, transparent);
}

.sidebar :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  background: var(--layout-accent-soft);
  color: var(--layout-accent-text);
}

.sidebar :deep(.el-sub-menu .el-menu-item) {
  margin-left: 8px;
}

.sidebar :deep(.el-menu-item [class^='el-icon']),
.sidebar :deep(.el-sub-menu__title [class^='el-icon']) {
  color: var(--layout-icon-color);
}

.sidebar :deep(.el-menu-item.is-active [class^='el-icon']) {
  color: var(--layout-accent-strong);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 22px;
  background: rgba(255, 255, 255, 0.82);
  border-bottom: 1px solid rgba(117, 152, 196, 0.12);
  box-shadow: 0 10px 26px rgba(30, 61, 98, 0.05);
  backdrop-filter: blur(14px);
}

.header-left,
.header-right,
.user-info {
  display: flex;
  align-items: center;
}

.header-left {
  gap: 16px;
}

.header-right {
  gap: 16px;
}

.collapse-btn {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 14px;
  background: color-mix(in srgb, var(--layout-accent-strong) 9%, white);
  color: var(--layout-accent-strong);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 12px 26px color-mix(in srgb, var(--layout-accent-strong) 12%, transparent);
  }
}

.breadcrumb-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.breadcrumb-kicker {
  color: rgba(39, 60, 88, 0.58);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.header-tip {
  padding: 10px 14px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--layout-accent-strong) 8%, white);
  color: var(--layout-accent-text);
  font-size: 13px;
  font-weight: 600;
}

.user-info {
  gap: 10px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 10px 22px rgba(30, 61, 98, 0.06);
  cursor: pointer;
}

.username {
  color: #4e6073;
  font-weight: 600;
}

.main-content {
  padding: 18px;
  overflow-y: auto;
  background: transparent;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 900px) {
  .header {
    padding: 0 14px;
  }

  .header-tip {
    display: none;
  }
}
</style>
