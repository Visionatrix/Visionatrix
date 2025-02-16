<script lang="ts" setup>
useSettingsStore().loadLocalSettings()
useSettingsStore().fetchAllSettings()
useFlowsStore().fetchFlows()
useWorkersStore().loadWorkers()

const config = useRuntimeConfig()
if (config.app.isNextcloudIntegration) {
	useNextcloudStore().registerListener()
}
</script>

<template>
	<div class="flex flex-col w-full h-screen">
		<Navbar />
		<NuxtPage class="w-full min-h-vh py-1.5 z-10" />
	</div>
	<UNotifications />
</template>
