<script setup lang="ts">
const flowStore = useFlowsStore()
</script>

<template>
	<div v-for="installingFlow in flowStore.installing"
		:key="installingFlow.flow_name"
		class="mb-3 last:mb-0 border-b p-3 flex items-center">
		<template v-if="installingFlow.error === ''">
			<UIcon name="i-heroicons-arrow-down-tray-solid" class="mx-1" />
			{{ installingFlow.progress.toFixed(0) }}% Setting up flow
			<NuxtLink :to="`/workflows/${installingFlow.flow_name}`">
				<UBadge class="mx-1"
					color="white"
					variant="solid">
					{{ flowStore.flowByName(installingFlow.flow_name)?.display_name }}
				</UBadge>
			</NuxtLink>
		</template>
		<template v-else>
			<UIcon name="i-heroicons-exclamation-circle" class="mx-1" />
			Error setting up flow
			<NuxtLink :to="`/workflows/${installingFlow.flow_name}`">
				<UBadge class="mx-1"
					color="white"
					variant="solid">
					{{ flowStore.flowByName(installingFlow.flow_name)?.display_name }}
				</UBadge>
			</NuxtLink>
		</template>
	</div>
</template>
