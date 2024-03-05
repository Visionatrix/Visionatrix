<script setup lang="ts">
const flowStore = useFlowsStore()
</script>

<template>
	<div v-for="installingFlow in flowStore.installing"
		class="mb-3 last:mb-0 border-b p-3">
		{{ installingFlow.progress.toFixed(0) }}% Setting up flow
		<NuxtLink :to="`/workflows/${installingFlow.flow_name}`">
			<UBadge class="mx-1"
				color="white"
				variant="solid">
				{{ flowStore.flowByName(installingFlow.flow_name)?.display_name }}
			</UBadge>
		</NuxtLink>
	</div>
</template>
