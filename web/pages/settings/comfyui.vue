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
const flowsStore = useFlowsStore()

const showComfyUiFoldersModal = ref(false)
const loadingFoldersListing = ref(false)
const foldersListing = ref([] as ComfyUiFolderListing|ComfyUiFolder[]|any)
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

const hideEmptyFolders = ref(true)
watch(() => settingsStore.localSettings.showComfyUiNavbarButton, () => {
	settingsStore.saveLocalSettings()
})

const settingsKeys = [
	'comfyui_models_folder',
	'comfyui_base_data_folder',
	'comfyui_output_folder',
	'comfyui_input_folder',
	'comfyui_user_folder',
	'remote_vae_flows',
]

const savingSettings = ref(false)
function saveChanges() {
	savingSettings.value = true
	settingsStore.saveChanges(settingsKeys)
		.finally(() => {
			savingSettings.value = false
		})
}

const vaeRemoteDecodingOptions = computed(() => {
	return flowsStore.remoteVaeSupportedFlows.map((flow) => {
		return {
			label: `${flow.display_name} (${flow.name})`,
			value: flow.name,
		}
	})
})

onBeforeMount(() => {
	if (settingsStore.settingsMap.remote_vae_flows.value) {
		settingsStore.settingsMap.remote_vae_flows.value = JSON.parse(settingsStore.settingsMap.remote_vae_flows.value) ?? []
	}
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

						<UDivider class="my-5" />

						<UFormGroup
							size="md"
							class="py-3"
							label="ComfyUI models folder"
							description="Absolute path to the models folders or relative to current Visionatrix folder. Overrides ComfyUI base data folder.">

							<UAlert class="mt-3"
								color="blue"
								variant="solid"
								title="ComfyUI settings changes requires server restart"
								description="Restart Visionatrix server to apply changes"
								icon="i-heroicons-exclamation-triangle" />

							<UInput v-model="settingsStore.settingsMap.comfyui_models_folder.value"
								placeholder="ComfyUI folder path"
								class="w-fit mr-3 mt-3"
								type="text"
								size="sm"
								icon="i-heroicons-folder-16-solid"
								:loading="savingSettings"
								autocomplete="off" />
							<UButton
								icon="i-heroicons-eye"
								class="mt-3"
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
						</UFormGroup>

						<UFormGroup
							size="md"
							class="py-3"
							label="ComfyUI base data folder"
							description="Set the ComfyUI base data directory with an absolute path.">
							<UInput v-model="settingsStore.settingsMap.comfyui_base_data_folder.value"
								placeholder="ComfyUI base data folder path"
								class="w-full"
								type="text"
								size="sm"
								icon="i-heroicons-folder-16-solid"
								:loading="savingSettings"
								autocomplete="off" />
						</UFormGroup>

						<UFormGroup
							size="md"
							class="py-3"
							label="ComfyUI output folder"
							description="Set the ComfyUI output directory with an absolute path. Overrides ComfyUI base data folder.">
							<UInput v-model="settingsStore.settingsMap.comfyui_output_folder.value"
								placeholder="ComfyUI output folder path"
								class="w-full"
								type="text"
								size="sm"
								icon="i-heroicons-folder-16-solid"
								:loading="savingSettings"
								autocomplete="off" />
						</UFormGroup>

						<UFormGroup
							size="md"
							class="py-3"
							label="ComfyUI input folder"
							description="Set the ComfyUI input directory with an absolute path. Overrides ComfyUI base data folder.">
							<UInput v-model="settingsStore.settingsMap.comfyui_input_folder.value"
								placeholder="ComfyUI input folder path"
								class="w-full"
								type="text"
								size="sm"
								icon="i-heroicons-folder-16-solid"
								:loading="savingSettings"
								autocomplete="off" />
						</UFormGroup>

						<UFormGroup
							size="md"
							class="py-3"
							label="ComfyUI user folder"
							description="Set the ComfyUI user directory with an absolute path. Overrides ComfyUI base data folder.">
							<UInput v-model="settingsStore.settingsMap.comfyui_user_folder.value"
								placeholder="ComfyUI user folder path"
								class="w-full"
								type="text"
								size="sm"
								icon="i-heroicons-folder-16-solid"
								:loading="savingSettings"
								autocomplete="off" />
						</UFormGroup>

						<UDivider class="my-5" />

						<UFormGroup
							size="md"
							label="VAE Remote Decoding"
							description="List of installed Flows for which 'VAE Remote Decoding' is enabled">
							<UAlert
								v-if="flowsStore.remoteVaeSupportedFlows.length === 0"
								variant="soft"
								color="teal"
								class="my-3"
								title="No Flows with VAE Remote Decoding support installed"
								icon="i-heroicons-information-circle" />
							<USelectMenu
								v-model="settingsStore.settingsMap.remote_vae_flows.value"
								:options="vaeRemoteDecodingOptions"
								value-attribute="value"
								class="flex h-10"
								multiple
								searchable
								placeholder="Select flows to allow remote VAE decoding" />
						</UFormGroup>

						<UButton
							class="mt-3"
							icon="i-heroicons-check-16-solid"
							:loading="savingSettings"
							@click="saveChanges">
							Save
						</UButton>

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
						v-if="!settingsStore.isNextcloudIntegration"
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
								:to="buildBackendUrl() + '/comfy/'"
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
