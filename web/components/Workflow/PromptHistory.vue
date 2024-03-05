<script setup lang="ts">
const flowStore = useFlowsStore()
const history = computed(() => flowStore.flowPromptHistoryByName(flowStore.currentFlow?.name) || [])

const collapsed = ref(false)
</script>

<template>
	<div class="ring-1 ring-gray-200 dark:ring-gray-800 rounded p-3 my-5">
		<h2 class="text-lg font-bold cursor-pointer select-none flex items-center mb-3" @click="() => {
			collapsed = !collapsed
		}">
			<UIcon :name="collapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
				class="mr-2" />
			Prompts History ({{ history.length }})
		</h2>
		<template v-if="!collapsed">
			<p class="text-sm text-slate-500">No prompts history yet</p>
		</template>
	</div>
</template>
