<script setup lang="ts">
const props = defineProps({
	inputParamsMap: {
		type: Array<any>,
		required: true,
	},
	additionalInputParamsMap: {
		type: Array<any>,
		required: false,
		default: [],
	},
	advanced: {
		type: Boolean,
		default: false,
	},
})

const flowStore = useFlowsStore()

const advancedCollapsed = ref(!props.advanced)
</script>

<template>
	<div v-if="advanced" class="heading">
		<h4 class="text-md font-bold cursor-pointer select-none flex items-center mb-3" @click="() => {
			advancedCollapsed = !advancedCollapsed
		}">
			<UIcon :name="!advancedCollapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
				class="mr-2" />
			Advanced options
		</h4>
	</div>
	<div v-if="advancedCollapsed">
		<WorkflowPromptInputParam v-for="inputParam, index in flowStore.currentFlow.input_params"
			:key="index"
			:input-params-map="inputParamsMap"
			:index="index"
			:input-param="inputParam"
			:advanced="advanced" />
		<WorkflowPromptInputParam v-for="(inputParam, index) in additionalInputParamsMap"
			:key="Object.keys(inputParam)[0]"
			:input-params-map="additionalInputParamsMap"
			:index="index"
			:input-param="inputParam[Object.keys(inputParam)[0]]"
			:advanced="advanced" />
	</div>
</template>
