<script setup lang="ts">
const flowStore  = useFlowsStore()
const userStore = useUserStore()

// load input_params_map object from local storage by flow name
let prev_input_params_map: TaskHistoryInputParam|any = localStorage.getItem(`input_params_map_${flowStore.currentFlow?.name}`)
if (prev_input_params_map) {
	const prev_input_params_map_parsed = JSON.parse(prev_input_params_map)
	if ('flow_version' in prev_input_params_map_parsed
		&& prev_input_params_map_parsed.flow_version.split('.')[0] === flowStore.currentFlow?.version.split('.')[0]) {
		prev_input_params_map = prev_input_params_map_parsed
	} else {
		prev_input_params_map = null
		// remove old version of input_params_map from local storage
		localStorage.removeItem(`input_params_map_${flowStore.currentFlow?.name}`)
	}
}

const inputParamsMap: any = ref(flowStore.currentFlow?.input_params.map(input_param => {
	if (input_param.type === 'text') {
		return ({
			[input_param.name]: {
				value: prev_input_params_map !== null && prev_input_params_map[input_param.name] ? prev_input_params_map[input_param.name] : input_param.default as string || '',
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
				default: input_param.default || '',
				translatable: input_param.translatable || false,
				dynamic_lora: input_param.dynamic_lora || false,
				trigger_words: input_param.trigger_words || [],
			}
		})
	} else if (input_param.type === 'number') {
		return ({
			[input_param.name]: {
				value: prev_input_params_map !== null && prev_input_params_map[input_param.name] ? prev_input_params_map[input_param.name] : input_param.default as number || 0,
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
				default: input_param.default || 0,
				dynamic_lora: input_param.dynamic_lora || false,
				trigger_words: input_param.trigger_words || [],
			}
		})
	} else if (input_param.type === 'image') {
		return ({
			[input_param.name]: {
				value: null,
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
				dynamic_lora: input_param.dynamic_lora || false,
				trigger_words: input_param.trigger_words || [],
			}
		})
	} else if (input_param.type === 'image-mask') {
		return ({
			[input_param.name]: {
				value: null,
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
				source_input_name: input_param.source_input_name || null,
				dynamic_lora: input_param.dynamic_lora || false,
				trigger_words: input_param.trigger_words || [],
			}
		})
	} else if (input_param.type === 'list') {
		return ({
			[input_param.name]: {
				value: prev_input_params_map !== null && prev_input_params_map[input_param.name] ? prev_input_params_map[input_param.name] : input_param.default as any || Object.keys(input_param.options as object)[0] || '',
				type: input_param.type,
				optional: input_param.optional,
				options: input_param.options,
				advanced: input_param.advanced || false,
				default: input_param.default || Object.keys(input_param.options as object)[0] || '',
				dynamic_lora: input_param.dynamic_lora || false,
				trigger_words: input_param.trigger_words || [],
			}
		})
	} else if (input_param.type === 'bool') {
		return ({
			[input_param.name]: {
				value: prev_input_params_map !== null && prev_input_params_map[input_param.name] ? prev_input_params_map[input_param.name] : input_param.default as boolean || false,
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
				default: input_param.default || false,
				dynamic_lora: input_param.dynamic_lora || false,
				trigger_words: input_param.trigger_words || [],
			}
		})
	} else if (['range', 'range_scale'].includes(input_param.type)) {
		const param: any = {
			value: prev_input_params_map !== null && prev_input_params_map[input_param.name] ? prev_input_params_map[input_param.name] : input_param.default as number || 0,
			type: input_param.type,
			optional: input_param.optional,
			advanced: input_param.advanced || false,
			min: input_param.min || 0,
			max: input_param.max || 100,
			step: input_param.step || 1,
			default: input_param.default || 0,
			dynamic_lora: input_param.dynamic_lora || false,
			trigger_words: input_param.trigger_words || [],
		}
		if (input_param.type === 'range_scale') {
			param.source_input_name = input_param.source_input_name || null
			if (param.source_input_name === null || param.source_input_name === '') {
				// search for the first required input_param type 'image' to use as source_input_name
				const inputParamImage = flowStore.currentFlow?.input_params.find((input_param: any) => input_param.type === 'image' && !input_param.optional)
				if (inputParamImage) {
					param.source_input_name = inputParamImage.name
				}
			}
		}
		return ({
			[input_param.name]: param
		})
	}
}) || [])

const additionalInputParamsMap: any = ref([])
if (flowStore.currentFlow.is_seed_supported) {
	additionalInputParamsMap.value.push({
		seed: {
			name: 'seed',
			display_name: 'Random seed',
			value: Math.floor(Math.random() * 10000000) as number,
			type: 'number',
			optional: true,
			advanced: true,
			min: 0,
			max: 10000000,
			auto_increment: true,
		}
	})
}
const showAdditionalInputParams = computed(() => {
	return additionalInputParamsMap.value.length > 0 ||
		inputParamsMap.value.some((inputParam: any) => {
			const input_param_name = Object.keys(inputParam)[0]
			return inputParam[input_param_name].advanced
		})
})
const seedAutoIncrementEnabled = computed(() => additionalInputParamsMap.value.find((inputParam: any) => {
	return Object.keys(inputParam)[0] === 'seed'
})?.seed.auto_increment || false)

const settingsStore = useSettingsStore()
const shouldTranslate = ref(flowStore.currentFlow.is_translations_supported
	&& settingsStore.settingsMap.translations_provider.value.trim() !== '')
const surpriseMeSupported = ref(flowStore.currentFlow.is_surprise_me_supported
		&& settingsStore.settingsMap.llm_provider.value.trim() !== ''
)
const translatePrompt: Ref<boolean> = ref(shouldTranslate.value)
onBeforeMount(() => {
	const translatePromptLocal = localStorage.getItem('translatePrompt')
	if (translatePromptLocal) {
		translatePrompt.value = JSON.parse(translatePromptLocal)
	}
})
watch(translatePrompt, (value) => {
	localStorage.setItem('translatePrompt', JSON.stringify(value))
})


function copyPromptInputs(input_params_map: TaskHistoryInputParam) {
	console.debug('Copy prompt inputs', input_params_map)
	Object.keys(input_params_map).forEach((input_param_name: any) => {
		const inputParamIndex = inputParamsMap.value.findIndex((inputParam: any) => Object.keys(inputParam)[0] === input_param_name)
		if (inputParamIndex !== -1) {
			inputParamsMap.value[inputParamIndex][input_param_name].value = input_params_map[input_param_name].value
		}
	})
	const target = document.getElementById('prompt')
	if (target) {
		target.scrollIntoView({ behavior: 'smooth' })
	}
}

defineExpose({
	copyPromptInputs
})

inputParamsMap.value.forEach((inputParam: any) => {
	const input_param_name = Object.keys(inputParam)[0]
	if (!['image', 'image-mask'].includes(inputParam[input_param_name].type)) {
		watch(() => inputParam[input_param_name].value, () => {
			const input_params_map: any = {}
			inputParamsMap.value.forEach((inputParam: any) => {
				const input_param_name = Object.keys(inputParam)[0]
				input_params_map[input_param_name] = inputParam[input_param_name].value
			})
			localStorage.setItem(`input_params_map_${flowStore.currentFlow?.name}`, JSON.stringify({
				...input_params_map,
				flow_version: flowStore.currentFlow?.version
			}))
		})
	}
})

const showResetParams: ComputedRef<boolean> = computed(() => {
	return inputParamsMap.value
		.filter((inputParam: any) => {
			// do not include file inputs
			const input_param_name = Object.keys(inputParam)[0]
			return !['image', 'image-mask'].includes(inputParam[input_param_name].type)
		})
		.some((inputParam: any) => {
			const input_param_name = Object.keys(inputParam)[0]
			return inputParam[input_param_name].value !== inputParam[input_param_name].default
		})
})

function resetParamsToDefaults() {
	inputParamsMap.value.forEach((inputParam: any) => {
		const input_param_name = Object.keys(inputParam)[0]
		if (inputParam[input_param_name].type === 'text') {
			inputParam[input_param_name].value = inputParam[input_param_name].default || ''
		} else if (inputParam[input_param_name].type === 'number') {
			inputParam[input_param_name].value = inputParam[input_param_name].default || inputParam[input_param_name].min || 0
		} else if (inputParam[input_param_name].type === 'list') {
			inputParam[input_param_name].value = inputParam[input_param_name].default || Object.keys(inputParam[input_param_name].options)[0] || ''
		} else if (inputParam[input_param_name].type === 'bool') {
			inputParam[input_param_name].value = inputParam[input_param_name].default || false
		} else if (['range', 'range_scale'].includes(inputParam[input_param_name].type)) {
			inputParam[input_param_name].value = inputParam[input_param_name].default || inputParam[input_param_name].min || 0
		}
	})
}

const running = ref(false)
const batchSize = ref(1)
const collapsed = ref(false)

const requiredInputParamsValid = computed(() => {
	return inputParamsMap.value.every((inputParam: any) => {
		const input_param_name = Object.keys(inputParam)[0]
		if (inputParam[input_param_name].optional) {
			return true
		}

		const input_param_value = inputParam[input_param_name].value

		if (inputParam[input_param_name].type === 'text') {
			return input_param_value !== ''
		} else if (inputParam[input_param_name].type === 'number') {
			return input_param_value >= inputParam[input_param_name].min
				&& input_param_value <= inputParam[input_param_name].max
		} else if (inputParam[input_param_name].type === 'list') {
			return input_param_value !== ''
				&& Object.keys(inputParam[input_param_name].options).includes(input_param_value)
		} else if (inputParam[input_param_name].type === 'bool') {
			return true
		} else if (inputParam[input_param_name].type === 'range') {
			return input_param_value >= inputParam[input_param_name].min
				&& input_param_value <= inputParam[input_param_name].max
		} else if (inputParam[input_param_name].type === 'range_scale') {
			return input_param_value >= inputParam[input_param_name].min
				&& input_param_value <= inputParam[input_param_name].max
		} else if (inputParam[input_param_name].type === 'image') {
			if (inputParam[input_param_name]?.nc_file) {
				return true
			}
			return input_param_value instanceof File && input_param_value.size > 0
		} else if (inputParam[input_param_name].type === 'image-mask') {
			if (inputParam[input_param_name]?.nc_file) {
				return (inputParam[input_param_name]?.mask_applied || false)
			}
			return input_param_value instanceof File && input_param_value.size > 0
				&& (inputParam[input_param_name]?.mask_applied || false)
		}
	})
})

const profilingOptions = ref({
	'X-WORKER-UNLOAD-MODELS': 1,
	'X-WORKER-EXECUTION-PROFILER': 1,
	'X-WORKER-ID': null,
})
const profilingEnabled = ref(false)

watch(() => profilingOptions.value, () => {
	if (!userStore.isAdmin) {
		return
	}
	localStorage.setItem(`profilingOptions_${flowStore.currentFlow?.name}`, JSON.stringify(profilingOptions.value))
}, { deep: true })

function runPrompt(surprise = false) {
	running.value = true
	let headers = {}
	if (userStore.isAdmin && profilingEnabled) {
		headers = Object.fromEntries(
			Object.entries(profilingOptions)
				.filter(([_, value]) => {
					return value !== null
				})
				.map(([key, value]) => {
					if (key === 'X-WORKER-ID') {
						// @ts-ignore
						return [key, value?.value]
					}
					return [key, value]
				})
		)
	}
	flowStore.runFlow(
		flowStore.currentFlow,
		[...inputParamsMap.value, ...additionalInputParamsMap.value],
		seedAutoIncrementEnabled.value ? batchSize.value : 1,
		shouldTranslate.value && translatePrompt.value,
		false, null, surprise,
		headers
	).finally(() => {
		running.value = false
		if (seedAutoIncrementEnabled.value) {
			const seed = additionalInputParamsMap.value.find((inputParam: any) => {
				return Object.keys(inputParam)[0] === 'seed'
			})
			seed.seed.value = Number(seed.seed.value) + batchSize.value + 1
		}
	})
}
</script>

<template>
	<div
		v-if="flowStore.currentFlow"
		id="prompt"
		class="w-full my-10 lg:my-0 p-4 ring-1 ring-gray-200 dark:ring-gray-800 rounded-lg">
		<h2
			class="text-lg font-bold cursor-pointer select-none flex items-center mb-3" @click="() => {
				collapsed = !collapsed
			}">
			<UIcon
				:name="collapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
				class="mr-2" />
			Prompt
		</h2>

		<div v-show="!collapsed">
			<WorkflowPromptInputParams
				v-model:input-params-map="inputParamsMap"
				v-model:additional-input-params-map="additionalInputParamsMap"
				:advanced="false" />
			<WorkflowPromptInputParams
				v-if="showAdditionalInputParams"
				v-model:input-params-map="inputParamsMap"
				v-model:additional-input-params-map="additionalInputParamsMap"
				v-model:profiling-options="profilingOptions"
				v-model:profiling-enabled="profilingEnabled"
				:advanced="true" />

			<UFormGroup v-if="flowStore.currentFlow.is_count_supported" label="Number of results">
				<UInput
					v-model="batchSize"
					type="number"
					min="1"
					max="50"
					label="Batch size"
					:disabled="!seedAutoIncrementEnabled"
					class="mb-3 max-w-fit flex justify-end" />
			</UFormGroup>
			<UFormGroup
				v-if="shouldTranslate"
				class="my-3 flex justify-end">
				<UCheckbox
					v-model="translatePrompt"
					label="Translate prompt" />
			</UFormGroup>
			<div class="flex flex-col md:flex-row" :class="{ 'justify-between': showResetParams, 'justify-end': !showResetParams }">
				<UTooltip v-if="showResetParams" text="Reset input params values to defaults">
					<UButton
						icon="i-heroicons-arrow-path-rounded-square"
						variant="ghost"
						color="amber"
						@click="resetParamsToDefaults">
						Reset params
					</UButton>
				</UTooltip>
				<div class="action flex items-center justify-end">
					<UTooltip v-if="surpriseMeSupported"
						text="Randomize prompt based on your input">
						<UButton
							class="mr-2"
							icon="i-heroicons-gift"
							variant="soft"
							color="blue"
							:loading="running"
							@click="() => runPrompt(true)">
							Surprise me
						</UButton>
					</UTooltip>
					<UButton
						icon="i-heroicons-sparkles-16-solid"
						variant="outline"
						:loading="running"
						:disabled="!requiredInputParamsValid"
						@click="() => runPrompt(false)">
						Run prompt
					</UButton>
				</div>
			</div>
		</div>
	</div>
</template>
