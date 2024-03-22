<script setup lang="ts">
const systemStore = useSystemStore()
</script>

<template>
	<div v-if="'devices' in systemStore.$state.stats" class="flex absolute w-full top-0">
		<span class="transition-all bg-neutral-400 dark:bg-neutral-600 h-1 rounded-lg" :style="{
			width: `${systemStore.gpusVramUsage.vram_free / systemStore.gpusVramUsage.vram_total * 100}%`
		}" :title="`VRAM usage: ${systemStore.gpusVramUsage.vram_free}/${systemStore.gpusVramUsage.vram_total}`" />
	</div>
</template>
