<script setup lang="ts">
useHead({
	title: 'Workers - Visionatrix',
	meta: [
		{
			name: 'description',
			content: 'Workers - Visionatrix',
		},
	],
})

const workersStore = useWorkersStore()
const settingsStore = useSettingsStore()

onMounted(() => {
	workersStore.startPolling()
})

onBeforeUnmount(() => {
	workersStore.stopPolling()
})

const tableHeadersMap = [
	{
		id: 'worker_status',
		label: 'Worker status',
		sortable: true,
	},
	{
		id: 'id',
		label: 'ID',
	},
	{
		id: 'worker_id',
		label: 'Worker ID',
	},
	{
		id: 'worker_version',
		label: 'Worker version',
		sortable: true,
	},
	{
		id: 'last_seen',
		label: 'Last seen',
		sortable: true,
	},
	{
		id: 'tasks_to_give',
		label: 'Tasks to give',
		sortable: false,
	},
	{
		id: 'os',
		label: 'OS',
		sortable: true,
	},
	{
		id: 'version',
		label: 'Python Version',
		sortable: true,
	},
	{
		id: 'device_name',
		label: 'Device name',
	},
	{
		id: 'device_type',
		label: 'Device type',
		sortable: true,
	},
	{
		id: 'vram_total',
		label: 'VRAM total',
		sortable: true,
	},
	{
		id: 'vram_free',
		label: 'VRAM free',
		sortable: true,
	},
	{
		id: 'torch_vram_total',
		label: 'Torch VRAM total',
		sortable: true,
	},
	{
		id: 'torch_vram_free',
		label: 'Torch VRAM free',
		sortable: true,
	},
	{
		id: 'ram_total',
		label: 'RAM total',
		sortable: true,
	},
	{
		id: 'ram_free',
		label: 'RAM free',
		sortable: true,
	},
]

const columns = tableHeadersMap.map((header) => {
	return {
		key: header.id,
		label: header.label,
		sortable: header.sortable || false,
		class: '',
	}
})


const selectedColumnsFromLocalStorage = localStorage.getItem('selectedColumns')
let savedSelectedColumns = null
if (selectedColumnsFromLocalStorage !== null) {
	const selectedColumnsKeys = JSON.parse(selectedColumnsFromLocalStorage)
	savedSelectedColumns = columns.filter((column) => selectedColumnsKeys.includes(column.key))
	savedSelectedColumns.sort(sortColumnsOrder)
}
const selectedColumns = ref(savedSelectedColumns || [...columns])
// TODO: Remove after UTable bug first column removed fix is released in nuxt/ui
selectedColumns.value.unshift({
	key: '',
	label: '',
	sortable: false,
	class: '',
})

// watch for changes in selected columns and save to local storage
watch(selectedColumns, (value: any) => {
	localStorage.setItem('selectedColumns', JSON.stringify(Object.values(columns).filter((column) => value.includes(column)).map((column) => column.key)))
	value.sort(sortColumnsOrder)
})

function sortColumnsOrder(a: any, b: any) {
	return tableHeadersMap.findIndex((header) => header.id === a.key) - tableHeadersMap.findIndex((header) => header.id === b.key)
}

const flowsStore = useFlowsStore()
const flowsAvailableOptions = computed(() => flowsStore.flows.map((flow: Flow) => {
	return {
		label: flow.display_name,
		value: flow.name,
	}
}))
const tasksToGive = ref<any[]>([])
onBeforeMount(() => {
	if (flowsStore.flows.length === 0) {
		flowsStore.fetchFlows().then(() => {
			tasksToGive.value = [...flowsAvailableOptions.value]
		})
		return
	}
	tasksToGive.value = [...flowsAvailableOptions.value]
})
const settingTasksToGive = ref(false)

function updateSelectedTasksToGive() {
	settingTasksToGive.value = true
	Promise.all(selectedRows.value.map((row: any) => {
		return workersStore.setTasksToGive(row.worker_id, tasksToGive.value.map((task: any) => task.value))
	})).then(() => {
		const toast = useToast()
		toast.add({
			title: 'Tasks to give updated',
			description: 'Tasks to give updated successfully',
		})
		selectedRows.value = []
	}).catch(() => {
		const toast = useToast()
		toast.add({
			title: 'Failed to update tasks to give',
			description: 'Try again',
		})
	}).finally(() => {
		settingTasksToGive.value = false
		workersStore.loadWorkers()
	})
}

const filterQuery = ref('')
const rows = computed(() => workersStore.$state.workers)
const rowsFiltered = computed(() => {
	return rows.value.filter((row: WorkerInfo) => {
		return Object.values(row).some((value) => {
			return String(value).toLowerCase().includes(filterQuery.value.toLowerCase())
		})
	})
})

function getWorkerStatus(row: WorkerInfo) {
	const lastSeenDate = new Date(row.last_seen.includes('Z') ? row.last_seen : row.last_seen + 'Z')
	const currentTime = new Date().getTime()
	const timeDifference = currentTime - lastSeenDate.getTime()
	return timeDifference <= 60 * 5 * 1000 ? 'Online' : 'Offline'
}

const selectedRows: any = ref([])
watch(rows, (newRows: WorkerInfo[]) => {
	// restore selected rows after data is updated
	if (selectedRows.value.length > 0) {
		const selectedRowsIds = selectedRows.value.map((row: WorkerInfo) => row.id)
		selectedRows.value = newRows.filter((row: WorkerInfo) => selectedRowsIds.includes(row.id))
	}
})
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<div class="flex flex-col md:flex-row">
			<UVerticalNavigation :links="settingsStore.links" class="md:w-1/5" />
			<div class="px-5 md:w-4/5">
				<h2 class="mb-3 text-xl">Workers</h2>
				<div class="flex flex-col lg:flex-row px-3 py-3.5 border-b border-gray-200 dark:border-gray-700">
					<div class="flex">
						<USelectMenu
							v-model="selectedColumns"
							class="mr-3"
							:options="columns"
							multiple />
						<UInput v-model="filterQuery" placeholder="Filter workers..." />
					</div>
					<div v-if="selectedRows.length >= 1" class="flex flex-col md:flex-row items-center">
						<USelectMenu
							v-model="tasksToGive"
							class="mr-3 my-3 lg:mx-3 lg:my-0 w-full max-w-64 min-w-64"
							:options="flowsAvailableOptions"
							multiple>
							<template #label>
								<span>Tasks to give</span>
							</template>
						</USelectMenu>
						<UTooltip
							text="Flows available for worker to get tasks">
							<UButton
								icon="i-heroicons-check-16-solid"
								variant="outline"
								color="cyan"
								size="sm"
								:loading="settingTasksToGive"
								@click="updateSelectedTasksToGive">
								Update tasks to give
							</UButton>
						</UTooltip>
					</div>
				</div>
				<UTable
					v-model="selectedRows"
					:columns="selectedColumns"
					:rows="filterQuery === '' ? rows : rowsFiltered"
					:loading="workersStore.$state.loading">
					<template #worker_status-data="{ row }">
						<UBadge
							variant="solid"
							:color="getWorkerStatus(row) === 'Online' ? 'green' : 'red'">
							{{ getWorkerStatus(row) }}
						</UBadge>
					</template>
					<template #tasks_to_give-data="{ row }">
						<template v-if="row.tasks_to_give.length === 0">
							<span>All</span>
						</template>
						<template v-else>
							<UPopover :popper="{ placement: 'bottom' }">
								<UButton
									icon="i-heroicons-list-bullet-16-solid"
									variant="outline"
									color="gray"
									size="sm">
									<span>{{ row.tasks_to_give.length }} selected</span>
								</UButton>
								<template #panel>
									<div class="p-4 flex flex-wrap max-w-64 max-h-60 overflow-y-auto">
										<UBadge v-for="task in row.tasks_to_give" :key="task" class="mr-2 mb-2" variant="solid" color="cyan">
											<ULink class="hover:underline" :to="`/workflows/${task}`">
												{{ task }}
											</ULink>
										</UBadge>
									</div>
								</template>
							</UPopover>
						</template>
					</template>
					<template #last_seen-data="{ row }">
						{{ new Date(row.last_seen).toLocaleString() }}
					</template>
					<template #vram_total-data="{ row }">
						{{ formatBytes(row.vram_total) }}
					</template>
					<template #vram_free-data="{ row }">
						{{ formatBytes(row.vram_free) }}
					</template>
					<template #torch_vram_total-data="{ row }">
						{{ formatBytes(row.torch_vram_total) }}
					</template>
					<template #torch_vram_free-data="{ row }">
						{{ formatBytes(row.torch_vram_free) }}
					</template>
					<template #ram_total-data="{ row }">
						{{ formatBytes(row.ram_total) }}
					</template>
					<template #ram_free-data="{ row }">
						{{ formatBytes(row.ram_free) }}
					</template>
				</UTable>
			</div>
		</div>
	</AppContainer>
</template>
