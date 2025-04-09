<script setup lang="ts">
const flowStore = useFlowsStore()

const running = computed(() => flowStore.running.reduce((running, runningFlow) => {
	// Always hide federated tasks
	if (runningFlow?.extra_flags?.federated_task === true) {
		return running
	}

	if (!running[runningFlow.flow_name]) {
		// Show if not hidden OR if hidden but the global filter is enabled
		if (!runningFlow.hidden || (runningFlow.hidden && flowStore.$state.flows_hidden_filter)) {
			running[runningFlow.flow_name] = []
		}
	}

	// Add to the list if not hidden OR if hidden but the global filter is enabled
	if (!runningFlow.hidden || (runningFlow.hidden && flowStore.$state.flows_hidden_filter)) {
		// Check again if the flow_name key exists (it might not if the first item was hidden and filter is off)
		if (running[runningFlow.flow_name]) {
			running[runningFlow.flow_name].push(runningFlow)
		}
	}
	return running
}, {} as any))
</script>

<template>
	<div
		v-for="flow_name in Object.keys(running)"
		:key="flow_name"
		class="mb-3 last:mb-0">
		<span>({{ running[flow_name].length }})</span>
		Flow
		<NuxtLink :to="`/workflows/${flow_name}`">
			<UBadge
				class="mx-1"
				color="white"
				variant="solid">
				{{ flowStore.flowByName(flow_name)?.display_name }}
			</UBadge>
		</NuxtLink>
		is running
		<UBadge
			class="mx-1"
			color="white"
			variant="solid">
			{{ running[flow_name].filter((r: FlowRunning) => r.progress > 0)[0]?.progress.toFixed(0) || 0 }}%
		</UBadge>
		<span v-if="running[flow_name].filter((r: FlowRunning) => r.error).length > 0" class="text-red-500">
			({{ running[flow_name].filter((r: FlowRunning) => r.error).length }})
		</span>
	</div>
</template>
