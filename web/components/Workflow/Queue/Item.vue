<script setup lang="ts">
defineProps({
	running: {
		type: Object as PropType<FlowRunning>,
		required: true,
	},
})

const flowStore = useFlowsStore()

const canceling = ref(false)
const priorityLoading = ref(false)

function buildQueueDropdownItems(running: FlowRunning) {
	return [
		[{
			label: 'Comfy flow',
			labelClass: 'text-blue-500',
			icon: 'i-heroicons-arrow-down-tray',
			iconClass: 'bg-blue-500',
			click: () => flowStore.downloadFlowComfy(flowStore.currentFlow?.name, running.task_id),
		}],
		[
			{
				label: `Raise priority ${running.priority > 0 ? `(${running.priority})` : ''}`,
				labelClass: 'text-gray-500',
				icon: 'i-heroicons-arrow-up',
				iconClass: 'bg-gray-500',
				disabled: running.priority === 15 || running.progress > 0,
				click: () => {
					priorityLoading.value = true
					flowStore.raiseQueuePriority(running).finally(() => {
						priorityLoading.value = false
					})
				},
			},
			{
				label: `Lower priority ${running.priority > 0 ? `(${running.priority})` : ''}`,
				labelClass: 'text-gray-500',
				icon: 'i-heroicons-arrow-down',
				iconClass: 'bg-gray-500',
				disabled: running.priority === 0 || running.progress > 0,
				click: () => {
					priorityLoading.value = true
					flowStore.lowerQueuePriority(running).finally(() => {
						priorityLoading.value = false
					})
				},
			},
			{
				label: `Reset priority ${running.priority > 0 ? `(${running.priority})` : ''}`,
				labelClass: 'text-gray-500',
				icon: 'i-heroicons-arrow-path-rounded-square-solid',
				iconClass: 'bg-gray-500',
				disabled: running.priority === 0 || running.progress > 0,
				click: () => {
					priorityLoading.value = true
					flowStore.resetQueuePriority(running).finally(() => {
						priorityLoading.value = false
					})
				},
			}
		]
	]
}
</script>

<template>
	<div class="mb-5">
		<UProgress class="mb-3" :value="running?.progress" indicator :color="!running.error ? 'green' : 'red'" />
		<p class="text-sm mb-5 text-slate-500">
			{{
				[
					`${running?.priority && running.priority > 0 ? '[' + running.priority + '] ' : ''}#${running.task_id}`,
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
			<UDropdown :items="buildQueueDropdownItems(running)"
				mode="click"
				:popper="{ placement: 'bottom-end' }">
				<UButton color="blue" variant="outline" icon="i-heroicons-ellipsis-vertical-16-solid" />
			</UDropdown>
		</div>
	</div>
</template>
