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

const links = [
	{
		label: 'Settings',
		icon: 'i-heroicons-cog-6-tooth-20-solid',
		to: '/settings',
	},
	{
		label: 'Workers information',
		icon: 'i-heroicons-chart-bar-16-solid',
		to: '/settings/workers',
	},
]


const tableHeadersMap = [
	{
		text: 'Worker status',
		value: 'worker_status',
		sortable: true,
	},
	{
		text: 'ID',
		value: 'id',
	},
	{
		text: 'Worker ID',
		value: 'worker_id',
	},
	{
		text: 'Worker version',
		value: 'worker_version',
		sortable: true,
	},
	{
		text: 'Last seen',
		value: 'last_seen',
		sortable: true,
	},
	{
		text: 'OS',
		value: 'os',
		sortable: true,
	},
	{
		text: 'Python Version',
		value: 'version',
		sortable: true,
	},
	{
		text: 'Device name',
		value: 'device_name',
	},
	{
		text: 'Device type',
		value: 'device_type',
		sortable: true,
	},
	{
		text: 'VRAM total',
		value: 'vram_total',
		sortable: true,
	},
	{
		text: 'VRAM free',
		value: 'vram_free',
		sortable: true,
	},
	{
		text: 'Torch VRAM total',
		value: 'torch_vram_total',
		sortable: true,
	},
	{
		text: 'Torch VRAM free',
		value: 'torch_vram_free',
		sortable: true,
	},
	{
		text: 'RAM total',
		value: 'ram_total',
		sortable: true,
	},
	{
		text: 'RAM free',
		value: 'ram_free',
		sortable: true,
	},
]

const columns = tableHeadersMap.map((header) => {
	return {
		key: header.value,
		label: header.text,
		sortable: header.sortable || false,
		class: 'whitespace-nowrap',
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
watch(selectedColumns, (value) => {
	localStorage.setItem('selectedColumns', JSON.stringify(Object.values(columns).filter((column) => value.includes(column)).map((column) => column.key)))
	value.sort(sortColumnsOrder)
})

function sortColumnsOrder(a: any, b: any) {
	return tableHeadersMap.findIndex((header) => header.value === a.key) - tableHeadersMap.findIndex((header) => header.value === b.key)
}

const bytesFormattableColumns = ['vram_total', 'vram_free', 'torch_vram_total', 'torch_vram_free', 'ram_total', 'ram_free']

function formatBytes(bytes: number, decimals: number = 2) {
	if (bytes === 0) return '0 Bytes'

	const k = 1024
	const dm = decimals < 0 ? 0 : decimals
	const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

	const i = Math.floor(Math.log(bytes) / Math.log(k))

	return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

const filterQuery = ref('')

const rows = computed(() => {
	const rowsData = workersStore.$state.workers.map((worker: object|any) => {
		// Format bytes columns to human readable format
		Object.keys(worker).forEach((key) => {
			if (bytesFormattableColumns.includes(key) && typeof worker[key] === 'number') {
				worker[key] = formatBytes(worker[key])
			}
			// Set worker_status depending on the last_seen date difference from now to 2 minutes
			worker.worker_status = new Date().getTime() - new Date(worker.last_seen).getTime() < 120000 ? 'Online' : 'Offline'
			if (key === 'last_seen') {
				worker[key] = new Date(worker[key]).toLocaleString()
			}
		})
		return worker
	})

	if (filterQuery.value) {
		return rowsData.filter((row) => {
			return Object.values(row).some((value) => {
				return String(value).toLowerCase().includes(filterQuery.value.toLowerCase())
			})
		})
	}

	return rowsData
})
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<div class="flex flex-col md:flex-row">
			<UVerticalNavigation :links="links" class="md:w-1/5" />
			<div class="px-5 md:w-4/5">
				<h2 class="my-3 text-xl">Workers</h2>
				<div class="flex px-3 py-3.5 border-b border-gray-200 dark:border-gray-700">
					<USelectMenu
						v-model="selectedColumns"
						class="mr-3"
						:options="columns"
						multiple />
					<UInput v-model="filterQuery" placeholder="Filter workers..." />
				</div>
				<UTable :columns="selectedColumns" :rows="rows" :loading="workersStore.$state.loading">
					<template #caption>
						<caption>Workers</caption>
					</template>
				</UTable>
			</div>
		</div>
	</AppContainer>
</template>
