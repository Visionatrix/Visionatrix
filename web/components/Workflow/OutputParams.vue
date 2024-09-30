<script setup lang="ts">
const props = defineProps({
	flowResult: {
		type: Object as PropType<FlowResult>,
		required: true
	},
})

const inputParams = computed(() => {
	return [
		'#' + props.flowResult.task_id,
		...Object.keys(props.flowResult.input_params_mapped)
			.filter((key) => {
				return props.flowResult.input_params_mapped[key].value && props.flowResult.input_params_mapped[key].value !== ''
			})
			.map((key) => {
				if (showTranslatedParams.value 
					&& props.flowResult.translated_input_params_mapped
					&& props.flowResult.translated_input_params_mapped[key]) {
					return `${props.flowResult.input_params_mapped[key].display_name}: ${props.flowResult.translated_input_params_mapped[key].value}`
				}
				return `${props.flowResult.input_params_mapped[key].display_name}: ${props.flowResult.input_params_mapped[key].value}`
			}),
	].join(' | ') + `${props.flowResult.execution_time
		? ' | execution_time: ' + props.flowResult.execution_time.toFixed(2) + 's'
		: ''
	}`
})
const showTranslatedParams = ref(false)
</script>

<template>
	<UTooltip
		v-if="flowResult.translated_input_params_mapped && Object.keys(flowResult.translated_input_params_mapped).length > 0"
		:text="!showTranslatedParams ? 'Show translated input params' : 'Hide translated input params'"
		:popper="{ placement: 'top' }">
		<UButton
			class="mb-2 mr-2"
			color="white"
			size="xs"
			variant="outline"
			icon="i-heroicons-language-solid"
			@click="() => {
				showTranslatedParams = !showTranslatedParams
			}" />
	</UTooltip>
	<UBadge v-for="inputParamStr in inputParams.split('|')"
		:key="inputParamStr"
		class="mr-2 mb-2 last:mr-0 hover:cursor-pointer"
		variant="soft"
		color="gray"
		@click="() => {
			const clipboard = useCopyToClipboard()
			clipboard.copy(inputParamStr.split(':')[1].trim())
			const toast = useToast()
			toast.add({
				title: 'Clipboard',
				description: `${inputParamStr.split(':')[0].trim()} copied to clipboard`,
				timeout: 2000,
			})
		}">
		{{ inputParamStr }}
	</UBadge>
</template>
