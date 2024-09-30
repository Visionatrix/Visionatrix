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
	inputParamsMapped: {
		type: Object,
		required: true,
	},
	isChildTask: {
		type: Boolean,
		required: false,
		default: false,
	},
	translatePrompt: {
		type: Boolean,
		required: false, // TODO: make required with possibility to adjust it
		default: false,
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
					node_id: props.flowResult.outputs.length > 1 ? props.flowResult.outputs[props.outputParamIndex].comfy_node_id : props.flowResult.outputs[0].comfy_node_id,
				}) || '',
				type: input_param.type,
			}
		} else if (input_param.type === 'list') {
			input_param_map[input_param.name] = {
				value: input_param.default || Object.keys(input_param.options as object)[0] || '',
				type: input_param.type,
				options: input_param.options,
			}
		} else if (input_param.type === 'bool') {
			input_param_map[input_param.name] = {
				value: input_param.default as boolean || false,
				type: input_param.type
			}
		} else if (['range', 'range_scale'].includes(input_param.type)) {
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
	flowStore.runFlow(
		targetFlow,
		input_params_map,
		1,
		props.translatePrompt,
		bindAsChildTask.value,
		bindAsChildTask.value ? Number(props.flowResult.task_id) : null
	)
		.finally(() => {
			sending.value = false
			emit('update:show', false)
		})
}

const bindAsChildTask = ref(false)
const flowResultReady = computed(() => props.flowResult.progress === 100 && props.flowResult?.error === '')

onBeforeMount(() => {
	// TODO: change to dynamic according to the output type
	flowStore.fetchSubFlows('image').then(() => {
		selectedFlow.value = subFlows.value[0] || ''
	})
	bindAsChildTask.value = false
})
</script>

<template>
	<UModal v-model="$props.show" class="z-[90]" :transition="false">
		<div class="p-4">
			<h2 class="text-lg text-center mb-4">Send to flow</h2>
			<div class="flex justify-center mb-4">
				<NuxtImg v-if="flowResultReady"
					:src="outputImgSrc"
					class="w-1/2 rounded-lg"
					:draggable="false" />
				<UAlert v-else
					color="orange"
					icon="i-heroicons-exclamation-circle-solid"
					:title="`Task is still running (${Math.ceil(flowResult.progress)}%, ${flowResult.execution_time.toFixed(2)}s)`"
					:description="flowResult.error !== '' ? flowResult.error : ''" />
			</div>
			<p v-if="inputParamsMapped" class="text-sm text-slate-500 text-center mb-4">
				{{
					[
						'#' + flowResult.task_id,
						...Object.keys(inputParamsMapped)
							.filter((key) => {
								return inputParamsMapped[key].value !== ''
							})
							.map((key) => {
								return `${inputParamsMapped[key].display_name}: ${inputParamsMapped[key].value}`
							})
					].join(' | ')
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
			<UAlert v-if="isChildTask"
				class="mb-4"
				icon="i-heroicons-exclamation-circle-solid"
				title="Child task"
				description="The latest child task is always used as input for sub-flow" />
			<div class="flex items-center justify-between">
				<UCheckbox v-model="bindAsChildTask" label="Bind as child task" />
				<UButton
					icon="i-heroicons-arrow-uturn-up-solid"
					color="violet"
					variant="outline"
					:loading="sending"
					:disabled="subFlows.length === 0 || (isChildTask && !flowResultReady)"
					@click="sendToFlow">
					Send
				</UButton>
			</div>
		</div>
	</UModal>
</template>
