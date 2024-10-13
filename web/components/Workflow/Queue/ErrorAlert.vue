<script setup lang="ts">
defineProps({
	running: {
		type: Object as () => FlowRunning,
		required: true,
	},
})

const flowStore = useFlowsStore()
const restarting = ref(false)
</script>

<template>
	<UAlert
		class="mb-5"
		icon="i-heroicons-exclamation-circle-16-solid"
		color="red"
		variant="soft"
		:title="'Task failed'"
		:description="running.error"
		:actions="[
			{
				variant: 'outline',
				color: 'yellow',
				label: 'Restart',
				loading: restarting,
				icon: 'i-heroicons-arrow-path', click: () => {
					restarting = true
					flowStore.restartFlow($props.running).finally(() => {
						restarting = false
					})
				}
			},
		]" />
</template>
