<script setup lang="ts">
const settingsStore = useSettingsStore()

onBeforeMount(() => {
	fetchOrphanModels()
})

function fetchOrphanModels() {
	settingsStore.getOrphanModelsList().then((res: any) => {
		console.debug('[DEBUG] Orphan models: ', res)
		orphanModelsList.value = res
	})
}

const columns = [
	{ key: 'full_path', label: 'Path', sortable: true, class: '' },
	{ key: 'size', label: 'Size', sortable: true, class: '' },
	{ key: 'creation_time', label: 'Created time', sortable: true, class: '' },
	{ key: 'res_model', label: 'Model', sortable: true, class: '' },
	{ key: 'possible_flows', label: 'Possible Flows', sortable: true, class: '' },
	{ key: 'actions', label: 'Actions', sortable: false, class: '' },
]

function deleteSelectedOrphanModels() {
	console.debug('[DEBUG] Deleting orphan models: ', selectedRows)
	deletingOrphanModel.value = true
	Promise.all(selectedRows.value.map((row) => settingsStore.deleteOrphanModel(row.full_path, row.creation_time))).then(() => {
		fetchOrphanModels()
		deletingOrphanModel.value = false
		selectedRows.value = selectedRows.value.filter((row) => row.full_path !== row.full_path)
	}).catch((error: any) => {
		console.error('[ERROR] Failed to delete orphan models: ', error)
		const toast = useToast()
		toast.add({
			title: 'Failed to delete orphan models',
			description: error.details,
		})
		deletingOrphanModel.value = false
	})
}

const orphanModelsList = ref<OrphanModel[]>([])
const selectedRows = ref<OrphanModel[]>([])
const deletingOrphanModel = ref<boolean>(false)

watch(() => settingsStore.settingsMap.comfyui_models_folder.value, () => {
	fetchOrphanModels()
})
</script>

<template>
	<div class="orphan-models">
		<h3 class="text-md font-bold">
			Orphan models <span v-if="orphanModelsList.length > 0" class="text-red-500">({{ orphanModelsList.length }} - {{ formatBytes(orphanModelsList.reduce((acc, model) => acc + model.size, 0)) }})</span>
		</h3>
		<p class="text-gray-500 text-sm">
			Orphan models are models that are not associated with any model type.
			They are not used in any installed flow and can be deleted.
		</p>
		<div v-if="selectedRows.length > 0" class="flex justify-end items-center space-x-2 mt-3">
			<span class="text-gray-500 text-sm">
				Selected: {{ selectedRows.length }} ({{ formatBytes(selectedRows.reduce((acc, row) => acc + row.size, 0)) }})
			</span>
			<UButton
				icon="i-heroicons-trash-16-solid"
				variant="outline"
				color="red"
				:loading="deletingOrphanModel"
				@click="() => {
					deleteSelectedOrphanModels()
				}">
				Delete selected
			</UButton>
		</div>
		<UTable
			v-if="orphanModelsList.length > 0"
			v-model="selectedRows"
			class="mt-5"
			:ui="{
				thead: 'sticky top-0 dark:bg-gray-800 bg-white z-10',
			}"
			:rows="orphanModelsList"
			:columns="columns"
			style="max-height: 40vh;">
			<template #full_path-data="{ row }">
				{{ row.full_path }}
			</template>
			<template #size-data="{ row }">
				{{ row.size ? formatBytes(row.size) : '-' }}
			</template>
			<template #creation_time-data="{ row }">
				{{ row.creation_time ? new Date(row.creation_time * 1000).toLocaleString() : '-' }}
			</template>
			<template #res_model-data="{ row }">
				<a v-if="row.res_model" :href="row.res_model.homepage" target="_blank" class="text-blue-500">{{ row.res_model.name }}</a>
				<span v-else>-</span>
			</template>
			<template #possible_flows-data="{ row }">
				<UPopover>
					<UButton
						icon="i-heroicons-chevron-down-16-solid"
						variant="outline"
						color="blue">
						{{ row.possible_flows.length }}
					</UButton>
					<template #panel>
						<div class="p-4 flex flex-col space-y-2 max-h-60 overflow-y-auto">
							<UButton
								v-for="flow in row.possible_flows"
								:key="flow.id"
								:to="`/workflows/${flow?.name}`"
								variant="soft"
								color="blue"
								target="_blank">
								{{ flow.name }}
							</UButton>
						</div>
					</template>
				</UPopover>
			</template>
			<template #actions-data="{ row }">
				<UButton
					icon="i-heroicons-trash-16-solid"
					variant="outline"
					color="red"
					:loading="deletingOrphanModel"
					:disabled="row.readonly === true"
					@click="() => {
						console.debug('[DEBUG] Deleting orphan model: ', row)
						deletingOrphanModel = true
						settingsStore.deleteOrphanModel(row.full_path, row.creation_time).then(() => {
							fetchOrphanModels()
						}).catch((error) => {
							console.error('[ERROR] Failed to delete orphan model: ', error)
							const toast = useToast()
							toast.add({
								title: 'Failed to delete orphan model',
								description: error.details,
							})
						}).finally(() => {
							deletingOrphanModel = false
						})
					}">
					Delete
				</UButton>
			</template>
		</UTable>
		<span v-else class="text-gray-500">No orphan models found.</span>
	</div>
</template>