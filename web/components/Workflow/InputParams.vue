<script setup lang="ts">
const props = defineProps({
	inputParamsMap: {
		type: Object,
		required: true,
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
		<h4 class="text-md font-bold cursor-pointer select-none flex items-center mb-3"@click="() => {
			advancedCollapsed = !advancedCollapsed
		}">
			<UIcon :name="advancedCollapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
				class="mr-2" />
			Advanced options
		</h4>
	</div>
	<div v-if="advancedCollapsed">
		<WorkflowInputParam v-for="inputParam, index in flowStore.currentFlow.input_params"
			:key="index"
			:index="index"
			:input-param="inputParam"
			:input-params-map.sync="inputParamsMap"
			:advanced="advanced" />
	</div>
</template>
