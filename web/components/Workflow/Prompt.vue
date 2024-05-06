<script setup lang="ts">
const flowStore  = useFlowsStore()

// load input_params_map object from local storage by flow name
let prev_input_params_map: TaskHistoryInputParam|any = localStorage.getItem(`input_params_map_${flowStore.currentFlow?.name}`)
if (prev_input_params_map) {
	prev_input_params_map = JSON.parse(prev_input_params_map)
}

const inputParamsMap: any = ref(flowStore.currentFlow?.input_params.map(input_param => {
	if (input_param.type === 'text') {
		return ({
			[input_param.name]: {
				value: prev_input_params_map !== null ? prev_input_params_map[input_param.name] : input_param.default as string || '',
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
			}
		})
	}
	else if (input_param.type === 'number') {
		return ({
			[input_param.name]: {
				value: prev_input_params_map !== null ? prev_input_params_map[input_param.name] : input_param.default as number || 0,
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
			}
		})
	}
	else if (input_param.type === 'image') {
		return ({
			[input_param.name]: {
				value: prev_input_params_map !== null ? prev_input_params_map[input_param.name] : input_param.default as any || {},
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
			}
		})
	} else if (input_param.type === 'list') {
		return ({
			[input_param.name]: {
				value: prev_input_params_map !== null ? prev_input_params_map[input_param.name] : input_param.default as any || Object.keys(input_param.options as object)[0] || '',
				type: input_param.type,
				optional: input_param.optional,
				options: input_param.options,
				advanced: input_param.advanced || false,
			}
		})
	} else if (input_param.type === 'bool') {
		return ({
			[input_param.name]: {
				value: prev_input_params_map !== null ? prev_input_params_map[input_param.name] : input_param.default as boolean || false,
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
			}
		})
	} else if (['range', 'range_scale'].includes(input_param.type)) {
		const param: any = {
			value: prev_input_params_map !== null ? prev_input_params_map[input_param.name] : input_param.default as number || 0,
			type: input_param.type,
			optional: input_param.optional,
			advanced: input_param.advanced || false,
			min: input_param.min || 0,
			max: input_param.max || 100,
			step: input_param.step || 1,
		}
		if (input_param.type === 'range_scale') {
			param.source_input_name = input_param.source_input_name
		}
		return ({
			[input_param.name]: param
		})
	}
}) || [])

const additionalInputParamsMap: any = ref([
	{
		seed: {
			name: 'seed',
			display_name: 'Random seed',
			value: Math.floor(Math.random() * 1000000) as number,
			type: 'number',
			optional: true,
			advanced: true,
			min: 0,
			max: 10000000,
		}
	}
])

function copyPromptInputs(input_params_map: TaskHistoryInputParam) {
	console.debug('Copy prompt inputs', input_params_map)
	Object.keys(input_params_map).forEach((input_param_name: any) => {
		const inputParamIndex = inputParamsMap.value.findIndex((inputParam: any) => Object.keys(inputParam)[0] === input_param_name)
		if (inputParamIndex !== -1) {
			inputParamsMap.value[inputParamIndex][input_param_name].value = input_params_map[input_param_name]
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
	if (inputParam[input_param_name].type !== 'image') {
		watch(() => inputParam[input_param_name].value, () => {
			const input_params_map: any = {}
			inputParamsMap.value.forEach((inputParam: any) => {
				const input_param_name = Object.keys(inputParam)[0]
				input_params_map[input_param_name] = inputParam[input_param_name].value
			})
			localStorage.setItem(`input_params_map_${flowStore.currentFlow?.name}`, JSON.stringify(input_params_map))
		})
	}
})

const running = ref(false)
const batchSize = ref(1)
const collapsed = ref(false)
</script>

<template>
	<div v-if="flowStore.currentFlow"
		id="prompt"
		class="w-full my-10 lg:my-0 p-4 ring-1 ring-gray-200 dark:ring-gray-800 rounded-lg">
		<h2 class="text-lg font-bold cursor-pointer select-none flex items-center mb-3" @click="() => {
			collapsed = !collapsed
		}">
			<UIcon :name="collapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
				class="mr-2" />
			Prompt
		</h2>

		<div v-show="!collapsed">
			<WorkflowInputParams :input-params-map.sync="inputParamsMap"
				:additional-input-params-map.sync="additionalInputParamsMap"
				:advanced="false" />
			<WorkflowInputParams v-if="flowStore.currentFlow.input_params.some((input_param: any) => input_param.advanced)"
				:input-params-map.sync="inputParamsMap"
				:additional-input-params-map.sync="additionalInputParamsMap"
				:advanced="true" />

			<UFormGroup label="Number of images">
				<UInput v-model="batchSize"
					type="number"
					min="1"
					max="50"
					label="Batch size"
					class="mb-3 max-w-fit flex justify-end" />
			</UFormGroup>
			<div class="flex justify-end px-2">
				<UButton icon="i-heroicons-sparkles-16-solid"
					variant="outline"
					:loading="running"
					@click="() => {
						running = true
						flowStore.runFlow(
							flowStore.currentFlow,
							[...inputParamsMap, ...additionalInputParamsMap],
							batchSize
						).finally(() => {
							running = false
							const seed = additionalInputParamsMap.find((inputParam: any) => {
								return Object.keys(inputParam)[0] === 'seed'
							})
							seed.seed.value = Number(seed.seed.value) + batchSize + 1
						})
					}">
					Run prompt
				</UButton>
			</div>
		</div>
	</div>
</template>
