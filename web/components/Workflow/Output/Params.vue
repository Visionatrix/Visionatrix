<script setup lang="ts">
const props = defineProps({
	flowResult: {
		type: Object as PropType<FlowResult>,
		required: true
	},
})

const showTranslatedParams = ref(false)
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

onUnmounted(() => {
	props.flowResult.showInputFiles = false
	props.flowResult.showExecutionDetailsModal = false
})

const hasProfilingDetails = computed(() => {
	return (props.flowResult.execution_details)
		&& props.flowResult.extra_flags !== null
})

const executionDetailsShort = computed(() => {
	const details = { // @ts-ignore
		unload_models: props.flowResult.extra_flags.unload_models, // @ts-ignore
		max_memory_usage: props.flowResult.execution_details.max_memory_usage, // @ts-ignore
		disable_smart_memory: props.flowResult.execution_details.disable_smart_memory, // @ts-ignore
		vram_state: props.flowResult.execution_details.vram_state, // @ts-ignore
	}
	return JSON.stringify(details, null, '\t')
})

function downloadRawDetails() {
	const details = {
		extra_flags: props.flowResult.extra_flags,
		execution_details: props.flowResult.execution_details
	}
	const blob = new Blob([JSON.stringify(details, null, '\t')], { type: 'application/json' })
	const url = URL.createObjectURL(blob)
	const a = document.createElement('a')

	a.href = url
	a.download = `${props.flowResult.task_id}_execution_details.json`
	a.click()
	window.URL.revokeObjectURL(url)
}
</script>

<template>
	<UModal v-if="hasProfilingDetails" v-model="flowResult.showExecutionDetailsModal">
		<UButton
			class="absolute top-4 right-4"
			icon="i-heroicons-x-mark"
			variant="ghost"
			@click="() => flowResult.showExecutionDetailsModal = false" />
		<div class="w-full h-full p-4">
			<h3 class="text-center font-bold">
				Execution details
			</h3>
			<div class="mt-4 max-h-96 overflow-y-auto text-sm whitespace-pre-wrap">
				{{ executionDetailsShort }}
			</div>
			<UButton
				class="mt-3"
				icon="i-heroicons-arrow-down-tray-20-solid"
				variant="outline"
				size="xs"
				color="gray"
				@click="() => downloadRawDetails()">
				Download raw details
			</UButton>
		</div>
	</UModal>

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
	<UBadge
		v-for="inputParamStr in inputParams.split('|')"
		:key="inputParamStr"
		class="mr-2 mb-2 last:mr-0 hover:cursor-pointer"
		variant="soft"
		color="gray"
		@click="() => {
			const clipboard = useCopyToClipboard()
			const index = inputParamStr.indexOf(':')
			const value = inputParamStr.substring(index + 1).trim()
			clipboard.copy(value)
			const toast = useToast()
			toast.add({
				title: 'Clipboard',
				description: `${inputParamStr.split(':')[0].trim()} copied to clipboard`,
				timeout: 2000,
			})
		}">
		{{ inputParamStr }}
	</UBadge>
	<UBadge v-if="flowResult.input_files.length > 0"
		class="mr-2 mb-2 last:mr-0 hover:cursor-pointer select-none"
		variant="subtle"
		color="sky"
		@click="() => {
			flowResult.showInputFiles = !flowResult.showInputFiles
		}">
		<UIcon :name="flowResult.showInputFiles
				? 'i-heroicons-chevron-down'
				: 'i-heroicons-chevron-up'"
			class="mr-1" />
		<UIcon name="i-heroicons-document-solid" class="mr-1" />
		{{ `input_files: ${flowResult.input_files.length}` }}
	</UBadge>
</template>
