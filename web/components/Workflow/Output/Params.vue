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
})

const hasProfilingDetails = computed(() => {
	return (props.flowResult.execution_details)
		&& props.flowResult.extra_flags !== null
})
const showProfilingDetailsModal = ref(false)
</script>

<template>
	<UTooltip v-if="hasProfilingDetails" text="Show profiling details" :popper="{ placement: 'top' }">
		<UButton
			class="mb-2 mr-2"
			color="orange"
			size="xs"
			variant="outline"
			icon="i-mdi-bug"
			@click="() => {
				showProfilingDetailsModal = true
			}" />
		<UModal v-model="showProfilingDetailsModal">
			<UButton
				class="absolute top-4 right-4"
				icon="i-heroicons-x-mark"
				variant="ghost"
				@click="() => showProfilingDetailsModal = false" />
			<div class="w-full h-full p-4">
				<h3 class="text-center font-bold">
					Profiling details
				</h3>

				<h4 class="mt-2 flex items-center">
					Extra flags
					<UButton
						class="ml-2"
						icon="i-mdi-content-copy"
						variant="outline"
						size="xs"
						color="gray"
						@click="() => {
							const clipboard = useCopyToClipboard()
							clipboard.copy(JSON.stringify(props.flowResult.extra_flags, null, '\t'))
							const toast = useToast()
							toast.add({
								title: 'Clipboard',
								description: 'Extra flags copied to clipboard',
								timeout: 2000,
							})
						}" />
				</h4>
				<div class="mt-4 max-h-96 overflow-y-auto text-sm whitespace-pre-wrap">
					{{ JSON.stringify(props.flowResult.extra_flags, null, '\t') }}
				</div>

				<h4 class="mt-2 flex items-center">
					Execution details
					<UButton
						class="ml-2"
						icon="i-mdi-content-copy"
						variant="outline"
						size="xs"
						color="gray"
						@click="() => {
							const clipboard = useCopyToClipboard()
							clipboard.copy(JSON.stringify(props.flowResult.execution_details, null, '\t'))
							const toast = useToast()
							toast.add({
								title: 'Clipboard',
								description: 'Execution details copied to clipboard',
								timeout: 2000,
							})
						}" />
				</h4>
				<div class="mt-4 max-h-96 overflow-y-auto text-sm whitespace-pre-wrap">
					{{ JSON.stringify(props.flowResult.execution_details, null, '\t') }}
				</div>
			</div>
		</UModal>
	</UTooltip>

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
