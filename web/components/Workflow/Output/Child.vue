<script setup lang="ts">
const props = defineProps({
	flowResult: {
		type: Object as PropType<FlowResult>,
		required: true
	},
	outputsIndex: {
		type: Number,
		required: false,
		default: () => 0,
	},
	openImageModal: {
		type: Function,
		required: true,
	},
})

const flowsStore = useFlowsStore()


const findPreLatestAndLatestChildTask = (task: FlowResult|TaskHistoryItem|any, parentNodeId: number|null = null, keepLeft: boolean = false) => {
	if (task.child_tasks.length === 0) {
		return task
	}
	const childTaskIndex = task.child_tasks.findIndex((t: FlowResult|TaskHistoryItem|any) => t.parent_task_node_id === parentNodeId)
	if (childTaskIndex !== -1) {
		if (!keepLeft) {
			leftComparisonTask.value = task
		}
		return findPreLatestAndLatestChildTask(task.child_tasks[childTaskIndex], task.child_tasks[childTaskIndex].outputs[0].comfy_node_id, keepLeft)
	}
	return task
}

function findChildTaskByTaskIdNodeId(task: FlowResult|TaskHistoryItem|any, taskId: number, parentNodeId: number|null = null) {
	if (parentNodeId !== null && task.parent_task_node_id === parentNodeId
		|| (Number(task.task_id) === taskId)) {
		return task
	}

	for (let k=0; k < task.child_tasks.length; k++) {
		for (let i = 0; i < task.child_tasks[k].outputs.length; i++) {
			const result_task: FlowResult|TaskHistoryItem|any = findChildTaskByTaskIdNodeId(task.child_tasks[k], taskId, task.child_tasks[k].outputs[i].comfy_node_id)
			if (result_task !== null) {
				return result_task
			}
		}
	}
	return null
}

const leftComparisonTask: Ref<FlowResult|TaskHistoryItem|any> = ref(props.flowResult)
const rightComparisonTask: Ref<TaskHistoryItem|FlowResult|any> = ref(findPreLatestAndLatestChildTask(props.flowResult, props.flowResult.outputs[props.outputsIndex].comfy_node_id, false))

function buildLeftDropdownItems(task: FlowResult|TaskHistoryItem|any) {
	return [
		[
			{
				label: `${flowsStore.flowByName(task?.flow_name ?? task?.name)?.display_name}#${task.task_id}`,
				disabled: true, // TODO: navigate to task with scroll to task_id
			}
		],
		[
			{
				label: 'View image',
				icon: 'i-heroicons-eye',
				click: () => {
					props.openImageModal(outputResultSrc({
						task_id: task.task_id,
						node_id: task.outputs.length > 1 ? task.outputs[props.outputsIndex].comfy_node_id : task.outputs[0].comfy_node_id
					}))
				}
			},
		],
	]
}

function buildRightDropdownItems(task: FlowResult|TaskHistoryItem|any) {
	const items: any = [
		[
			{
				label: `${flowsStore.flowByName(task?.flow_name ?? task?.name)?.display_name}#${task.task_id}`,
				disabled: true, // TODO: navigate to task with scroll to task_id
			}
		],
		[
			{
				label: 'View image',
				icon: 'i-heroicons-eye',
				disabled: task.progress < 100 || task.error !== '',
				click: () => {
					props.openImageModal(outputResultSrc({
						task_id: task.task_id,
						node_id: task.outputs.length > 1 ? task.outputs[props.outputsIndex].comfy_node_id : task.outputs[0].comfy_node_id
					}))
				}
			},
			{
				label: (task.progress < 100) ? 'Cancel' : 'Delete',
				labelClass: (task.progress < 100) ? 'text-orange-500' : 'text-red-500',
				icon: (task.progress < 100) ? 'i-heroicons-stop' : 'i-heroicons-trash',
				iconClass: (task.progress < 100) ? 'bg-orange-500' : 'bg-red-500',
				click: () => {
					flowsStore.deleteFlowHistory(task.task_id).then(() => {
						const parentTask = findChildTaskByTaskIdNodeId(props.flowResult, task.parent_task_id, task.parent_task_node_id)
						if (parentTask) {
							parentTask.child_tasks = parentTask.child_tasks.filter((childTask: TaskHistoryItem) => {
								return Number(childTask.task_id) !== Number(task.task_id)
							})
						}
						resetComparison(false, props.flowResult)
					})
				}
			}
		],
	]

	if (task.progress < 100) {
		items[0][1]= {
			label: `Progress: ${Math.ceil(task.progress)}% (${task.execution_time.toFixed(2)}s)`,
			labelClass: 'text-blue-500',
			disabled: true,
		}
	}

	if (task.error !== '') {
		items[0].push({
			label: `Error: ${task.error}`,
			labelClass: 'text-red-500',
			slot: 'error',
			click: () => {
				// copy error message to clipboard
				const clipboard = useCopyToClipboard()
				clipboard.copy(task.error)
				const toast = useToast()
				toast.add({
					title: 'Clipboard',
					description: `Task #${task.task_id} error copied to clipboard`,
					timeout: 2000,
				})
			}
		})
	}

	return items
}


function prevLeftComparisonTask() {
	const parentTaskId = leftComparisonTask.value.parent_task_id
	if (!parentTaskId) {
		return
	}
	const parentTask = findChildTaskByTaskIdNodeId(props.flowResult, parentTaskId, leftComparisonTask.value.parent_task_node_id)
	if (!parentTask) {
		return
	}
	leftComparisonTask.value = parentTask
}

function nextLeftComparisonTask() {
	if (leftComparisonTask.value.child_tasks.length === 0) {
		return
	}
	const currentOutputNodeId = leftComparisonTask.value.outputs.length > 1 ? leftComparisonTask.value.outputs[props.outputsIndex].comfy_node_id : leftComparisonTask.value.outputs[0].comfy_node_id
	const nextChildTask = leftComparisonTask.value.child_tasks.find((t: FlowResult|TaskHistoryItem|any) => t.parent_task_node_id === currentOutputNodeId)
	if (!nextChildTask) {
		return
	}
	leftComparisonTask.value = nextChildTask
}

const hasNextLeftComparisonTask = computed(() => {
	if (leftComparisonTask.value.child_tasks.length === 0) {
		return
	}
	const currentOutputNodeId = leftComparisonTask.value.outputs.length > 1 ? leftComparisonTask.value.outputs[props.outputsIndex].comfy_node_id : leftComparisonTask.value.outputs[0].comfy_node_id
	const nextChildTask = leftComparisonTask.value.child_tasks.find((t: FlowResult|TaskHistoryItem|any) => t.parent_task_node_id === currentOutputNodeId)
	return nextChildTask.task_id !== rightComparisonTask.value.task_id
})

function prevRightComparisonTask() {
	const parentTaskId = rightComparisonTask.value.parent_task_id
	if (!parentTaskId) {
		return
	}
	const parentTask = findChildTaskByTaskIdNodeId(props.flowResult, parentTaskId, rightComparisonTask.value.parent_task_node_id)
	if (!parentTask) {
		return
	}
	rightComparisonTask.value = parentTask
}

function nextRightComparisonTask() {
	if (rightComparisonTask.value.child_tasks.length === 0) {
		return
	}
	const currentOutputNodeId = Number(rightComparisonTask.value.outputs[0].comfy_node_id)
	const nextChildTask = rightComparisonTask.value.child_tasks.find((t: FlowResult|TaskHistoryItem|any) => Number(t.parent_task_node_id) === currentOutputNodeId)
	if (!nextChildTask) {
		return
	}
	rightComparisonTask.value = nextChildTask
}

function resetComparison(keepLeft = false, flowResult: FlowResult|null = null) {
	if (!keepLeft) {
		leftComparisonTask.value = flowResult
	}
	rightComparisonTask.value = findPreLatestAndLatestChildTask(flowResult, flowResult?.outputs[props.outputsIndex].comfy_node_id, keepLeft)
	toggleOriginal.value = false
}

watch(props.flowResult, (newFlowResult) => {
	resetComparison(true, newFlowResult)
})

const toggleOriginal = ref(false)
const toggleCompare = ref(true)
const prevLeftCompare = ref(null)

watch(toggleOriginal, (newToggleOriginal) => {
	if (newToggleOriginal) {
		prevLeftCompare.value = leftComparisonTask.value
		leftComparisonTask.value = props.flowResult
	} else {
		if (prevLeftCompare.value) {
			leftComparisonTask.value = prevLeftCompare.value
			rightComparisonTask.value = findLatestChildTask(prevLeftCompare.value, props.outputsIndex, leftComparisonTask.value.outputs.length > 1 ? leftComparisonTask.value.outputs[props.outputsIndex].comfy_node_id : leftComparisonTask.value.outputs[0].comfy_node_id)
		}
	}
})
</script>

<template>
	<div class="flex flex-col items-center mb-2 max-w-fit mx-auto z-0">
		<NuxtImg
			v-show="!toggleCompare"
			class="mb-2 rounded-lg cursor-pointer"
			:height="flowsStore.outputMaxSize"
			:width="flowsStore.outputMaxSize"
			draggable="false"
			fit="cover"
			loading="lazy"
			:src="outputResultSrc({
				task_id: rightComparisonTask.progress === 100 ? rightComparisonTask.task_id : flowResult.task_id,
				node_id: rightComparisonTask.progress === 100 ? rightComparisonTask.outputs[0].comfy_node_id : flowResult.outputs[outputsIndex].comfy_node_id
			})"
			@click="openImageModal(outputResultSrc({
				task_id: rightComparisonTask.task_id ?? flowResult.task_id,
				node_id: rightComparisonTask.outputs[0].comfy_node_id ?? flowResult.outputs[outputsIndex].comfy_node_id
			}))" />
		<ImgComparisonSlider v-if="toggleCompare"
			class="mb-2 mx-auto outline-none w-fit rounded-lg">
			<NuxtImg
				slot="first"
				:height="flowsStore.outputMaxSize"
				:width="flowsStore.outputMaxSize"
				fit="cover"
				draggable="false"
				:src="outputResultSrc({
					task_id: !toggleOriginal ? leftComparisonTask.task_id : flowResult.task_id,
					node_id: !toggleOriginal ? leftComparisonTask.parent_task_node_id !== null ? leftComparisonTask?.outputs[0].comfy_node_id : leftComparisonTask?.outputs[outputsIndex].comfy_node_id ?? leftComparisonTask?.outputs[0].comfy_node_id : flowResult.outputs[outputsIndex].comfy_node_id
				})" />
			<NuxtImg
				v-if="rightComparisonTask && rightComparisonTask.progress === 100"
				slot="second"
				:height="flowsStore.outputMaxSize"
				:width="flowsStore.outputMaxSize"
				fit="cover"
				draggable="false"
				:src="outputResultSrc({
					task_id: rightComparisonTask.task_id,
					node_id: rightComparisonTask.outputs[0].comfy_node_id
				})" />
			<NuxtImg
				v-else
				slot="second"
				:height="flowsStore.outputMaxSize"
				:width="flowsStore.outputMaxSize"
				fit="cover"
				draggable="false"
				:src="`${buildBackendUrl()}/vix_logo.png`" />
		</ImgComparisonSlider>
		<div class="text-slate-500 text-center text-sm w-full mx-auto flex flex-wrap items-center justify-center md:justify-between">
			<div class="toggles py-2">
				<div class="mr-2 inline-flex items-center text-sm">
					<UToggle
						:id="`toggle-compare-${flowResult.task_id}-${outputsIndex}`"
						v-model="toggleCompare"
						size="xs"
						class="mr-2" />
					<label class="cursor-pointer select-none"
						:for="`toggle-compare-${flowResult.task_id}-${outputsIndex}`">
						Comparison
					</label>
				</div>
				<div class="mr-2 inline-flex items-center text-sm">
					<UToggle
						:id="`toggle-original-${flowResult.task_id}-${outputsIndex}`"
						v-model="toggleOriginal"
						:disabled="!toggleCompare"
						size="xs"
						class="mr-2" />
					<label class="cursor-pointer select-none"
						:for="`toggle-original-${flowResult.task_id}-${outputsIndex}`">
						Original
					</label>
				</div>
			</div>
			<div v-if="toggleCompare" class="flex items-center">
				<UButton
					icon="i-heroicons-arrow-small-left-20-solid"
					size="2xs"
					variant="soft"
					color="cyan"
					:disabled="toggleOriginal || leftComparisonTask.parent_task_id === null"
					@click="prevLeftComparisonTask" />
				<UDropdown
					:items="buildLeftDropdownItems(leftComparisonTask)"
					mode="click"
					:popper="{ placement: 'top' }">
					<UButton
						variant="link"
						color="white"
						size="xs">
						#{{ !toggleOriginal ? leftComparisonTask.task_id : flowResult.task_id }}
					</UButton>
				</UDropdown>
				<UButton
					icon="i-heroicons-arrow-small-right-20-solid"
					size="2xs"
					variant="soft"
					color="cyan"
					:disabled="toggleOriginal || !hasNextLeftComparisonTask"
					@click="nextLeftComparisonTask" />

				<UIcon class="mx-3" name="i-heroicons-arrows-right-left-16-solid" />

				<UButton
					icon="i-heroicons-arrow-small-left-20-solid"
					size="2xs"
					variant="soft"
					color="cyan"
					:disabled="!findChildTaskByTaskIdNodeId(props.flowResult, rightComparisonTask.parent_task_id, rightComparisonTask.parent_task_node_id) || rightComparisonTask.parent_task_id === Number(leftComparisonTask.task_id) || rightComparisonTask.parent_task_id === null"
					@click="prevRightComparisonTask" />
				<UDropdown
					:items="buildRightDropdownItems(rightComparisonTask)"
					mode="click"
					:popper="{ placement: 'top' }">
					<UButton
						:class="{
							'text-blue-500': rightComparisonTask.progress !== 100 && rightComparisonTask.error === '',
							'text-red-500': rightComparisonTask.error !== '',
						}"
						variant="link"
						color="white"
						size="xs">
						{{ rightComparisonTask.progress === 100 ? '#' + rightComparisonTask.task_id: Math.ceil(rightComparisonTask.progress) + '%' }}
					</UButton>
					<template #error="{ item }">
						<div class="text-red-500 truncate" :title="item.label">
							{{ item.label }}
						</div>
					</template>
				</UDropdown>
				<UButton
					icon="i-heroicons-arrow-small-right-20-solid"
					size="2xs"
					variant="soft"
					color="cyan"
					:disabled="rightComparisonTask.child_tasks.length === 0"
					@click="nextRightComparisonTask" />
				<UTooltip
					class="ml-3"
					text="Reset comparison"
					:popper="{ placement: 'top' }">
					<UButton
						icon="i-heroicons-arrow-path-rounded-square-solid"
						size="2xs"
						variant="outline"
						color="white"
						@click="() => resetComparison(false, flowResult)" />
				</UTooltip>
			</div>
		</div>
	</div>
</template>
