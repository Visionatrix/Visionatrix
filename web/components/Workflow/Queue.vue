<script setup lang="ts">
const flowStore = useFlowsStore()

const canceling = ref(false)
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
			>
				Cancel all
			</UButton>
		</div>
		<template v-if="!collapsed">
			<div v-for="running in flowStore.flowsRunningByName(flowStore.currentFlow?.name)" :key="running.task_id" class="mb-5">
				<UProgress class="mb-3" :value="running?.progress" indicator :color="!running.error ? 'green' : 'red'" />
				<p class="text-sm mb-5 text-slate-500">
					{{
						[
							'#' + running.task_id,
							...Object.keys(running.input_params_mapped)
								.filter((key) => {
									return running.input_params_mapped[key].value && running.input_params_mapped[key].value !== ''
								})
								.map((key) => {
									return `${running.input_params_mapped[key].display_name}: ${running.input_params_mapped[key].value}`
								})
						].join(' | ') + `${running.execution_time 
							? ' | execution_time: ' + running.execution_time.toFixed(2) + 's' 
							: ''
						}`
					}}
				</p>
				<WorkflowQueueInputFiles :running="running" />
				<WorkflowQueueErrorAlert v-if="running.error" :running="running" />
				<div class="flex justify-between">
					<UButton :icon="running.progress >= 0
							&& running.progress < 100
							? 'i-heroicons-stop'
							: 'i-heroicons-minus-circle'"
						:color="!running.error ? 'orange' : 'red'"
						variant="outline"
						:loading="canceling"
						@click="() => {
							canceling = true
							flowStore.cancelRunningFlow(running).finally(() => {
								canceling = false
							})
						}">
						{{
							running.progress >= 0
								&& running.progress < 100
								? 'Cancel'
								: 'Remove'
						}}
					</UButton>
					<UDropdown :items="[
							[{
								label: 'Comfy flow',
								labelClass: 'text-blue-500',
								icon: 'i-heroicons-arrow-down-tray',
								iconClass: 'bg-blue-500',
								click: () => flowStore.downloadFlowComfy(flowStore.currentFlow?.name, running.task_id),
							}]
						]"
						mode="click"
						:popper="{ placement: 'bottom-end' }">
						<UButton color="blue" variant="outline" icon="i-heroicons-ellipsis-vertical-16-solid" />
					</UDropdown>
				</div>
			</div>
		</template>
	</div>
</template>

<style scoped>
.progress-queue {
	height: 100%;
	max-height: 25dvh;
	overflow-y: auto;
}
</style>
