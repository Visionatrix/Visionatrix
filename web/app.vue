<script lang="ts" setup>
useFlowsStore().fetchFlows()
</script>

<template>
  <div>
    <div class="flex flex-col w-full h-screen justify-between">
      <NuxtLoadingIndicator />
      <Navbar />
      <NuxtPage class="w-full min-h-vh py-1.5 z-10" />
    </div>
    <UNotifications class="z-5" />
  </div>
</template>

<style>
.page-enter-active,
.page-leave-active {
  transition: all 0.1s;
}
.page-enter-from,
.page-leave-to {
  opacity: 0;
  filter: blur(1rem);
}
</style>
