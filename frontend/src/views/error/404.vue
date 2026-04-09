<template>
  <div class="error-page">
    <h1>404</h1>
    <p>你访问的页面不存在。</p>
    <el-button type="primary" @click="$router.push('/dashboard')">返回首页</el-button>
  </div>
</template>

<style scoped lang="scss">
.error-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: linear-gradient(180deg, #f7fbff 0%, #eef4fb 100%);

  h1 {
    font-size: 84px;
    line-height: 1;
    color: #2f5b9a;
  }

  p {
    color: #4e6073;
    font-size: 16px;
  }
}
</style>
