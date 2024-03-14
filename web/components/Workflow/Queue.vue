<script setup lang="ts">
const flowStore = useFlowsStore()

const canceling = ref(false)
const collapsed = ref(true)
</script>

<template>
	<div class="w-full p-4 ring-1 ring-gray-200 dark:ring-gray-800 rounded-lg shadow-md mt-5 mb-10">
		<div class="flex items-center justify-between">
			<h2 class="text-lg font-bold cursor-pointer select-none flex items-center" @click="() => {
				collapsed = !collapsed
			}">
				<UIcon :name="collapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
					class="mr-2" />
				Queue ({{ flowStore.flowsRunningByName(flowStore.currentFlow?.name).length }})
			</h2>
			<UButton v-if="flowStore.currentFlow?.name && flowStore.flowsRunningByName(flowStore.currentFlow?.name).length > 0"
				icon="i-heroicons-x-mark"
				variant="outline"
				:loading="canceling"
				@click="() => {
					canceling = true
					flowStore.cancelRunningFlows(flowStore.flowsRunningByName(flowStore.currentFlow?.name)).finally(() => {
						canceling = false
					})
				}"
				>Cancel all</UButton>
		</div>
		<div v-if="!collapsed"
			v-for="running in flowStore.flowsRunningByName(flowStore.currentFlow?.name)"
			class="mb-5">
			<UProgress class="mb-3" :value="running?.progress" indicator />
			<p class="text-sm mb-5 text-slate-500">{{ running.input_prompt }}</p>
			<UButton icon="i-heroicons-x-mark"
				variant="outline"
				:loading="canceling"
				@click="() => {
					canceling = true
					flowStore.cancelRunningFlow(running).finally(() => {
						canceling = false
					})
				}"
				>Cancel</UButton>
		</div>
	</div>
</template>

<style scoped>
.progress-queue {
	height: 100%;
	max-height: 25dvh;
	overflow-y: auto;
}
</style>
