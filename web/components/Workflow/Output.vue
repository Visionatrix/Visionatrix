<script setup lang="ts">
const flowStore  = useFlowsStore()

const hasOutputResult = computed(() => flowStore.flowResultsByName(flowStore.currentFlow?.name).length > 0 || false)
const results = computed(() => flowStore.flowResultsByName(flowStore.currentFlow?.name).reverse() || [])
const resultsPerPage = computed(() => flowStore.$state.resultsPageSize)

// watch for total results length and update the page to the last one
watch(results, () => {
	if (results.value.length <= flowStore.$state.resultsPageSize) {
		flowStore.$state.resultsPage = 1
	}
	else if (flowStore.$state.resultsPage > Math.ceil(results.value.length / flowStore.$state.resultsPageSize)) {
		flowStore.$state.resultsPage = Math.ceil(results.value.length / flowStore.$state.resultsPageSize)
	}
})

watch(resultsPerPage, () => {
	if (results.value.length <= flowStore.$state.resultsPageSize) {
		flowStore.$state.resultsPage = 1
	}
	else if (flowStore.$state.resultsPage > Math.ceil(results.value.length / flowStore.$state.resultsPageSize)) {
		flowStore.$state.resultsPage = Math.ceil(results.value.length / flowStore.$state.resultsPageSize)
	}
	flowStore.saveUserOptions()
})

onUnmounted(() => {
	flowStore.$state.flow_results_filter = ''
	flowStore.$state.resultsPage = 1
})

const emit = defineEmits(['copy-prompt-inputs'])

function copyPromptInputs(flowResult: FlowResult) {
	emit('copy-prompt-inputs', flowResult.input_params_mapped)
}

function openImageModal(src: string) {
	modalImageSrc.value = src
	isModalOpen.value = true
}

const outputContainer = ref<HTMLElement|any>(null)
const showScrollToTop = ref(false)

window.addEventListener('scroll', () => {
	showScrollToTop.value = window.scrollY > (outputContainer.value?.offsetTop + window.screen.height || 0)
})

const currentPageNumber = computed(() => {
	return flowStore.$state.resultsPage
})

watch(currentPageNumber, () => {
	const target = document.getElementById('output-container')
	if (target) {
		target.scrollIntoView({ behavior: 'smooth' })
	}
})

const collapsed = ref(false)
const isModalOpen = ref(false)
const modalImageSrc = ref('')
const deleteModalOpen = ref(false)
const deletingFlowResults = ref(false)

const showSendToFlowModal = ref(false)
const sendToImgSrc = ref('')
const sendToFlowResult = ref<FlowResult|TaskHistoryItem|any>(null)
const sendToFlowInputParamsMapped = ref<any>({})
const sendToFlowOutputParamIndex = ref(0)
const sendToFlowIsChildTask = ref(false)

function handleSendToFlow(flowResult: FlowResult, outputIndex: number = 0) {
	showSendToFlowModal.value = true
	if (flowResult.child_tasks.length === 0 || !hasChildTaskByParentTaskNodeId(flowResult, outputIndex, flowResult.outputs[outputIndex].comfy_node_id)) {
		sendToFlowResult.value = flowResult
		sendToImgSrc.value = outputImgSrc({
			task_id: flowResult.task_id,
			node_id: flowResult.outputs[outputIndex].comfy_node_id
		})
		sendToFlowInputParamsMapped.value = flowResult.input_params_mapped
		sendToFlowIsChildTask.value = false
	} else {
		const targetTask = findLatestChildTask(flowResult, outputIndex, flowResult.outputs[outputIndex].comfy_node_id)
		sendToFlowResult.value = targetTask
		sendToFlowInputParamsMapped.value = flowResult.input_params_mapped
		sendToImgSrc.value = outputImgSrc({
			task_id: targetTask.task_id,
			node_id: targetTask.outputs[0].comfy_node_id
		})
		sendToFlowIsChildTask.value = true
	}
	sendToFlowOutputParamIndex.value = outputIndex
}

function buildResultInputParams(flowResult: FlowResult) {
	return [
		'#' + flowResult.task_id,
		...Object.keys(flowResult.input_params_mapped)
			.filter((key) => {
				return flowResult.input_params_mapped[key].value && flowResult.input_params_mapped[key].value !== ''
			})
			.map((key) => {
				return `${flowResult.input_params_mapped[key].display_name}: ${flowResult.input_params_mapped[key].value}`
			}),
	].join(' | ') + `${flowResult.execution_time
		? ' | execution_time: ' + flowResult.execution_time.toFixed(2) + 's'
		: ''
	}`
}

function buildResultDropdownItems(flowResult: FlowResult) {
	const taskDropdownItems = [
		[{
			label: 'Use params',
			labelClass: 'text-cyan-500',
			icon: 'i-heroicons-document-duplicate-16-solid',
			iconClass: 'bg-cyan-500',
			click: () => copyPromptInputs(flowResult),
		}],
		[{
			label: 'Send to flow',
			labelClass: 'text-violet-500',
			icon: 'i-heroicons-arrow-uturn-up-solid',
			iconClass: 'bg-violet-500',
			click: () => {
				handleSendToFlow(flowResult)
			},
			disabled: flowResult.outputs.length !== 1
		}],
		[{
			label: 'Comfy flow',
			labelClass: 'text-blue-500',
			icon: 'i-heroicons-arrow-down-tray',
			iconClass: 'bg-blue-500',
			click: () => flowStore.downloadFlowComfy(flowStore.currentFlow?.name, flowResult.task_id),
		}]
	]
	return taskDropdownItems
}
</script>

<template>
	<div id="output-container"
		ref="outputContainer"
		class="w-full p-4 ring-1 ring-gray-200 dark:ring-gray-800 rounded-lg shadow-md my-10">
		<ScrollToTop :show="showScrollToTop"
			class="fixed bottom-5 right-5"
			target="output-container" />
		<h2 class="text-lg font-bold cursor-pointer select-none flex items-center mb-3"
			@click="() => {
				collapsed = !collapsed
			}">
			<UIcon :name="collapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
				class="mr-2" />
			Output ({{ results.filter((task) => task.parent_task_id === null).length }})
		</h2>

		<template v-if="!collapsed">
			<div class="flex flex-col md:flex-row items-center justify-center mb-5 sticky top-1 z-[10]">
				<UInput v-model="flowStore.$state.flow_results_filter"
					icon="i-heroicons-magnifying-glass-20-solid"
					color="white"
					class="md:mr-3"
					:label="'Filter by prompt'"
					:trailing="true"
					:placeholder="'Filter results by prompt'" />
				<UPagination v-if="results.filter((task) => task.parent_task_id === null).length > flowStore.$state.resultsPageSize"
					v-model="flowStore.$state.resultsPage"
					class="my-1 md:my-0"
					:page-count="flowStore.$state.resultsPageSize"
					:total="results.filter((task) => task.parent_task_id === null).length"
					show-first
					show-last />
				<div class="flex items-center justify-center">
					<USelect v-model="flowStore.resultsPageSize"
						class="md:mx-3 w-fit mr-3"
						:options="[5, 10, 20, 50, 100]"
						:label="'Results per page'" />
					<UDropdown :items="[
						[{
							label: 'Delete all results',
							labelClass: 'text-red-500',
							icon: 'i-heroicons-trash',
							iconClass: 'dark:text-red-500 text-red-500',
							click: () => deleteModalOpen = true,
						}]
					]" mode="click" label="Options" :popper="{ placement: 'bottom-end' }">
						<UButton color="white" icon="i-heroicons-ellipsis-vertical-16-solid" />
					</UDropdown>
				</div>
				<UModal v-model="deleteModalOpen" class="z-[90]" :transition="false">
					<div class="p-4">
						<p class="text-lg text-center mb-4">Are you sure you want to delete all results?</p>
						<p class="text-md text-center text-red-500 mb-4">
							All history and images of
							<UBadge class="mx-1" color="orange" variant="outline">
								{{ flowStore.currentFlow.display_name }}
							</UBadge>
							will be deleted.
						</p>
						<div class="flex justify-center">
							<UButton class="mr-2" color="red" variant="outline" :loading="deletingFlowResults"
								@click="() => {
									deletingFlowResults = true
									flowStore.deleteFlowResults(flowStore.currentFlow?.name).then(() => {
										deletingFlowResults = false
										deleteModalOpen = false
									})
								}">
								Yes
							</UButton>
							<UButton variant="outline" @click="() => deleteModalOpen = false">No</UButton>
						</div>
					</div>
				</UModal>
			</div>
			<div v-if="hasOutputResult" class="results overflow-auto">
				<div v-for="flowResult in flowStore.flowResultsByNamePaginated(flowStore.currentFlow?.name)"
					:id="'task_id_' + flowResult.task_id"
					:key="flowResult.task_id"
					class="flex flex-col justify-center mx-auto mb-5">
					<template v-if="flowResult.outputs.length === 1">
						<WorkflowChildOutput
							v-if="flowResult?.child_tasks && flowResult?.child_tasks.length > 0"
							:flow-result="flowResult"
							:open-image-modal="openImageModal" />
						<NuxtImg v-else-if="flowResult.outputs.length === 1"
							class="mb-2 h-100 mx-auto rounded-lg cursor-pointer"
							draggable="false"
							fit="outside"
							loading="lazy"
							:src="outputImgSrc({
								task_id: flowResult.task_id,
								node_id: flowResult.outputs[0].comfy_node_id
							})"
							@click="openImageModal(outputImgSrc({
								task_id: flowResult.task_id,
								node_id: flowResult.outputs[0].comfy_node_id
							}))" />
					</template>
					<UCarousel v-else-if="flowResult.outputs.length > 1"
						v-slot="{ item }"
						class="mb-3 rounded-lg overflow-hidden"
						:items="flowResult.outputs.map((result_output_param, index) => {
							return {
								task_id: flowResult.task_id,
								node_id: result_output_param.comfy_node_id,
								index,
							}
						})"
						:ui="{
							item: 'basis-full md:basis-1/2',
							indicators: {
								wrapper: 'relative bottom-0 mt-4'
							}
						}"
						:page="1"
						indicators>
						<div class="flex flex-col basis-full">
							<WorkflowChildOutput
								v-if="flowResult?.child_tasks
									&& hasChildTaskByParentTaskNodeId(flowResult, item.index, item.node_id)"
								:flow-result="flowResult"
								:outputs-index="item.index"
								:open-image-modal="openImageModal" />
							<NuxtImg
								v-else
								class="mb-2 h-100 mx-auto rounded-lg cursor-pointer"
								draggable="false"
								fit="outside"
								loading="lazy"
								:src="outputImgSrc(item)"
								@click="openImageModal(outputImgSrc(item))" />
							<UButton
								class="mt-2 w-fit mx-auto"
								icon="i-heroicons-arrow-uturn-up-solid"
								color="violet"
								variant="outline"
								@click="() => {
									handleSendToFlow(flowResult, item.index)
								}">
								Send to flow
							</UButton>
						</div>
					</UCarousel>
					<div class="text-sm text-slate-500 text-center mb-1">
						<div class="w-5/6 mx-auto">
							<UBadge v-for="inputParamStr in buildResultInputParams(flowResult).split('|')"
								:key="inputParamStr"
								class="mr-2 mb-2 last:mr-0 hover:cursor-pointer"
								variant="soft"
								color="gray"
								@click="() => {
									const clipboard = useCopyToClipboard()
									clipboard.copy(inputParamStr)
									const toast = useToast()
									toast.add({
										title: 'Clipboard',
										description: `${inputParamStr.split(':')[0].trim()} copied to clipboard`,
										timeout: 2000,
									})
								}">
								{{ inputParamStr }}
							</UBadge>
						</div>
					</div>
					<div class="w-full flex justify-center items-center">
						<UButton
							class="mr-3"
							color="red"
							icon="i-heroicons-trash"
							variant="outline"
							@click="() => flowStore.deleteFlowHistory(flowResult.task_id)">
							Delete
						</UButton>
						<UDropdown :items="buildResultDropdownItems(flowResult)"
							mode="click"
							:popper="{ placement: 'bottom-start' }">
							<UButton color="white" icon="i-heroicons-ellipsis-vertical-16-solid" />
						</UDropdown>
					</div>
				</div>
				<WorkflowSendToFlowModal
					v-model="showSendToFlowModal"
					:flow-result="sendToFlowResult"
					:output-img-src="sendToImgSrc"
					:output-param-index="sendToFlowOutputParamIndex"
					:input-params-mapped="sendToFlowInputParamsMapped"
					:is-child-task="sendToFlowIsChildTask"
					@update:show="(value) => showSendToFlowModal = value" />
			</div>
			<p v-else class="text-center text-slate-500">
				No output results available
			</p>
		</template>
		<UModal v-model="isModalOpen" class="z-[90]" :transition="false" fullscreen>
			<UButton class="absolute top-4 right-4"
				icon="i-heroicons-x-mark"
				variant="ghost"
				@click="() => isModalOpen = false" />
			<div class="flex items-center justify-center w-full h-full p-4"
				@click.left="() => isModalOpen = false">
				<NuxtImg v-if="modalImageSrc"
					class="lg:h-full"
					fit="inside"
					loading="lazy"
					:src="modalImageSrc" />
			</div>
		</UModal>
	</div>
</template>
