<script setup lang="ts">
const flowStore = useFlowsStore()
const collapsed = ref(true)
const canceling = ref(false)
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
							.filter((running: FlowRunning) => running.progress > 0)[0]?.progress.toFixed(0) ?? 0}%`
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
			>
				Cancel all
			</UButton>
		</div>
		<template v-if="!collapsed">
			<WorkflowQueueItem
				v-for="running in flowStore.flowsRunningByName(flowStore.currentFlow?.name)"
				:key="running.task_id"
				:running="running" />
		</template>
	</div>
</template>
