<script lang="ts" setup>
useSettingsStore().loadSettings()
useFlowsStore().fetchFlows()
useWorkersStore().loadWorkers()
</script>

<template>
	<div class="flex flex-col w-full h-screen">
		<NavBar />
		<NuxtPage class="w-full min-h-vh py-1.5 z-10" />
	</div>
	<UNotifications
		:ui="{
			wrapper: 'fixed flex flex-col justify-end z-[55] pointer-events-none',
			position: 'bottom-0 end-0',
			width: 'w-full sm:w-96',
			container: 'px-4 sm:px-6 py-6 space-y-3 overflow-y-auto',
		}" />
</template>
