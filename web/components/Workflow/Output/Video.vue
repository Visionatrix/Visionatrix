<script setup lang="ts">
defineProps({
	flowResult: {
		type: Object as PropType<FlowResult>,
		required: true
	},
})

const flowStore = useFlowsStore()
</script>

<template>
	<div class="video-output">
		<template v-if="flowResult.outputs.length === 1">
			<video
				controls
				class="mb-2 mx-auto rounded-lg"
				style="max-height: 80vh;"
				:width="flowStore.$state.outputMaxSize"
				:height="flowStore.$state.outputMaxSize">
				<source
					:src="outputResultSrc({
						task_id: flowResult.task_id,
						node_id: flowResult.outputs[0].comfy_node_id
					})">
			</video>
		</template>
		<UCarousel
			v-else-if="flowResult.outputs.length > 1"
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
				<video
					controls
					class="mb-2 mx-auto rounded-lg"
					:width="flowStore.$state.outputMaxSize"
					:height="flowStore.$state.outputMaxSize">
					<source
						:src="outputResultSrc({
							task_id: flowResult.task_id,
							node_id: flowResult.outputs[0].comfy_node_id
						})">
				</video>
			</div>
		</UCarousel>
	</div>
</template>
