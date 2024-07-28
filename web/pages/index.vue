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
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<UProgress v-if="flowsStore.$state.loading.flows_available || flowsStore.loading.flows_installed || flowsStore.$state.loading.tasks_history" />
		<template v-else>
			<div class="w-full sticky z-[100] top-1 flex flex-col md:flex-row justify-center items-center my-1">
				<USelectMenu
					v-model="flowsStore.$state.flows_tags_filter"
					class="mb-1 md:mr-3 md:mb-0"
					:options="flowsStore.flowsTags"
					multiple
					searchable>
					<template #label>
						<span v-if="flowsStore.$state.flows_tags_filter.length > 0" class="truncate">{{ flowsStore.$state.flows_tags_filter.join(',') }}</span>
						<span v-else>Select tags to filter</span>
					</template>
				</USelectMenu>
				<UPagination
					v-model="flowsStore.$state.page"
					:page-count="flowsStore.$state.pageSize"
					:total="flowsStore.flows.length" />
			</div>
			<div v-if="flowsStore.flows.length > 0" class="flex flex-wrap justify-center items-center mb-10">
				<WorkflowListItem v-for="flow in flowsStore.paginatedFlows" :key="flow.name" :flow="flow" />
			</div>
			<p v-else class="text-center text-slate-500">
				No flows available
			</p>
		</template>
	</AppContainer>
</template>
