<script setup lang="ts">
const flowStore  = useFlowsStore()

const hasOutputResult = computed(() => flowStore.flowResultsByName(flowStore.currentFlow?.name).length > 0 || false)
const results = computed(() => flowStore.flowResultsByName(flowStore.currentFlow?.name).reverse() || [])
const resultsPerPage = computed(() => flowStore.$state.resultsPageSize)

const outputImgSrc = function (result: any) {
	return `${buildBackendApiUrl()}/task-results?task_id=${result.task_id}&node_id=${result.node_id}`
}

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

function openImageModal(src: string) {
	modalImageSrc.value = src
	isModalOpen.value = true
}

const outputContainer = ref<HTMLElement|any>(null)
const showScrollToTop = ref(false)

window.addEventListener('scroll', () => {
	showScrollToTop.value = window.scrollY > (outputContainer.value?.offsetTop + window.screen.height || 0)
})

const collapsed = ref(false)
const isModalOpen = ref(false)
const modalImageSrc = ref('')
const deleteModalOpen = ref(false)
const deletingFlowResults = ref(false)
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
			Output ({{ results.length }})
		</h2>

		<template v-if="!collapsed">
			<div class="flex flex-col md:flex-row items-center justify-center mb-5 sticky top-1 z-[10]">
				<UInput v-model="flowStore.$state.flow_results_filter"
					icon="i-heroicons-magnifying-glass-20-solid"
					color="white"
					class="md:mr-3"
					:label="'Filter results by prompt'"
					:trailing="true"
					:placeholder="'Filter results by prompt'" />
				<UPagination v-if="results.length > flowStore.$state.resultsPageSize"
					v-model="flowStore.$state.resultsPage"
					class="my-1 md:my-0"
					:page-count="flowStore.$state.resultsPageSize"
					:total="results.length"
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
					:key="flowResult.task_id"
					class="flex flex-col justify-center mx-auto mb-5">
					<NuxtImg v-if="flowResult.output_params.length === 1"
						class="mb-2 h-100 mx-auto rounded-lg cursor-pointer" draggable="false"
						fit="outside"
						loading="lazy"
						:src="outputImgSrc({
							task_id: flowResult.task_id,
							node_id: flowResult.output_params[0].comfy_node_id
						})"
						@click="() => openImageModal(outputImgSrc({
							task_id: flowResult.task_id,
							node_id: flowResult.output_params[0].comfy_node_id
						}))" />
					<UCarousel v-else
						v-slot="{ item }"
						class="mb-3 rounded-lg overflow-hidden" 
						:items="flowResult.output_params.map((result_output_param) => {
							return { task_id: flowResult.task_id, node_id: result_output_param.comfy_node_id }
						})"
						:ui="{ item: 'basis-full md:basis-1/2' }"
						:page="1"
						indicators>
						<NuxtImg class="w-full cursor-pointer"
							loading="lazy"
							:src="outputImgSrc(item)"
							draggable="false"
							@click="() => openImageModal(outputImgSrc(item))" />
					</UCarousel>
					<p class="text-sm text-slate-500 text-center mb-3">
						{{
							Object.keys(flowResult.input_params_mapped)
								.filter((key) => {
									return flowResult.input_params_mapped[key] !== ''
								})
								.map((key) => {
									return `${key}: ${flowResult.input_params_mapped[key]}`
								}).join(' | ') 
								+ `${flowResult.execution_time 
									? ' | execution_time: ' + flowResult.execution_time.toFixed(2) + 's' 
									: ''
								}`
						}}
					</p>
					<UButton
						class="w-fit mx-auto"
						color="red"
						icon="i-heroicons-trash"
						variant="outline"
						@click="() => flowStore.deleteFlowHistory(flowResult.task_id)">
						Delete
					</UButton>
				</div>
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
					:src="modalImageSrc" />
			</div>
		</UModal>
	</div>
</template>
