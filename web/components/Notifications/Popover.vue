<script setup lang="ts">
const flowStore = useFlowsStore()
const noNotifications = computed(() => flowStore.running.filter((running: FlowRunning) => !running.hidden || (running.hidden && flowStore.$state.flows_hidden_filter)).length === 0 && flowStore.installing.length === 0)
</script>

<template>
	<UPopover :popper="{ placement: 'top-end' }">
		<UChip :show="flowStore.showNotificationChip" @click="() => flowStore.showNotificationChip = false">
			<UButton
				icon="i-heroicons-bell-solid"
				variant="ghost"
				color="white"
				class="text-black dark:text-white hover:bg-transparent lg:px-3 py-2" />
		</UChip>

		<template #panel>
			<div class="p-4 min-w-52 max-h-52 overflow-auto">
				<NotificationsFlowRunning v-if="flowStore.running.filter((running: FlowRunning) => !running.hidden || (running.hidden && flowStore.$state.flows_hidden_filter)).length > 0" />
				<NotificationsFlowInstalling v-if="flowStore.installing.length > 0" />

				<p v-if="noNotifications" class="text-sm text-slate-500">No notifications available</p>
			</div>
		</template>
	</UPopover>
</template>
