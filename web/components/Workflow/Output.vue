<script setup lang="ts">
import { buildBackendApiUrl } from '~/stores/flows'

defineProps({
	output: Object
})

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
})

onUnmounted(() => {
	flowStore.$state.flow_results_filter = ''
})

const collapsed = ref(false)
</script>

<template>
	<div class="w-full p-4 ring-1 ring-gray-200 dark:ring-gray-800 rounded-lg shadow-md my-10">
		<h2 class="text-lg font-bold cursor-pointer select-none flex items-center mb-3"
			@click="() => {
				collapsed = !collapsed
			}">
			<UIcon :name="collapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
				class="mr-2" />
			Output ({{ results.length }})
		</h2>

		<template v-if="!collapsed">
			<div class="flex flex-col md:flex-row items-center justify-center mb-5 sticky top-0 z-[10]">
				<UInput v-model="flowStore.$state.flow_results_filter"
					icon="i-heroicons-magnifying-glass-20-solid"
					color="white"
					class="md:mr-3"
					:label="'Filter results by prompt'"
					:trailing="true"
					:placeholder="'Filter results by prompt'" />
				<UPagination v-if="results.length > flowStore.$state.resultsPageSize"
					class="my-1 md:my-0"
					v-model="flowStore.$state.resultsPage"
					:page-count="flowStore.$state.resultsPageSize"
					:total="results.length"
					show-first
					show-last />
				<USelect v-if="results.length > flowStore.$state.resultsPageSize"
					v-model="flowStore.resultsPageSize"
					class="md:ml-3 w-fit"
					:options="[5, 10, 20, 50, 100]"
					:label="'Results per page'"
					:placeholder="'Results per page'" />
			</div>
			<div class="results overflow-auto" v-if="hasOutputResult">
				<div v-for="flowResult in flowStore.flowResultsByNamePaginated(flowStore.currentFlow?.name)"
					class="flex flex-col justify-center w-full mx-auto mb-5">
					<div v-if="flowResult.output_params.length === 1" class="img-wrapper h-100">
						<NuxtImg class="mb-2 mx-auto" draggable="false"
							:src="outputImgSrc({
								task_id: flowResult.task_id,
								node_id: flowResult.output_params[0].comfy_node_id
							})" />
					</div>
					<UCarousel v-else
						class="mb-3 rounded-lg overflow-hidden" v-slot="{ item }"
						:items="flowResult.output_params.map((result_output_param) => {
							return { task_id: flowResult.task_id, node_id: result_output_param.comfy_node_id }
						})" 
						:ui="{ item: 'basis-full md:basis-1/2' }"
						:page="1"
						indicators>
						<NuxtImg class="w-full" :src="outputImgSrc(item)"
							draggable="false"/>
					</UCarousel>
					<p class="text-sm text-slate-500 text-center mb-3">
						{{
							flowResult.input_params_mapped ?
							Object.keys(flowResult.input_params_mapped)
							.filter((key) => {
								return flowResult.input_params_mapped[key] !== ''
							})
							.map((key) => {
								return `${key}: ${flowResult.input_params_mapped[key]}`
							}).join(' | ')
							: flowResult.prompt
						}}
					</p>
					<UButton
						class="w-fit mx-auto"
						color="red"
						icon="i-heroicons-trash"
						variant="outline"
						@click="() => flowStore.deleteFlowHistory(flowResult.task_id)">
						Delete image
					</UButton>
				</div>
			</div>
			<p v-else class="text-center text-slate-500">No output results available</p>
		</template>
	</div>
</template>
