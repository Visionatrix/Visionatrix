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
const userStore = useUserStore()

onMounted(() => {
	workersStore.startPolling()
})

onBeforeUnmount(() => {
	workersStore.stopPolling()
})

const tableHeadersMap = [
	{
		id: 'actions',
		label: 'Actions',
		sortable: false,
	},
	{
		id: 'worker_status',
		label: 'Worker status',
		sortable: true,
	},
	{
		id: 'federated',
		label: 'Federated',
		sortable: true,
	},
	{
		id: 'busy',
		label: 'Busy',
		sortable: true,
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
	{
		id: 'smart_memory',
		label: 'Smart memory',
		sortable: true,
	},
	{
		id: 'cache_type',
		label: 'Cache type',
		sortable: true,
	},
	{
		id: 'cache_size',
		label: 'Cache size',
		sortable: true,
	},
	{
		id: 'vae_cpu',
		label: 'VAE CPU',
		sortable: true,
	},
	{
		id: 'reserve_vram',
		label: 'Reserve VRAM (GB)',
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
// watch for changes in selected columns and save to local storage
watch(selectedColumns, (value: any) => {
	localStorage.setItem('selectedColumns', JSON.stringify(Object.values(columns).filter((column) => value.includes(column)).map((column) => column.key)))
	value.sort(sortColumnsOrder)
})

function sortColumnsOrder(a: any, b: any) {
	return tableHeadersMap.findIndex((header) => header.id === a.key) - tableHeadersMap.findIndex((header) => header.id === b.key)
}

const flowsStore = useFlowsStore()
const flowsAvailableOptions = computed(() => [
	...flowsStore.$state.flows_installed,
	...flowsStore.$state.flows_available,
].map((flow: Flow) => {
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
const tasksToGiveLabel = computed(() => {
	return tasksToGive.value.length === 0 ? 'All' : tasksToGive.value.length
})
const settingTasksToGive = ref(false)

function updateSelectedTasksToGive() {
	settingTasksToGive.value = true
	Promise.all(selectedRows.value.filter((worker: WorkerInfo) => worker.federated_instance_name === '').map((row: any) => {
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
		const selectedRowsIds = selectedRows.value.map((row: WorkerInfo) => row.worker_id)
		selectedRows.value = newRows.filter((row: WorkerInfo) => selectedRowsIds.includes(row.worker_id))
	}
})

const settingsKeys = [
	'smart_memory',
	'cache_type',
	'cache_size',
	'vae_cpu',
	'reserve_vram',
]
const savingSettings = ref(false)
function saveChanges() {
	savingSettings.value = true
	settingsStore.saveChanges(settingsKeys).finally(() => {
		savingSettings.value = false
	})
}
const showEditWorkerModal = ref(false)
const selectedWorker = ref<WorkerInfo | null>(null)
const openEditWorkerModal = (worker: WorkerInfo) => {
	selectedWorker.value = worker
	showEditWorkerModal.value = true
}
const closeEditWorkerModal = () => {
	showEditWorkerModal.value = false
	selectedWorker.value = null
}
const updatingWorker = ref(false)
const updateSelectedWorkerOptions = () => {
	if (selectedWorker.value) {
		updatingWorker.value = true
		workersStore.updateWorkerOptions(selectedWorker.value.worker_id, {
			smart_memory: selectedWorker.value.smart_memory ?? null,
			cache_type: selectedWorker.value.cache_type ?? null,
			cache_size: selectedWorker.value.cache_size ?? null,
			vae_cpu: selectedWorker.value.vae_cpu ?? null,
			reserve_vram: selectedWorker.value.reserve_vram ?? null,
		}).then(() => {
			const toast = useToast()
			toast.add({
				title: 'Worker options updated',
				description: 'Worker options updated successfully',
			})
			workersStore.loadWorkers()
		}).catch(() => {
			const toast = useToast()
			toast.add({
				title: 'Failed to update worker options',
				description: 'Try again',
			})
		}).finally(() => {
			updatingWorker.value = false
			closeEditWorkerModal()
		})
	}
}
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<div class="flex flex-col md:flex-row">
			<UVerticalNavigation :links="settingsStore.links" class="md:w-1/5" />
			<div class="px-5 md:w-4/5">
				<h2 class="mb-3 text-xl">Workers</h2>

				<div v-if="userStore.isAdmin">
					<UDivider class="mb-3" label="Default Workers settings" />

					<UFormGroup
						size="md"
						class="py-3"
						label="Smart memory"
						description="When disabled forces ComfyUI to aggressively offload to regular RAM instead of keeping models in VRAM when it can.">
						<UCheckbox
							v-model="settingsStore.settingsMap.smart_memory.value"
							color="primary"
							class="py-3"
							label="Enable smart memory" />
					</UFormGroup>

					<UFormGroup
						size="md"
						class="py-3"
						label="Cache type">
						<template #description>
							<p>
								Classic - Use the old style (aggressive) caching. <br>
								LRU - Use LRU caching with a maximum of N node results cached. May use more RAM/VRAM. <br>
								None - Reduced RAM/VRAM usage at the expense of executing every node for each run. <br>
							</p>
						</template>
						<div class="flex w-full items-center my-2">
							<USelectMenu
								v-model="settingsStore.settingsMap.cache_type.value"
								class="w-fit"
								placeholder="Select cache type"
								value-attribute="value"
								:options="settingsStore.settingsMap.cache_type.options" />
						</div>
						<UInput
							v-if="settingsStore.settingsMap.cache_type.value === 'lru'"
							v-model="settingsStore.settingsMap.cache_size.value"
							type="number"
							class="w-fit"
							min="1"
							@change="() => {
								settingsStore.settingsMap.cache_size.value = settingsStore.settingsMap.cache_size.value.toString()
							}" />
					</UFormGroup>

					<UFormGroup
						size="md"
						class="py-3"
						label="VAE cpu"
						description="Run the VAE on the CPU.">
						<UCheckbox
							v-model="settingsStore.settingsMap.vae_cpu.value"
							color="primary"
							class="py-3"
							label="VAE on CPU" />
					</UFormGroup>

					<UFormGroup
						size="md"
						class="py-3"
						label="Reserve VRAM"
						description="Amount of VRAM in GB to reserve for use.">
						<UInput
							v-model="settingsStore.settingsMap.reserve_vram.value"
							type="number"
							min="0"
							step="0.1"
							class="w-fit" />
					</UFormGroup>

					<UButton
						class="mt-3"
						icon="i-heroicons-check-16-solid"
						:loading="updatingWorker"
						@click="saveChanges">
						Save
					</UButton>
				</div>

				<UDivider class="my-3" />

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
							searchable
							class="mr-3 my-3 lg:mx-3 lg:my-0 w-full max-w-64 min-w-64"
							:options="flowsAvailableOptions"
							multiple>
							<template #label>
								<span>Tasks to give ({{ tasksToGiveLabel }})</span>
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
						<UButton
							icon="i-heroicons-x-mark"
							variant="outline"
							color="white"
							class="ml-2"
							@click="() => {
								tasksToGive = []
							}" />
					</div>
				</div>

				<UModal v-model="showEditWorkerModal" :transition="false">
					<div class="p-4 overflow-y-auto relative">
						<h2 class="font-bold">Individual worker configuration options</h2>
						<p class="text-sm text-slate-500">{{ selectedWorker?.worker_id }}</p>

						<div v-if="selectedWorker">
							<UFormGroup
								size="md"
								class="py-3"
								label="Smart memory"
								description="When disabled forces ComfyUI to aggressively offload to regular RAM instead of keeping models in VRAM when it can.">
								<UAlert
									v-if="selectedWorker.smart_memory === null"
									color="cyan"
									variant="soft"
									title="Not set"
									class="mb-2" />
								<div class="flex items-center w-full">
									<UCheckbox
										v-model="selectedWorker.smart_memory"
										color="primary"
										class="py-3"
										label="Enable smart memory" />
									<UButton
										v-if="selectedWorker.smart_memory"
										icon="i-heroicons-x-mark"
										variant="outline"
										color="white"
										class="ml-2"
										@click="() => { 
											if (selectedWorker) {
												// @ts-ignore
												selectedWorker.smart_memory = null
											}
										}" />
								</div>
							</UFormGroup>
							
							<UFormGroup
								size="md"
								class="py-3"
								label="Cache type">
								<template #description>
									<p>
										Classic - Use the old style (aggressive) caching. <br>
										LRU - Use LRU caching with a maximum of N node results cached. May use more RAM/VRAM. <br>
										None - Reduced RAM/VRAM usage at the expense of executing every node for each run. <br>
									</p>
								</template>
								<UAlert
									v-if="selectedWorker.cache_type === null"
									color="cyan"
									variant="soft"
									title="Not set"
									class="mb-2" />
								<div class="flex w-full items-center my-2">
									<USelectMenu
										v-model="selectedWorker.cache_type"
										class="w-fit"
										placeholder="Select cache type"
										value-attribute="value"
										:options="settingsStore.settingsMap.cache_type.options" />
									<UButton
										v-if="selectedWorker.cache_type !== null"
										icon="i-heroicons-x-mark"
										variant="outline"
										color="white"
										class="ml-2"
										@click="() => {
											if (selectedWorker) {
												// @ts-ignore
												selectedWorker.cache_type = null
											}
										}" />
								</div>

								<UAlert
									v-if="selectedWorker.cache_type === 'lru' && selectedWorker.cache_size === null"
									color="cyan"
									variant="soft"
									title="Not set"
									class="mb-2" />
								<div v-if="selectedWorker.cache_type === 'lru'"
									class="flex w-full items-center my-2">
									<UInput
										v-model="selectedWorker.cache_size"
										type="number"
										class="w-fit"
										min="1" />
									<UButton
										v-if="selectedWorker.cache_size !== null"
										icon="i-heroicons-x-mark"
										variant="outline"
										color="white"
										class="ml-2"
										@click="() => { 
											if (selectedWorker) {
												// @ts-ignore
												selectedWorker.cache_size = null
											}
										}" />
								</div>
							</UFormGroup>

							<UFormGroup
								size="md"
								class="py-3"
								label="VAE cpu"
								description="Run the VAE on the CPU.">
								<UAlert
									v-if="selectedWorker.vae_cpu === null"
									color="cyan"
									variant="soft"
									title="Not set"
									class="mb-2" />
								<div class="flex items-center w-full">
									<UCheckbox
										v-model="selectedWorker.vae_cpu"
										color="primary"
										class="py-3"
										label="VAE on CPU" />
									<UButton
										v-if="selectedWorker.vae_cpu"
										icon="i-heroicons-x-mark"
										variant="outline"
										color="white"
										class="ml-2"
										@click="() => {
											if (selectedWorker) {
												// @ts-ignore
												selectedWorker.vae_cpu = null
											}
										}" />
								</div>
							</UFormGroup>

							<UFormGroup
								size="md"
								class="py-3"
								label="Reserve VRAM"
								description="Amount of VRAM in GB to reserve for use.">
								<UAlert
									v-if="selectedWorker.reserve_vram === null"
									color="cyan"
									variant="soft"
									title="Not set"
									class="mb-2" />
								<div class="flex items-center w-full">
									<UInput
										v-model="selectedWorker.reserve_vram"
										type="number"
										min="0"
										step="0.1"
										class="w-fit" />
									<UButton
										v-if="selectedWorker.reserve_vram !== null"
										icon="i-heroicons-x-mark"
										variant="outline"
										color="white"
										class="ml-2"
										@click="() => { 
											if (selectedWorker) {
												// @ts-ignore
												selectedWorker.reserve_vram = null
											}
										}" />
								</div>
							</UFormGroup>
						</div>

						<div class="flex justify-end my-4">
							<UButton
								class="mr-2"
								variant="solid"
								color="green"
								:loading="settingTasksToGive"
								@click="updateSelectedWorkerOptions">
								Save
							</UButton>
							<UButton
								class="mr-2"
								variant="solid"
								color="white"
								@click="closeEditWorkerModal">
								Cancel
							</UButton>
						</div>
					</div>
				</UModal>

				<UTable
					v-model="selectedRows"
					:columns="selectedColumns"
					:rows="filterQuery === '' ? rows : rowsFiltered"
					:loading="workersStore.$state.loading">

					<template #actions-data="{ row }">
						<UButton
							icon="i-heroicons-pencil-16-solid"
							variant="outline"
							color="cyan"
							size="sm"
							@click="() => {
								openEditWorkerModal(row)
							}">
							Edit
						</UButton>
					</template>

					<template #worker_status-data="{ row }">
						<UBadge
							variant="solid"
							:color="getWorkerStatus(row) === 'Online' ? 'green' : 'red'">
							{{ getWorkerStatus(row) }}
						</UBadge>
					</template>
					<template #federated-data="{ row }">
						<UBadge
							variant="solid"
							:color="row.federated_instance_name !== '' ? 'blue' : 'green'">
							{{ row.federated_instance_name !== '' ? 'Yes' : 'No' }}
						</UBadge>
					</template>
					<template #busy-data="{ row }">
						<UBadge
							variant="solid"
							:color="row.empty_task_requests_count === 0 ? 'red' : 'green'">
							{{ row.empty_task_requests_count === 0 ? 'Yes' : 'No' }}
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
					<template #smart_memory-data="{ row }">
						<UBadge
							variant="solid"
							:color="row.smart_memory ? 'green' : 'red'">
							{{ row.smart_memory ? 'Yes' : 'No' }}
						</UBadge>
					</template>
					<template #cache_type-data="{ row }">
						<UBadge
							variant="solid"
							:color="row.cache_type === 'none' ? 'red' : 'green'">
							{{ row.cache_type ?? settingsStore.settingsMap.cache_type.value }}
						</UBadge>
					</template>
					<template #cache_size-data="{ row }">
						{{ row.cache_size && row.cache_type === 'lru' ? row.cache_size + ' nodes' : 'N/A' }}
					</template>
					<template #vae_cpu-data="{ row }">
						<UBadge
							variant="solid"
							:color="row.vae_cpu ? 'green' : 'red'">
							{{ row.vae_cpu ? 'Yes' : 'No' }}
						</UBadge>
					</template>
					<template #reserve_vram-data="{ row }">
						{{ row.reserve_vram ?? 'N/A' }}
					</template>
				</UTable>
			</div>
		</div>
	</AppContainer>
</template>
