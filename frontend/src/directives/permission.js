/**
 * v-permission 自定义指令
 * ========================
 * 按钮级权限控制指令。
 *
 * 用法: <el-button v-permission="['admin']">仅管理员可见</el-button>
 *
 * 逻辑:
 * - 绑定值: 允许访问的角色列表
 * - 如果当前用户角色不在列表中，自动移除该DOM元素
 * - 在mounted时判断权限
 */
import { useUserStore } from '@/stores/user'

export const permission = {
  mounted(el, binding) {
    const userStore = useUserStore()
    const userRole = userStore.role
    const allowedRoles = binding.value

    // 如果没有传入角色列表，默认显示
    if (!allowedRoles || !Array.isArray(allowedRoles)) {
      return
    }

    // 如果用户角色不在允许列表中，移除元素
    if (!allowedRoles.includes(userRole)) {
      el.parentNode?.removeChild(el)
    }
  }
}
