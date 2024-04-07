<script setup lang="ts">
const flowStore = useFlowsStore()

const canceling = ref(false)
const restarting = ref(false)
const collapsed = ref(true)
</script>

<template>
	<div class="w-full p-4 ring-1 ring-gray-200 dark:ring-gray-800 rounded-lg shadow-md mt-5 mb-10">
		<div class="flex items-center justify-between mb-2">
			<h2 class="text-lg font-bold cursor-pointer select-none flex items-center" @click="() => {
				collapsed = !collapsed
			}">
				<UIcon :name="collapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
					class="mr-2" />
				<span>
					Queue ({{ flowStore.flowsRunningByName(flowStore.currentFlow?.name).length }})
				</span>
				<span v-if="flowStore.flowsRunningByName(flowStore.currentFlow?.name).length > 0">
					&nbsp;-
					{{
						`${flowStore.flowsRunningByName(flowStore.currentFlow?.name)
						.filter((running) => running.progress > 0)[0]?.progress.toFixed(0) ?? 0}%`
					}}
				</span>
				<template v-if="flowStore.flowsRunningByNameWithErrors(flowStore?.currentFlow.name).length > 0">
					<span class="text-red-400">
						&nbsp;({{ flowStore.flowsRunningByNameWithErrors(flowStore.currentFlow?.name).length }})
					</span>
				</template>
			</h2>
			<UButton v-if="flowStore.currentFlow?.name && flowStore.flowsRunningByName(flowStore.currentFlow?.name).length > 0"
				icon="i-heroicons-stop"
				color="orange"
				variant="outline"
				:loading="canceling"
				@click="() => {
					canceling = true
					flowStore.cancelRunningFlows(flowStore.currentFlow?.name).finally(() => {
						canceling = false
					})
				}"
				>Cancel all</UButton>
		</div>
		<div v-if="!collapsed"
			v-for="running in flowStore.flowsRunningByName(flowStore.currentFlow?.name)"
			class="mb-5">
			<UProgress class="mb-3" :value="running?.progress" indicator :color="!running.error ? 'green' : 'red'"/>
			<p class="text-sm mb-5 text-slate-500">
				{{
					Object.keys(running.input_params_mapped)
						.filter((key) => {
							return running.input_params_mapped[key] !== ''
						})
						.map((key) => {
							return `${key}: ${running.input_params_mapped[key]}`
						}).join(' | ')
				}}
			</p>
			<p v-if="running.error" class="text-red-500 p-3 mb-5 rounded-lg flex items-center overflow-x-auto">
				<UIcon name="i-heroicons-exclamation-circle" class="mr-2 text-3xl" />
				<span class="w-full">{{ running.error }}</span>
			</p>
			<UButton icon="i-heroicons-stop"
				color="orange"
				variant="outline"
				:loading="canceling"
				@click="() => {
					canceling = true
					flowStore.cancelRunningFlow(running).finally(() => {
						canceling = false
					})
				}"
				>Cancel</UButton>
			<UButton v-if="running.error"
				class="ml-2"
				icon="i-heroicons-arrow-path"
				variant="outline"
				:loading="restarting"
				@click="() => {
					restarting = true
					flowStore.restartFlow(running).finally(() => {
						restarting = false
					})
				}">
				Restart</UButton>
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
