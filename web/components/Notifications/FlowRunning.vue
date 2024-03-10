<script setup lang="ts">
const flowStore = useFlowsStore()
</script>

<template>
	<div v-for="runningFlow in flowStore.running"
		class="mb-3 last:mb-0">
		Flow
		<NuxtLink :to="`/workflows/${runningFlow.flow_name}`">
			<UBadge class="mx-1"
				color="white"
				variant="solid">
				{{ flowStore.flowByName(runningFlow.flow_name)?.display_name }}
			</UBadge>
		</NuxtLink>
		is running
		<UBadge class="mx-1"
			color="white"
			variant="solid">
			{{ runningFlow.progress.toFixed(0) }}%
		</UBadge>
	</div>
</template>
