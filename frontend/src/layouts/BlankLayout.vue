<template>
  <div class="blank-layout">
    <router-view v-slot="{ Component }">
      <transition name="fade-up" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<style scoped lang="scss">
.blank-layout {
  width: 100%;
  min-height: 100vh;
}

.fade-up-enter-active,
.fade-up-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
