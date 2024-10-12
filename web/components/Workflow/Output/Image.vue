<script setup lang="ts">
defineProps({
	flowResult: {
		type: Object as PropType<FlowResult>,
		required: true
	},
	handleSendToFlow: {
		type: Function as PropType<(flowResult: FlowResult, index: number) => void>,
		required: true
	},
	openImageModal: {
		type: Function as PropType<(src: string) => void>,
		required: true
	}
})

const flowStore = useFlowsStore()
</script>

<template>
	<div class="image-output">
		<template v-if="flowResult.outputs.length === 1">
			<WorkflowOutputChild
				v-if="flowResult?.child_tasks && flowResult?.child_tasks.length > 0"
				:flow-result="flowResult"
				:open-image-modal="openImageModal" />
			<NuxtImg v-else-if="flowResult.outputs.length === 1"
				class="mb-2 mx-auto rounded-lg cursor-pointer"
				:height="flowStore.$state.outputMaxSize"
				:width="flowStore.$state.outputMaxSize"
				draggable="false"
				fit="cover"
				loading="lazy"
				:src="outputResultSrc({
					task_id: flowResult.task_id,
					node_id: flowResult.outputs[0].comfy_node_id
				})"
				@click="openImageModal(outputResultSrc({
					task_id: flowResult.task_id,
					node_id: flowResult.outputs[0].comfy_node_id
				}))" />
		</template>
		<UCarousel v-else-if="flowResult.outputs.length > 1"
			v-slot="{ item }"
			class="mb-3 rounded-lg overflow-hidden"
			:items="flowResult.outputs.map((result_output_param: FlowOutputParam, index: number) => {
				return {
					task_id: flowResult.task_id,
					node_id: result_output_param.comfy_node_id,
					index,
				}
			})"
			:ui="{
				item: 'basis-full md:basis-1/2',
				indicators: {
					wrapper: 'relative bottom-0 mt-4 md:hidden'
				}
			}"
			:page="1"
			indicators>
			<div class="flex flex-col basis-full justify-between mx-2">
				<WorkflowOutputChild
					v-if="flowResult?.child_tasks
						&& hasChildTaskByParentTaskNodeId(flowResult, item.index, item.node_id)"
					:flow-result="flowResult"
					:outputs-index="item.index"
					:open-image-modal="openImageModal" />
				<NuxtImg
					v-else
					:class="`mb-2 h-100 max-h-[${flowStore.$state.outputMaxSize}px] mx-auto rounded-lg cursor-pointer`"
					draggable="false"
					:height="flowStore.$state.outputMaxSize"
					:width="flowStore.$state.outputMaxSize"
					fit="cover"
					loading="lazy"
					:src="outputResultSrc(item)"
					@click="openImageModal(outputResultSrc(item))" />
				<UButton
					class="mt-2 w-fit mx-auto"
					icon="i-heroicons-arrow-uturn-up-solid"
					color="violet"
					size="xs"
					variant="outline"
					@click="() => {
						handleSendToFlow(flowResult, item.index)
					}">
					Send to flow
				</UButton>
			</div>
		</UCarousel>
	</div>
</template>
