<script setup lang="ts">
const colorMode = useColorMode()
const isDark = computed({
  get() {
    return colorMode.value === 'dark'
  },
  set() {
    colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
  }
})

const themingToggleIconClass = computed(() => {
  return isDark.value ? 'i-heroicons-moon-solid' : 'i-heroicons-sun-solid'
})
</script>

<template>
  <AppContainer class="w-full z-[60]">
    <header class="flex w-full flex-col lg:flex-row justify-between items-center my-5">
      <div class="flex w-full items-center justify-between">
        <ULink to="/" class="text-lg mr-3">
          <span class="font-bold text-neutral-400 hover:text-neutral-300 mr-1">Visionatrix</span>
        </ULink>
        <div class="flex items-center">
          <NotificationsPopover />

          <UButton :icon="themingToggleIconClass"
            variant="ghost"
            color="white"
            class="flex lg:px-3 py-2 text-black dark:text-white hover:bg-transparent"
          @click="isDark = !isDark" />
        </div>
      </div>
    </header>
  </AppContainer>
</template>
