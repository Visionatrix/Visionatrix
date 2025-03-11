<script setup lang="ts">
defineProps({
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
	flow: {
		type: Object as PropType<Flow>,
		required: true,
	},
})

const advancedCollapsed = ref(true)
</script>

<template>
	<div v-if="advanced" class="heading">
		<h4
			class="text-md font-bold cursor-pointer select-none flex items-center mb-3" @click="() => {
				advancedCollapsed = !advancedCollapsed
			}">
			<UIcon
				:name="!advancedCollapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
				class="mr-2" />
			Advanced options
		</h4>
	</div>
	<div v-if="advancedCollapsed">
		<UAlert v-if="flow.input_params.filter((inputParam) => {
				return (inputParam.advanced || false) === advanced && !['image', 'image-mask', 'range_scale'].includes(inputParam.type)
			}).length === 0"
			type="info"
			class="mb-3"
			variant="soft"
			color="cyan"
			:title="advanced ? 'No advanced input params to adjust' : 'No input params to adjust'" />
		<WorkflowSendToFlowInputParam
			v-for="inputParam, index in flow.input_params"
			:key="index"
			:input-params-map="inputParamsMap"
			:index="index"
			:input-param="inputParam"
			:advanced="advanced" />
		<WorkflowSendToFlowInputParam
			v-for="(inputParam, index) in additionalInputParamsMap"
			:key="Object.keys(inputParam)[0]"
			:input-params-map="additionalInputParamsMap"
			:index="index"
			:input-param="inputParam[Object.keys(inputParam)[0]]"
			:advanced="advanced" />
	</div>
</template>
