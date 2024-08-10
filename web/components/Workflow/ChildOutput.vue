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

// Currently only linear child_tasks linked list is supported
const findPreLatestAndLatestChildTask = (task: FlowResult|TaskHistoryItem|any) => {
	if (task.child_tasks.length === 0) {
		return task
	}
	if (task.child_tasks.length === 1) {
		leftComparisonTask.value = task
	}
	return findPreLatestAndLatestChildTask(task.child_tasks[0])
}

function findChildTaskByTaskId(task: FlowResult|TaskHistoryItem|any, taskId: number) {
	if (Number(task.task_id) === taskId) {
		return task
	}
	if (task.child_tasks.length === 0) {
		return null
	}
	return findChildTaskByTaskId(task.child_tasks[0], taskId)
}

const leftComparisonTask: Ref<FlowResult|TaskHistoryItem|any> = ref(props.flowResult)
const rightComparisonTask: Ref<TaskHistoryItem|FlowResult|any> = ref(findPreLatestAndLatestChildTask(props.flowResult))

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
					props.openImageModal(outputImgSrc({
						task_id: task.task_id,
						node_id: task.outputs[props.outputsIndex].comfy_node_id
					}))
				}
			},
		],
	]
}

function buildRightDropdownItems(task: FlowResult|TaskHistoryItem|any) {
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
					props.openImageModal(outputImgSrc({
						task_id: task.task_id,
						node_id: task.outputs[props.outputsIndex].comfy_node_id
					}))
				}
			},
			{
				label: `Delete #${task.task_id} task`,
				icon: 'i-heroicons-trash',
				click: () => {
					flowsStore.deleteFlowHistory(task.task_id).then(() => {
						const parentTask = findChildTaskByTaskId(props.flowResult, task.parent_task_id)
						if (parentTask) {
							parentTask.child_tasks = parentTask.child_tasks.filter((childTask: TaskHistoryItem) => {
								return childTask.task_id !== task.task_id
							})
						}
						resetComparison()
					})
				}
			}
		],
	]
}



function prevLeftComparisonTask() {
	const parentTaskId = leftComparisonTask.value.parent_task_id
	if (!parentTaskId) {
		return
	}
	const parentTask = findChildTaskByTaskId(props.flowResult, parentTaskId)
	if (!parentTask) {
		return
	}
	leftComparisonTask.value = parentTask
}

function nextLeftComparisonTask() {
	if (leftComparisonTask.value.child_tasks.length === 0) {
		return
	}
	leftComparisonTask.value = leftComparisonTask.value.child_tasks[0]
}

function prevRightComparisonTask() {
	const parentTaskId = rightComparisonTask.value.parent_task_id
	if (!parentTaskId) {
		return
	}
	const parentTask = findChildTaskByTaskId(props.flowResult, parentTaskId)
	if (!parentTask) {
		return
	}
	rightComparisonTask.value = parentTask
}

function nextRightComparisonTask() {
	if (rightComparisonTask.value.child_tasks.length === 0) {
		return
	}
	rightComparisonTask.value = rightComparisonTask.value.child_tasks[0]
}

function resetComparison() {
	leftComparisonTask.value = props.flowResult
	rightComparisonTask.value = findPreLatestAndLatestChildTask(props.flowResult)
	toggleOriginal.value = false
}

// watch for flowResult.child_tasks changes
watch(props.flowResult, (newFlowResult) => {
	console.debug('[ChildOutput] flowResult changed', newFlowResult)
	resetComparison()
})

const toggleOriginal = ref(false)
const toggleCompare = ref(true)

watch(toggleOriginal, (newToggleOriginal) => {
	if (newToggleOriginal) {
		leftComparisonTask.value = props.flowResult
	}
})
</script>

<template>
	<div class="flex flex-col items-center mb-2 max-w-fit mx-auto z-0">
		<NuxtImg
			v-show="!toggleCompare"
			class="mb-2 h-100 mx-auto rounded-lg cursor-pointer"
			draggable="false"
			fit="outside"
			loading="lazy"
			:src="outputImgSrc({
				task_id: flowResult.task_id,
				node_id: flowResult.outputs[outputsIndex].comfy_node_id
			})"
			@click="openImageModal(outputImgSrc({
				task_id: flowResult.task_id,
				node_id: flowResult.outputs[outputsIndex].comfy_node_id
			}))" />
		<ImgComparisonSlider v-if="toggleCompare"
			class="mb-2 mx-auto outline-none w-fit rounded-lg">
			<NuxtImg
				slot="first"
				:src="outputImgSrc({
					task_id: !toggleOriginal ? leftComparisonTask.task_id : flowResult.task_id,
					node_id: !toggleOriginal ? leftComparisonTask?.outputs[outputsIndex].comfy_node_id : flowResult.outputs[outputsIndex].comfy_node_id
				})" />
			<NuxtImg
				v-if="rightComparisonTask && rightComparisonTask.progress === 100"
				slot="second"
				:src="outputImgSrc({
					task_id: rightComparisonTask.task_id,
					node_id: rightComparisonTask.outputs[outputsIndex].comfy_node_id
				})" />
		</ImgComparisonSlider>
		<div class="text-slate-500 text-center text-sm w-full mx-auto flex flex-wrap items-center justify-center md:justify-between">
			<div class="toggles py-2">
				<div class="mr-2 inline-flex items-center text-sm">
					<UToggle
						:id="`toggle-compare-${flowResult.task_id}`"
						v-model="toggleCompare"
						size="xs"
						class="mr-2" />
					<label class="cursor-pointer select-none"
						:for="`toggle-compare-${flowResult.task_id}`">
						Comparison
					</label>
				</div>
				<div class="mr-2 inline-flex items-center text-sm">
					<UToggle
						:id="`toggle-original-${flowResult.task_id}`"
						v-model="toggleOriginal"
						:disabled="!toggleCompare"
						size="xs"
						class="mr-2" />
					<label class="cursor-pointer select-none"
						:for="`toggle-original-${flowResult.task_id}`">
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
					:disabled="toggleOriginal || Number(leftComparisonTask.child_tasks[0].task_id) === Number(rightComparisonTask.task_id)"
					@click="nextLeftComparisonTask" />

				<UIcon class="mx-3" name="i-heroicons-arrows-right-left-16-solid" />

				<UButton
					icon="i-heroicons-arrow-small-left-20-solid"
					size="2xs"
					variant="soft"
					color="cyan"
					:disabled="rightComparisonTask.parent_task_id === Number(leftComparisonTask.task_id) || rightComparisonTask.parent_task_id === null"
					@click="prevRightComparisonTask" />
				<UDropdown
					:items="buildRightDropdownItems(rightComparisonTask)"
					mode="click"
					:popper="{ placement: 'top' }">
					<UButton
						variant="link"
						color="white"
						size="xs">
						#{{ rightComparisonTask.task_id }}
					</UButton>
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
						@click="resetComparison" />
				</UTooltip>
			</div>
		</div>
	</div>
</template>
