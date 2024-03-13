<script setup lang="ts">
const flowStore  = useFlowsStore()
const inputParamsMap: any = ref(flowStore.currentFlow?.input_params.map(input_param => {
	if (input_param.type === 'text') {
		return ({
			[input_param.name]: {
				value: <string>input_param.default || '',
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
			}
		})
	}
	else if (input_param.type === 'number') {
		return ({
			[input_param.name]: {
				value: <number>input_param.default || 0,
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
			}
		})
	}
	else if (input_param.type === 'image') {
		return ({
			[input_param.name]: {
				value: <any>input_param.default || {},
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
			}
		})
	} else if (input_param.type === 'list') {
		return ({
			[input_param.name]: {
				value: <any>Object.keys(<object>input_param.options)[0] || '',
				type: input_param.type,
				optional: input_param.optional,
				options: input_param.options,
				advanced: input_param.advanced || false,
			}
		})
	} else if (input_param.type === 'bool') {
		return ({
			[input_param.name]: {
				value: <boolean>input_param.default || false,
				type: input_param.type,
				optional: input_param.optional,
				advanced: input_param.advanced || false,
			}
		})
	}
}) || [])


const running = ref(false)
const batchSize = ref(1)
const collapsed = ref(false)
</script>

<template>
	<div v-if="flowStore.currentFlow" class="w-full my-10 lg:my-0 p-4 ring-1 ring-gray-200 dark:ring-gray-800 rounded-lg">
		<h2 class="text-lg font-bold cursor-pointer select-none flex items-center mb-3" @click="() => {
			collapsed = !collapsed
		}">
			<UIcon :name="collapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
				class="mr-2" />
			Prompt
		</h2>

		<template v-if="!collapsed">
			<WorkflowInputParams :input-params-map.sync="inputParamsMap" :advanced="false" />
			<WorkflowInputParams v-if="flowStore.currentFlow.input_params.some((input_param: any) => input_param.advanced)"
				:input-params-map.sync="inputParamsMap"
				:advanced="true" />

			<UFormGroup label="Number of images">
				<UInput type="number"
					min="1"
					max="50"
					v-model="batchSize"
					label="Batch size"
					class="mb-3 max-w-fit" />
			</UFormGroup>
			<div class="flex justify-end px-2">
				<UButton icon="i-heroicons-sparkles-16-solid"
					variant="outline"
					:loading="running"
					@click="() => {
						running = true
						// Run prompts according to batch size
						for (let i = 0; i < batchSize; i++) {
							// Increase the seed for each batch prompt
							const seed = inputParamsMap.find((inputParam: any) => {
								const paramName = Object.keys(inputParam)[0]
								return paramName === 'seed'
							})
							if (seed) {
								seed.seed.value = (Number(seed.seed.value) + 1).toString()
							}
							flowStore.runFlow(flowStore.currentFlow, inputParamsMap).then(() => {
								if (i === batchSize - 1)
									running = false
							}).catch(() => {
								running = false
							})
						}
				}">Run prompt</UButton>
			</div>
		</template>
	</div>
</template>
