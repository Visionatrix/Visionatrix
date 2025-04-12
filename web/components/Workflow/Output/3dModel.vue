<script setup lang="ts">
onMounted(() => {
	import('@google/model-viewer')
})

defineProps({
	flowResult: {
		type: Object as PropType<FlowResult>,
		required: true
	},
})

const flowStore = useFlowsStore()
</script>

<template>
	<div class="3d-model-output">
		<template v-if="flowResult.outputs.length === 1">
			<ClientOnly>
				<model-viewer
					auto-rotate
					camera-controls
					class="border border-slate-500 rounded-lg mx-auto mb-3"
					:style="{
						width: '100%',
						height: flowStore.$state.outputMaxSize + 'px',
					}"
					:src="outputResultSrc({
						task_id: flowResult.task_id,
						node_id: flowResult.outputs[0].comfy_node_id
					})"
				/>
			</ClientOnly>
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
				item: 'basis-full',
				indicators: {
					wrapper: 'relative bottom-0 mt-4 md:hidden'
				}
			}"
			:page="1"
			indicators>
			<div class="flex flex-col basis-full justify-between mx-2">
				<ClientOnly>
					<model-viewer
						auto-rotate
						camera-controls
						:style="{
							width: flowStore.$state.outputMaxSize + 'px',
							height: flowStore.$state.outputMaxSize + 'px',
						}"
						:src="outputResultSrc({
							task_id: flowResult.task_id,
							node_id: flowResult.outputs[0].comfy_node_id
						})"
					/>
				</ClientOnly>
			</div>
		</UCarousel>
	</div>
</template>
