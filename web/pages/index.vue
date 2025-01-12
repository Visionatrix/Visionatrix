<script lang="ts" setup>
useHead({
	title: 'Workflows - Visionatrix',
	meta: [
		{
			name: 'description',
			content: 'Workflows - Visionatrix',
		},
	],
})

const flowsStore = useFlowsStore()

watch(() => flowsStore.paginatedFlows, () => {
	if (flowsStore.flows.length <= flowsStore.$state.pageSize) {
		flowsStore.$state.page = 1
	} else if (flowsStore.$state.page > Math.ceil(flowsStore.flows.length / flowsStore.$state.pageSize)) {
		flowsStore.$state.page = Math.ceil(flowsStore.flows.length / flowsStore.$state.pageSize)
	}
})

function getFlowsOptions() {
	return [
		[{
			label: 'Show unsupported flows',
			icon: flowsStore.$state.show_unsupported_flows ? 'i-mdi-filter-check' : 'i-mdi-filter-minus',
			slot: 'show_unsupported_flows',
			click: () => {
				flowsStore.$state.show_unsupported_flows = !flowsStore.$state.show_unsupported_flows
				flowsStore.saveUserOptions()
			},
		}],
		[{
			label: 'Clear filters',
			icon: 'i-mdi-filter-off',
			click: () => {
				flowsStore.$state.flows_search_filter = ''
				flowsStore.$state.flows_tags_filter = []
				flowsStore.$state.show_unsupported_flows = false
			},
		}],
	]
}

const filterEnabled = computed(() => {
	return flowsStore.$state.flows_search_filter
		|| flowsStore.$state.flows_tags_filter.length > 0
		|| flowsStore.$state.show_unsupported_flows
})
const filtersCount = computed(() => {
	return (flowsStore.$state.flows_search_filter ? 1 : 0)
		+ flowsStore.$state.flows_tags_filter.length
		+ (flowsStore.$state.show_unsupported_flows ? 1 : 0)
})
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<UProgress v-if="flowsStore.$state.loading.flows_available || flowsStore.loading.flows_installed || flowsStore.$state.loading.tasks_history" />
		<template v-else>
			<div class="w-full sticky z-[100] top-1 flex flex-col md:flex-row justify-center items-center my-1">
				<UInput
					v-model="flowsStore.$state.flows_search_filter"
					icon="i-heroicons-magnifying-glass-20-solid"
					color="white"
					class="mb-1 md:mr-3 md:mb-0"
					:label="'Filter by prompt'"
					:trailing="true"
					placeholder="Search flows" />
				<UPagination
					v-if="flowsStore.flows.length > flowsStore.$state.pageSize"
					v-model="flowsStore.$state.page"
					class="mb-1 md:mr-3 md:mb-0"
					:page-count="flowsStore.$state.pageSize"
					:total="flowsStore.flows.length" />
				<div class="flex">
					<USelectMenu
						v-model="flowsStore.$state.flows_tags_filter"
						:options="flowsStore.flowsTags"
						multiple
						searchable>
						<template #label>
							<span v-if="flowsStore.$state.flows_tags_filter.length > 0" class="truncate">{{ flowsStore.$state.flows_tags_filter.join(',') }}</span>
							<span v-else>Select tags to filter</span>
						</template>
					</USelectMenu>
					<UDropdown class="ml-2"
						:items="getFlowsOptions()"
						mode="click"
						label="Options">
						<UButton color="white" icon="i-heroicons-ellipsis-vertical-16-solid">
							<span>{{ flowsStore.flows.length }}</span>
							<span v-if="filterEnabled">({{ filtersCount }})</span>
						</UButton>
						<template #show_unsupported_flows>
							<UCheckbox v-model="flowsStore.$state.show_unsupported_flows" />
							<span class="ml-2">Show unsupported flows</span>
						</template>
					</UDropdown>
				</div>
			</div>
			<div v-if="flowsStore.flows.length > 0" class="flex flex-wrap justify-center items-center mb-10">
				<WorkflowListItem v-for="flow in flowsStore.paginatedFlows" :key="flow.name" :flow="flow" />
			</div>
			<p v-else class="text-center text-slate-500 my-5">
				{{ flowsStore.$state.flows_search_filter || flowsStore.$state.flows_tags_filter ? 'No flows found' : 'No flows available' }}
			</p>
		</template>
	</AppContainer>
</template>
