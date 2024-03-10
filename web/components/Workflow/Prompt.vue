<script setup lang="ts">
defineProps({
	prompt: Object
})

const flowStore  = useFlowsStore()
const inputParamsMap: any = ref(flowStore.currentFlow?.input_params.map(input_param => {
	if (input_param.type === 'text') {
		return ({
			[input_param.name]: {
				value: <any>'',
				type: input_param.type,
				optional: input_param.optional,
			}
		})
	}
	else if (input_param.type === 'number') {
		return ({
			[input_param.name]: {
				value: <any>0,
				type: input_param.type,
				optional: input_param.optional,
			}
		})
	}
	else if (input_param.type === 'image') {
		return ({
			[input_param.name]: {
				value: <any>{},
				type: input_param.type,
				optional: input_param.optional,
			}
		})
	} else if (input_param.type === 'list') {
		return ({
			[input_param.name]: {
				value: <any>Object.keys(<object>input_param.options)[0] || '',
				type: input_param.type,
				optional: input_param.optional,
				options: input_param.options,
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
			<UFormGroup v-for="inputParam, index in flowStore.currentFlow.input_params"
				:label="inputParam.display_name">
				<template #hint>
					<span v-if="!inputParam.optional" class="text-red-300">required</span>
				</template>

				<UTextarea v-if="inputParam.type === 'text'"
					class="mb-3"
					size="md"
					:placeholder="inputParam.display_name"
					:required="!inputParam.optional"
					:resize="true"
					:label="inputParam.display_name"
					:value="inputParamsMap[index][inputParam.name].value"
					variant="outline" @input="(event: InputEvent) => {
						const input = event.target as HTMLTextAreaElement
						inputParamsMap[index][inputParam.name].value = input.value
					}" />

				<UInput v-if="inputParam.type === 'number'"
					type="number"
					class="mb-3"
					:label="inputParam.display_name"
					:required="!inputParam.optional"
					:value="inputParamsMap[index][inputParam.name].value"
					variant="outline" @input="(event: InputEvent) => {
						const input = event.target as HTMLInputElement
						inputParamsMap[index][inputParam.name].value = input.value
					}" />

				<UInput v-if="inputParam.type === 'image'"
					type="file"
					class="mb-3"
					accept="image/*"
					:label="inputParam.display_name"
					@change="(event: Event) => {
						const input = event.target as HTMLInputElement
						const file = input.files?.[0]
						inputParamsMap[index][inputParam.name].value = <File>file
						console.debug('inputParamsMap', inputParamsMap)
					}" />

				<USelectMenu v-if="inputParam.type === 'list'"
					class="mb-3"
					v-model="inputParamsMap[index][inputParam.name].value"
					:placeholder="inputParam.display_name"
					:options="Object.keys(<object>inputParam.options)" />
			</UFormGroup>

			<UFormGroup label="Batch prompts size">
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
