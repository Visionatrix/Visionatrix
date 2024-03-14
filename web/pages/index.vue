<script lang="ts" setup>
useHead({
  title: 'Workflows - AI Media Wizard',
  meta: [
    {
      name: 'description',
      content: 'Workflows - AI Media Wizard',
    },
  ],
})

const flowsStore = useFlowsStore()
</script>

<template>
  <AppContainer class="lg:h-dvh">
    <UProgress v-if="flowsStore.$state.loading.flows_available || flowsStore.loading.flows_installed || flowsStore.$state.loading.tasks_history" />
    <div v-else-if="flowsStore.flows.length > 0"
      class="h-full flex flex-col items-between justify-between">
      <div class="flex flex-wrap justify-center items-center">
        <WorkflowListItem v-for="flow in flowsStore.paginatedFlows" :key="flow.name" :flow="flow" />
      </div>
      <div v-if="flowsStore.flows.length > flowsStore.$state.pageSize" class="w-full flex justify-center my-5">
        <UPagination v-model="flowsStore.$state.page" :page-count="flowsStore.$state.pageSize" :total="flowsStore.flows.length" />
      </div>
    </div>
    <div v-else>
      <p class="text-center text-slate-500">No flows available</p>
    </div>
  </AppContainer>
</template>

<style scoped></style>
