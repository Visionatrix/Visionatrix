<script setup lang="ts">
useHead({
	title: 'ComfyUI settings - Visionatrix',
	meta: [
		{
			name: 'description',
			content: 'ComfyUI settings - Visionatrix',
		},
	],
})

const userStore = useUserStore()
const settingsStore = useSettingsStore()
const toast = useToast()

const showComfyUiFoldersModal = ref(false)
const loadingFoldersListing = ref(false)
const foldersListing = ref([] as ComfyUiFolderListing|ComfyUiFolder[]|any)
const modelsDir = ref('../vix_models') // default comfyui folder used in Visionatrix
const path = ref('')
const currentFoldersListing = computed(() => {
	if (foldersListing.value.length === 0) {
		return []
	}
	if (path.value === '') {
		return Object.keys(foldersListing.value).map((folderName: string) => {
			let total_size = 0
			if (foldersListing.value[folderName].length > 0) {
				total_size = foldersListing.value[folderName].reduce((acc: number, folder: ComfyUiFolder) => {
					return acc + (folder.total_size ?? 0)
				}, 0)
			}
			return {
				full_path: folderName,
				total_size: total_size,
				create_time: null,
			}
		})
	}
	return foldersListing.value[path.value] as ComfyUiFolder[] ?? []
})
const foldersLinks = computed(() => {
	const links = [{ label: 'Root', to: '' }]
	if (path.value === '') {
		return links
	}
	const pathParts = path.value.split('/')
	let currentPath = ''
	pathParts.forEach((part) => {
		currentPath += part
		links.push({ label: part, to: currentPath })
		currentPath += '/'
	})
	return links
})

const columns = computed(() => {
	const columns = [
		{
			key: 'full_path',
			label: 'Path',
			sortable: true,
			class: '',
		},
		{
			key: 'total_size',
			label: 'Size',
			sortable: true,
			class: '',
		},
	]
	if (path.value !== '') {
		columns.push({
			key: 'create_time',
			label: 'Created time',
			sortable: true,
			class: '',
		})
	}
	return columns
})

function navigateToFolder(folder: ComfyUiFolder) {
	if (folder.full_path in foldersListing.value) {
		path.value = folder.full_path
	}
}

const autoconfigLoading = ref(false)
function performComfyUiAutoconfig(modelsDir: string) {
	if (modelsDir === '') {
		resettingComfyUiFolders.value = true
	} else {
		autoconfigLoading.value = true
	}
	settingsStore.performComfyUiAutoconfig(modelsDir).then((res: any) => {
		if ('folders' in res) {
			console.debug('[DEBUG] ComfyUI folders: ', res.folders)
			settingsStore.loadAllSettings()
			if (modelsDir !== '') {
				foldersListing.value = res.folders
				toast.add({
					title: 'Autoconfig performed',
					description: 'Autoconfig performed successfully',
				})
			} else {
				foldersListing.value = []
				settingsStore.settingsMap.comfyui_models_folder.value = ''
				toast.add({
					title: 'ComfyUI folders reset',
					description: 'ComfyUI folders reset successfully',
				})
			}
		}
	}).catch((error) => {
		toast.add({
			title: 'Error performing autoconfig',
			description: error.details,
		})
	}).finally(() => {
		autoconfigLoading.value = false
		resettingComfyUiFolders.value = false
	})
}

const resettingComfyUiFolders = ref(false)
const hideEmptyFolders = ref(true)

watch(() => settingsStore.localSettings.showComfyUiNavbarButton, () => {
	settingsStore.saveLocalSettings()
})
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<div class="flex flex-col md:flex-row">
			<UVerticalNavigation :links="settingsStore.links" class="md:w-1/5" />
			<div class="px-5 pb-5 md:w-4/5">
				<div v-if="userStore.isAdmin" class="admin-settings mb-3">
					<h3 class="mb-3 text-xl font-bold">ComfyUI settings (global)</h3>

					<div class="mt-3 mb-5">
						<UFormGroup
							size="md"
							class="py-3"
							label="ComfyUI models folder"
							description="Relative or absolute path to the models folders">
							<div v-if="settingsStore.settingsMap.comfyui_models_folder.value === ''">
								<p class="text-gray-500">No ComfyUI folders initialized.</p>
								<UInput v-model="modelsDir"
									placeholder="ComfyUI folder path"
									class="w-fit mt-3"
									type="text"
									size="sm"
									icon="i-heroicons-folder-16-solid"
									:disabled="autoconfigLoading"
									autocomplete="off" />
								<UButton
									class="mt-3"
									icon="i-heroicons-cog-6-tooth-20-solid"
									color="orange"
									:loading="autoconfigLoading"
									@click="() => performComfyUiAutoconfig(modelsDir)">
									Perform autoconfig
								</UButton>
							</div>
							<UButton
								v-if="settingsStore.settingsMap.comfyui_models_folder.value !== ''"
								class="mt-3"
								icon="i-heroicons-folder-16-solid"
								color="cyan"
								@click="() => {
									settingsStore.getComfyUiFolderListing().then((res: any) => {
										console.debug('[DEBUG] ComfyUI folders: ', res)
										foldersListing = res.folders
									})
									showComfyUiFoldersModal = true
								}">
								Show ComfyUI folders
							</UButton>

							<UButton v-if="settingsStore.settingsMap.comfyui_models_folder.value !== ''"
								class="mt-3 ml-2"
								color="red"
								variant="outline"
								icon="i-heroicons-trash-16-solid"
								@click="() => performComfyUiAutoconfig('')">
								Reset ComfyUI folders
							</UButton>
						</UFormGroup>

						<UModal v-if="settingsStore.settingsMap.comfyui_models_folder.value !== ''"
							v-model="showComfyUiFoldersModal"
							class="z-[90]"
							fullscreen>
							<UButton
								class="absolute top-4 right-4"
								icon="i-heroicons-x-mark"
								variant="ghost"
								@click="() => showComfyUiFoldersModal = false" />
							<div class="p-4 max-h-screen">
								<h3 class="text-xl text-center">ComfyUI folders</h3>
								<div>
									<UCheckbox v-model="hideEmptyFolders"
										class="mt-3"
										label="Hide empty folders" />
								</div>

								<UBreadcrumb :links="foldersLinks" class="my-2">
									<template #default="{ link, isActive }">
										<UBadge :color="isActive ? 'primary' : 'gray'"
											class="rounded-full truncate cursor-pointer select-none"
											@click="() => {
												path = link.to
											}">
											{{ link.label }}
										</UBadge>
									</template>
								</UBreadcrumb>

								<UTable
									:loading="loadingFoldersListing"
									:loading-state="{ icon: 'i-heroicons-arrow-path-20-solid', label: 'Loading...' }"
									:rows="currentFoldersListing.filter((folder) => {
										if (hideEmptyFolders) {
											return folder.total_size > 0
										}
										return true
									})"
									:columns="columns"
									style="max-height: 80vh;">
									<template #full_path-data="{ row }">
										<span :class="{ 
												'text-blue-500': row.full_path in foldersListing,
												'cursor-pointer': row.full_path in foldersListing
											}"
											@click="() => navigateToFolder(row)">
											{{ row.full_path }}
										</span>
									</template>
									<template #total_size-data="{ row }">
										{{ row.total_size ? formatBytes(row.total_size): '-' }}
									</template>
									<template #create_time-data="{ row }">
										{{ row.create_time && new Date(row.create_time).getTime() !== 0 ? new Date(row.create_time).toLocaleString() : '-' }}
									</template>
								</UTable>
							</div>
						</UModal>
					</div>

					<UFormGroup
						size="md"
						class="py-3"
						label="Show 'Open ComfyUI' navbar button"
						description="Toggle Navbar button to open ComfyUI in a new tab (Stored in browser local storage	)">
						<div class="flex items-center mt-2">
							<UToggle v-model="settingsStore.localSettings.showComfyUiNavbarButton"
								class="mr-3" />
							<UButton
								icon="i-heroicons-rectangle-group-16-solid"
								variant="outline"
								color="white"
								:to="buildBackendUrl() + '/comfy'"
								target="_blank">
								Open ComfyUI
							</UButton>
						</div>
					</UFormGroup>

					<SettingsOrphanModels class="mt-3" />
				</div>
			</div>
		</div>
	</AppContainer>
</template>
