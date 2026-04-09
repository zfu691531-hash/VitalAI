import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getRoleHome } from '@/utils/role-ui'
import routes from './routes'

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

const whiteList = ['/login', '/403', '/404']

router.beforeEach(async (to) => {
  const userStore = useUserStore()
  const isLoggedIn = !!userStore.token

  document.title = to.meta.title ? `${to.meta.title} - 校园AI教务助手` : '校园AI教务助手'

  if (whiteList.includes(to.path)) {
    if (to.path === '/login' && isLoggedIn) {
      try {
        if (!userStore.role) {
          await userStore.fetchUserInfo()
        }
      } catch {
        userStore.logout()
        return '/login'
      }

      return getRoleHome(userStore.role)
    }

    return true
  }

  if (!isLoggedIn) {
    return {
      path: '/login',
      query: to.fullPath && to.fullPath !== '/dashboard'
        ? { redirect: to.fullPath }
        : undefined
    }
  }

  try {
    if (!userStore.role) {
      await userStore.fetchUserInfo()
    }
  } catch {
    userStore.logout()
    return '/login'
  }

  const homePath = getRoleHome(userStore.role)
  const requiredRoles = to.meta?.requiredRoles || []

  if (requiredRoles.length > 0 && !requiredRoles.includes(userStore.role)) {
    return homePath
  }

  if (to.path === '/') {
    return homePath
  }

  return true
})

export default router
