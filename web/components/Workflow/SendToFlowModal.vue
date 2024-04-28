<script setup lang="ts">
const props = defineProps({
	show: {
		type: Boolean,
		required: false,
	},
	flowResult: {
		type: Object,
		required: false,
		default: () => null,
	},
	outputImgSrc: {
		type: String,
		required: true,
	},
	outputParamIndex: {
		type: Number,
		required: true,
	},
})

const flowStore = useFlowsStore()
const subFlows = computed(() => {
	return flowStore.sub_flows.map((flow) => {
		return {
			value: flow.name,
			label: `${flow.display_name} - ${flow.description}`,
		}
	})
})
const selectedFlow = ref(subFlows.value[0] || '')
const sending = ref(false)

const emit = defineEmits(['update:show'])

function sendToFlow() {
	console.debug('[Send to flow]: ', selectedFlow.value)
	const targetFlow: Flow|any = flowStore.sub_flows.find((flow) => flow.name === selectedFlow.value.value && flow.display_name === selectedFlow.value.label.split(' - ')[0])
	console.debug('[Send to flow]: targetFlow', targetFlow)
	if (!targetFlow) {
		const toast = useToast()
		toast.add({
			title: `Target sub-flow "${selectedFlow.value.value}" not found`,
			description: 'Please, verify the target sub-flow is installed and available and try again',
			timeout: 5000,
		})
		return
	}
	// Build target flow input_params_map array with default values
	const input_params_map: any = targetFlow.input_params.reduce((acc: FlowInputParam[], input_param: FlowInputParam) => {
		const input_param_map: any = {}
		if (input_param.type === 'text') {
			input_param_map[input_param.name] = {
				value: input_param.default as string || '',
				type: input_param.type,
			}
		}
		else if (input_param.type === 'number') {
			input_param_map[input_param.name] = {
				value: input_param.default as number || 0,
				type: input_param.type,
			}
		}
		else if (input_param.type === 'image') {
			input_param_map[input_param.name] = {
				value: JSON.stringify({
					task_id: props.flowResult.task_id,
					node_id: props.flowResult.output_params[props.outputParamIndex].comfy_node_id,
				}) || '',
				type: input_param.type,
			}
		} else if (input_param.type === 'list') {
			input_param_map[input_param.name] = {
				value: Object.keys(input_param.options as object)[0] || '',
				type: input_param.type,
				options: input_param.options,
			}
		} else if (input_param.type === 'bool') {
			input_param_map[input_param.name] = {
				value: input_param.default as boolean || false,
				type: input_param.type
			}
		} else if (input_param.type === 'range') {
			input_param_map[input_param.name] = {
				value: input_param.default as number || 0,
				type: input_param.type
			}
		}
		acc.push(input_param_map)
		return acc
	}, [])

	console.debug('[Send to flow]: input_params_map', input_params_map)

	sending.value = true
	flowStore.runFlow(targetFlow, input_params_map).finally(() => {
		sending.value = false
		emit('update:show', false)
	})
}

onBeforeMount(() => {
	// TODO: change to dynamic according to the output type
	flowStore.fetchSubFlows('image').then(() => {
		selectedFlow.value = subFlows.value[0] || ''
	})
})
</script>

<template>
	<UModal v-model="$props.show" class="z-[90]" :transition="false">
		<div class="p-4">
			<h2 class="text-lg text-center mb-4">Send to flow</h2>
			<div class="flex justify-center mb-4">
				<NuxtImg :src="outputImgSrc" class="w-1/2 rounded-lg" :draggable="false" />
			</div>
			<p class="text-sm text-slate-500 text-center mb-4">
				{{
					Object.keys(flowResult.input_params_mapped)
						.filter((key) => {
							return flowResult.input_params_mapped[key] !== ''
						})
						.map((key) => {
							return `${key}: ${flowResult.input_params_mapped[key]}`
						}).join(' | ')
				}}
			</p>
			<p class="text-md text-center text-red-500 mb-4">
				<USelectMenu
					v-if="subFlows.length > 0"
					v-model="selectedFlow"
					class="w-full"
					size="lg"
					:options="subFlows" />
				<span v-else>No sub-flows available</span>
			</p>
			<div class="flex justify-end">
				<UButton
					icon="i-heroicons-arrow-uturn-up-solid"
					color="violet"
					variant="outline"
					:loading="sending"
					:disabled="subFlows.length === 0"
					@click="sendToFlow">
					Send
				</UButton>
			</div>
		</div>
	</UModal>
</template>
