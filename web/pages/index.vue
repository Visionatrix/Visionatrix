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
		<template v-else-if="flowsStore.flows.length > 0">
			<div v-if="flowsStore.flows.length > flowsStore.$state.pageSize" class="w-full sticky top-1 flex justify-center my-1">
				<UPagination v-model="flowsStore.$state.page" :page-count="flowsStore.$state.pageSize" :total="flowsStore.flows.length" />
			</div>
			<div class="flex flex-wrap justify-center items-center mb-10">
				<WorkflowListItem v-for="flow in flowsStore.paginatedFlows" :key="flow.name" :flow="flow" />
			</div>
		</template>
		<p v-else class="text-center text-slate-500">
			No flows available
		</p>
	</AppContainer>
</template>
