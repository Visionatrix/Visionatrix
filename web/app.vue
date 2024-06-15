<script lang="ts" setup>
useSettingsStore().loadSettings()
useFlowsStore().fetchFlows()
useWorkersStore().startPolling()
</script>

<template>
	<div class="flex flex-col w-full h-screen">
		<Navbar />
		<NuxtPage class="w-full min-h-vh py-1.5 z-10" />
	</div>
	<UNotifications class="z-5" />
</template>
