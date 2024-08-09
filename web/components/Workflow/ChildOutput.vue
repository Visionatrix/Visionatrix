<script setup lang="ts">
const props = defineProps({
	flowResult: {
		type: Object as PropType<FlowResult>,
		required: true
	},
})

const img = useImage()
const preLatestChildTask = ref(props.flowResult)

const findLatestChildTask = (task: any) => {
	if (task.child_tasks.length === 0) {
		return task
	}
	if (task.child_tasks.length === 1) {
		preLatestChildTask.value = task
		return findLatestChildTask(task.child_tasks[0])
	}
	if (task.child_tasks[task.child_tasks.length - 1].child_tasks.length === 0) {
		preLatestChildTask.value = task.child_tasks[task.child_tasks.length - 1]
	}
	return findLatestChildTask(task.child_tasks[task.child_tasks.length - 1])
}

const latestChildTask = computed(() => {
	const childTask: TaskHistoryItem = findLatestChildTask(props.flowResult)
	if (!childTask) {
		return null
	}
	return childTask
})
</script>

<template>
	<div class="flex flex-col items-center mb-2">
		<ImgComparisonSlider class="mb-2 mx-auto outline-none w-fit rounded-lg">
			<NuxtImg
				slot="first"
				class="h-100 mx-auto rounded-lg cursor-pointer" draggable="false"
				loading="lazy"
				:placeholder="img(`${buildBackendUrl()}/vix_logo.png`, { f: 'png', blur: 3, q: 50 })"
				:src="outputImgSrc({
					task_id: preLatestChildTask.task_id,
					node_id: preLatestChildTask?.outputs[0].comfy_node_id
				})" />
			<NuxtImg
				v-if="latestChildTask && latestChildTask.progress === 100"
				slot="second"
				class="h-100 mx-auto rounded-lg cursor-pointer" draggable="false"
				loading="lazy"
				:placeholder="img(`${buildBackendUrl()}/vix_logo.png`, { f: 'png', blur: 3, q: 50 })"
				:src="outputImgSrc({
					task_id: latestChildTask.task_id,
					node_id: latestChildTask.outputs[0].comfy_node_id
				})" />
		</ImgComparisonSlider>
		<p class="text-slate-500 text-center text-sm">
			<span v-if="latestChildTask && latestChildTask.progress === 100">
				Comparison with child task
				<ULink
					:to="`/workflows/${latestChildTask.name}?task_id=${latestChildTask.task_id}`"
					class="text-blue-500 hover:underline"
				>
					#{{ latestChildTask.task_id }}
				</ULink>
			</span>
			<span v-else>No child output available</span>
		</p>
	</div>
</template>
