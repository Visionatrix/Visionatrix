<script setup lang="ts">
const props = defineProps({
	flowResult: {
		type: Object as PropType<FlowResult>,
		required: true
	},
})

const flowsStore = useFlowsStore()
const toast = useToast()

const loading = ref<boolean>(false)
const outputResultsText = ref<any>({})

function getOutputText(flowResult: FlowResult, flowOutputParam: FlowOutputParam) {
	const { $apiFetch } = useNuxtApp()
	const url = outputResultSrc({
		task_id: flowResult.task_id,
		node_id: flowOutputParam.comfy_node_id
	})
	return $apiFetch(url).then((response: string|any) => {
		outputResultsText.value[flowOutputParam.comfy_node_id] = response
	}).catch((error: any) => {
		console.error(error)
	}).finally(() => {
		loading.value = false
	})
}

onMounted(() => {
	Promise.all(props.flowResult.outputs.filter((o: FlowOutputParam) => o.type === 'text').map((output: FlowOutputParam) => {
		return getOutputText(props.flowResult, output)
	}))
})
</script>

<template>
	<div class="text-output">
		<template v-if="flowResult.outputs.length === 1">
			<div class="mb-2 mx-auto rounded-lg text-md p-4 pr-8 border border-slate-500 relative">
				<UButton
					v-if="!loading"
					variant="outline"
					class="absolute top-2 right-2 z-10"
					icon="i-mdi-content-copy"
					size="xs"
					color="white"
					@click="() => {
						const clipboard = useCopyToClipboard()
						clipboard.copy(outputResultsText[flowResult.outputs[0].comfy_node_id])
						toast.add({
							title: 'Clipboard',
							description: 'Text copied to clipboard',
						})
					}" />

				<p>{{ !loading ? outputResultsText[flowResult.outputs[0].comfy_node_id] : 'Loading...' }}</p>
			</div>
		</template>
		<UCarousel
			v-else-if="flowResult.outputs.length > 1"
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
					wrapper: 'relative bottom-0 mt-4'
				}
			}"
			:page="1"
			indicators
			arrows>
			<div class="mb-2 mx-2 rounded-lg text-md p-4 border border-slate-500 shadow-sm overflow-y-auto relative"
				:style="{ 'max-height': Math.ceil(flowsStore.$state.outputMaxSize / 2) + 'px' }">
				<UButton
					v-if="!loading"
					variant="outline"
					class="absolute top-2 right-2 z-10"
					icon="i-mdi-content-copy"
					size="xs"
					color="white"
					@click="() => {
						const clipboard = useCopyToClipboard()
						clipboard.copy(outputResultsText[item.node_id])
						toast.add({
							title: 'Clipboard',
							description: 'Text copied to clipboard',
						})
					}" />
				<p>{{ !loading ? outputResultsText[item.node_id]: 'Loading...' }}</p>
			</div>
		</UCarousel>
	</div>
</template>
