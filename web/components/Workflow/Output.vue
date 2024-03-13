<script setup lang="ts">
const config = useRuntimeConfig()
defineProps({
	output: Object
})
const flowStore  = useFlowsStore()

const hasOutputResult = computed(() => flowStore.flowResultsByName(flowStore.currentFlow?.name).length > 0 || false)
const results = computed(() => flowStore.flowResultsByName(flowStore.currentFlow?.name).reverse() || [])

const outputImgSrc = function (result: any) {
	return `${config.app.backendApiUrl}/flow-results?task_id=${result.task_id}&node_id=${result.node_id}`
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


const modalOutputItem = <any>ref(null)
const isModalOpen = ref(false)
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
			<UPagination v-if="results.length > flowStore.$state.resultsPageSize"
				class="mb-5 justify-center sticky top-0"
				v-model="flowStore.$state.resultsPage"
				:page-count="flowStore.$state.resultsPageSize"
				:total="results.length" />
			<div class="progress-queue">
				<UProgress v-for="running in flowStore.flowsRunningByName(flowStore.currentFlow?.name)"
					class="mb-10"
					:value="running?.progress"
					indicator />
			</div>
			<div class="results overflow-auto" v-if="hasOutputResult">
				<div v-for="flowResult in flowStore.flowResultsByNamePaginated(flowStore.currentFlow?.name)"
					class="flex flex-col justify-center w-full mx-auto mb-5">
					<NuxtImg v-if="flowResult.output_params.length === 1"
						class="mb-2 cursor-pointer"
						draggable="false"
						:src="outputImgSrc({ task_id: flowResult.task_id, node_id: flowResult.output_params[0].comfy_node_id})"
						@click="() => {
							modalOutputItem = { task_id: flowResult.task_id, node_id: flowResult.output_params[0].comfy_node_id }
							isModalOpen = true
						}" />
					<UCarousel v-else class="mb-3 rounded-lg" v-slot="{ item }" :items="flowResult.output_params.map((result_output_param) => {
						return { task_id: flowResult.task_id, node_id: result_output_param.comfy_node_id }
					})" :ui="{ item: 'basis-full' }" arrows indicators>
						<NuxtImg class="w-full cursor-pointer" :src="outputImgSrc(item)"
							draggable="false"
							@click="() => {
								modalOutputItem = { task_id: flowResult.task_id, node_id: item.node_id }
								isModalOpen = true
							}" />
					</UCarousel>
					<p class="text-sm text-slate-500 text-center mb-3">{{ flowResult.prompt }}</p>
					<UTooltip class="w-full flex justify-center"
						text="Remove from local results history"
						:popper="{ placement: 'top' }">
						<UButton
							class="w-full flex justify-center"
							color="red"
							icon="i-heroicons-minus"
							variant="outline"
							@click="() => flowStore.deleteFlowHistory(flowResult.task_id)">
							Remove from history
						</UButton>
					</UTooltip>
				</div>
			</div>
			<p v-else class="text-center text-slate-500">No output results available</p>
		</template>

		<UModal v-model="isModalOpen" class="z-[90]" fullscreen>
			<UButton class="absolute top-4 right-4"
				icon="i-heroicons-x-mark"
				variant="ghost"
				@click="() => isModalOpen = false"/>
			<div class="flex items-center justify-center w-full h-full p-4">
				<NuxtImg v-if="modalOutputItem"
					class="lg:h-full"
					:src="outputImgSrc(modalOutputItem)" />
			</div>
		</UModal>
	</div>
</template>

<style scoped>
.results {
	height: 100%;
	min-height: 30vh;
	max-height: 75dvh;
}

.progress-queue {
	height: 100%;
	max-height: 25dvh;
	overflow-y: auto;
}
</style>
