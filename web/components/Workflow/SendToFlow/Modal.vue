<script setup lang="ts">
const props = defineProps({
	flowResult: {
		type: Object as PropType<FlowResult>,
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

const show = defineModel('show', { default: false, type: Boolean })

const tabs = [
	{
		key: 'send-to-flow-output',
		label: 'Send to flow',
	},
	{
		key: 'send-to-flow-params',
		label: 'Edit params',
		description: 'Edit prompt params before sending to sub-flow',
	},
]
const selectedTab = ref(0)

const flowStore = useFlowsStore()
const toast = useToast()
const subFlows = computed(() => {
	return flowStore.sub_flows.map((flow) => {
		return {
			value: flow.name,
			label: `${flow.display_name} - ${flow.description}`,
		}
	})
})
const selectedFlow = ref(subFlows.value[0] || '')
const selectedSubFlowData = ref<Flow|any>({})
const sendToFlowParamsMapped = ref([])
const sendToFlowParamsValid = computed(() => {
	return sendToFlowParamsMapped.value.every((param) => {
		if (!param || Object.keys(param).length === 0) {
			return true
		}
		const key = Object.keys(param)[0]
		const value: FlowInputParam|any = param[key]
		if (value.optional) {
			return true
		}
		if (value.type === 'text') {
			return value.value !== ''
		}
		return true // for now only required text inputs
	})
})

watch(() => selectedFlow.value, (value) => {
	updateSendToFlowParams(value)
})

function updateSendToFlowParams(value: any) {
	selectedSubFlowData.value = flowStore.sub_flows.find((flow) => flow.name === value.value)
	if (!selectedSubFlowData.value) {
		return
	}
	sendToFlowParamsMapped.value = selectedSubFlowData.value.input_params.reduce((acc: any, inputParam: FlowInputParam|any) => {
		// skip currently unsupported input_param types for send-to-flow
		// TODO: Add support later
		if (['image', 'image-mask', 'range_scale'].includes(inputParam.type)) {
			acc.push({})
			return acc
		}

		const param: FlowInputParam|any = {
			[inputParam.name]: {
				value: null,
				display_name: inputParam.display_name,
				type: inputParam.type,
				optional: inputParam.optional,
				advanced: inputParam.advanced || false,
				default: inputParam.default || '',
				dynamic_lora: inputParam.dynamic_lora || false,
				trigger_words: inputParam.trigger_words || [],
			},
		}

		if (inputParam.type === 'text') {
			param[inputParam.name].value = inputParam.default || ''
			param[inputParam.name].translatable = inputParam.translatable || false
		} else if (inputParam.type === 'number') {
			param[inputParam.name].value = inputParam.default || 0
			param[inputParam.name].min = inputParam.min || 0
			param[inputParam.name].max = inputParam.max || 100
			param[inputParam.name].step = inputParam.step || 1
		} else if (inputParam.type === 'range') {
			param[inputParam.name].value = inputParam.default || 0
			param[inputParam.name].min = inputParam.min || 0
			param[inputParam.name].max = inputParam.max || 100
			param[inputParam.name].step = inputParam.step || 1
		} else if (inputParam.type === 'list') {
			param[inputParam.name].value = Object.keys(inputParam.options as object)[0] || ''
			param[inputParam.name].default = Object.keys(inputParam.options as object)[0] || ''
		} else if (inputParam.type === 'bool') {
			param[inputParam.name].default = inputParam.default || false
		}

		acc.push(param)
		return acc
	}, [])
	batchSize.value = 1
}

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

	if (!sendToFlowParamsValid.value) {
		const toast = useToast()
		toast.add({
			title: 'Missing required input params',
			description: 'Please, fill in all required input params before sending to sub-flow',
			timeout: 5000,
		})
		selectedTab.value = 1
		return
	}

	// Build target flow input_params_map array with default values
	const input_params_map: any = targetFlow.input_params.reduce((acc: FlowInputParam[], input_param: FlowInputParam) => {
		const input_param_map: any = {}
		let input_param_value: FlowInputParam|any = sendToFlowParamsMapped.value.find((param) => Object.keys(param)[0] === input_param.name)
		input_param_value = input_param_value ? input_param_value[input_param.name].value : null
		if (input_param.type === 'text') {
			input_param_map[input_param.name] = {
				value: input_param_value ?? (input_param.default as string || ''),
				type: input_param.type,
			}
		}
		else if (input_param.type === 'number') {
			input_param_map[input_param.name] = {
				value: input_param_value ?? (input_param.default as number || 0),
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
				value: input_param_value ?? (input_param.default || Object.keys(input_param.options as object)[0] || ''),
				type: input_param.type,
				options: input_param.options,
			}
		} else if (input_param.type === 'bool') {
			input_param_map[input_param.name] = {
				value: input_param_value ?? (input_param.default as boolean || false),
				type: input_param.type
			}
		} else if (['range', 'range_scale'].includes(input_param.type)) {
			input_param_map[input_param.name] = {
				value: input_param_value ?? (input_param.default as number || 0),
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
		batchSize.value,
		props.translatePrompt,
		bindAsChildTask.value,
		bindAsChildTask.value ? Number(props.flowResult.task_id) : null
	)
		.then(() => {
			toast.add({
				title: 'Task sent to sub-flow',
				description: `Task ${props.flowResult.task_id} sent to sub-flow ${selectedFlow.value.value}`,
				timeout: 5000,
			})
		})
		.finally(() => {
			sending.value = false
			emit('update:show', false)
		})
}

const bindAsChildTask = ref(false)
const batchSize = ref(1)
const flowResultReady = computed(() => props.flowResult.progress === 100 && props.flowResult?.error === '')

watch(() => batchSize.value, (value) => {
	if (value > 1 && bindAsChildTask.value) {
		// disable bindAsChildTask if batchSize > 1, not supported
		bindAsChildTask.value = false
	}
})

onMounted(() => {
	const outputType = props.flowResult ? props?.flowResult?.outputs[props.outputParamIndex]?.type ?? 'image' : 'image'
	flowStore.fetchSubFlows(outputType).then(() => {
		selectedFlow.value = subFlows.value[0] || ''
		updateSendToFlowParams(selectedFlow.value)
	})
	bindAsChildTask.value = false
})
</script>

<template>
	<UModal v-model="show" :transition="false">
		<div class="p-4">
			<UTabs v-model="selectedTab" :items="tabs" class="w-full">
				<template #item="{ item }">

					<div class="text-center mb-4">
						<h2 class="text-lg">{{ item.label }}</h2>
						<p v-if="item.description" class="text-sm text-slate-500">{{ item.description }}</p>
					</div>

					<p class="text-md text-center text-red-500 mb-4">
						<USelectMenu
							v-if="subFlows.length > 0"
							v-model="selectedFlow"
							class="w-full"
							searchable
							size="lg"
							:options="subFlows" />
						<span v-else>No sub-flows available</span>
					</p>

					<template v-if="item.key === 'send-to-flow-output'">
						<div class="flex justify-center mb-4">
							<NuxtImg
								v-if="flowResultReady"
								:src="outputImgSrc"
								class="w-1/2 rounded-lg"
								:draggable="false" />
							<UAlert
								v-else
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
					</template>

					<template v-if="item.key === 'send-to-flow-params'">
						<WorkflowSendToFlowParams
							v-if="sendToFlowParamsMapped.length > 0"
							v-model:input-params-map="sendToFlowParamsMapped"
							:flow="selectedSubFlowData"
							:advanced="false" />
						<WorkflowSendToFlowParams
							v-if="sendToFlowParamsMapped.length > 0"
							v-model:input-params-map="sendToFlowParamsMapped"
							:flow="selectedSubFlowData"
							:advanced="true" />
						<UAlert v-if="sendToFlowParamsMapped.length === 0"
							class="mb-4"
							title="No input params"
							description="No input params available for selected sub-flow"
							variant="soft"
							color="primary" />
					</template>


					<UAlert
						v-if="isChildTask"
						class="mb-4"
						icon="i-heroicons-exclamation-circle-solid"
						title="Child task"
						description="The latest child task is always used as input for sub-flow" />
					<UFormGroup v-if="selectedSubFlowData && selectedSubFlowData.is_count_supported" label="Number of results">
						<UInput
							v-model="batchSize"
							type="number"
							min="1"
							max="50"
							label="Batch size"
							class="mb-3 max-w-fit flex justify-end" />
					</UFormGroup>
					<div class="flex items-center justify-between">
						<UTooltip
							:text="batchSize > 1 ? 'Multiple number of results is not supported for child tasks' : ''">
							<UCheckbox v-model="bindAsChildTask"
								label="Bind as child task"
								:disabled="batchSize > 1" />
						</UTooltip>
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

				</template>
			</UTabs>
		</div>
	</UModal>
</template>
