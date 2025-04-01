<script setup lang="ts">
const props = defineProps<{ flow: Flow }>()
const show = defineModel('show', { default: false, type: Boolean })

const toast = useToast()
const flowsStore = useFlowsStore()
const settingsStore = useSettingsStore()
const civitAiStore = useCivitAiStore()
const loading = ref(false)
const loras: any = ref({
	items: [],
	metadata: {},
})

const hasCivitAiToken = computed(() => settingsStore.settingsMap.civitai_auth_token.value !== '')
const token = computed(() => settingsStore.settingsMap.civitai_auth_token.value || '')

const columnsTable = [
	{ key: 'name', label: 'Name', sortable: true, class: '' },
	{ key: 'description', label: 'Description', sortable: false, class: '' },
	{ key: 'trigger_words', label: 'Trigger words', sortable: false, class: '' },
	{ key: 'nsfw', label: 'NSFW', sortable: false, class: '' },
	{ key: 'statsDownloadCount', label: 'Download count', sortable: false, class: '' },
	{ key: 'statsThumbsUpCount', label: 'Thumbs up', sortable: false, class: '' },
	{ key: 'modelVersion', label: 'Model version', sortable: false, class: '' },
	{ key: 'actions', label: 'Actions', sortable: false, class: '' },
]

const selectedRows = ref<ModelApiItem[]>([])
watch(selectedRows, (newSelectedRows, oldSelectedRows) => {
	const deselectedRows = oldSelectedRows.filter((row: ModelApiItem) => {
		return !newSelectedRows.includes(row)
	})
	deselectedRows.forEach((row: ModelApiItem) => {
		if (row.currentFlowLora) {
			removeCurrentLora(row)
		}
	})
})
const expand = ref({
	openedRows: [],
	row: {}
})
const filter = ref('')
const resetFilters = () => {
	filter.value = ''
}

const rows = computed<ModelApiItem[]>(() => {
	let items = loras.value?.items || []

	if (filter.value) {
		items = items.filter((item: ModelApiItem) => {
			return item.name.toLowerCase().includes(filter.value.toLowerCase())
		})
	}

	items.forEach((item: ModelApiItem) => {
		if (!loraSelectedModelVersions.value[item.id] && item?.modelVersions.length > 0) {
			loraSelectedModelVersions.value[item.id] = item?.modelVersions[0].name
		}

		const currentLorasHashes = Object.keys(currentFlowLorasInfo.value)
		item.modelVersions.forEach((v: any) => {
			if (currentLorasHashes.includes(v.files[0].hashes['SHA256'].toLowerCase())
				&& currentFlowLorasInfo.value[v.files[0].hashes['SHA256'].toLowerCase()] !== null) {
				loraSelectedModelVersions.value[item.id] = v.name
				item.currentFlowLora = true
				if (!selectedRows.value.includes(item)) {
					selectedRows.value.push(item)
				}
			}
		})
	})

	return items
})

const loraSelectedModelVersions: any = ref({})

function getModelApiItemImages(row: ModelApiItem) {
	return row.modelVersions.find((v: any) => v.name === loraSelectedModelVersions.value[row.id])?.images
		|| row.modelVersions[0].images || []
}

function getModelApiItemTrainedWords(row: ModelApiItem) {
	return row.modelVersions.find((v: any) => v.name === loraSelectedModelVersions.value[row.id])?.trainedWords
		|| row.modelVersions[0].trainedWords || []
}

const keepPreviousLoras = ref(true)
const newFlowName = ref('')
const newDisplayName = ref(props.flow.display_name)
const newFlowDescription = ref(props.flow.description)
const license = ref(props.flow.license)
const requiredMemoryGb = ref(props.flow.required_memory_gb || 0)
const version = ref(props.flow.version)

function getNewFlowConnectionPoints() {
	const key = Object.keys(props.flow.lora_connect_points)[0]
	const previousLoras = props.flow.lora_connect_points[key].connected_loras

	const previousLorasMapped = previousLoras.filter((lora: any) => {
		// Filter-out if current flow's LORA was deselected
		return currentFlowLorasInfo.value[lora.hash] !== null
	}).map((lora: any) => {
		return {
			display_name: lora.display_name,
			model_url: lora.url,
			strength_model: lora.strength_model,
		}
	})

	const loraConnectionPoints: any = {
		[key]: [],
	}
	if (keepPreviousLoras.value) {
		loraConnectionPoints[key].push(...previousLorasMapped)
	}

	const selectedNewLoras = selectedRows.value.reduce((carry: any[], row: ModelApiItem) => {
		const selectedModelVersion = row.modelVersions.find((v: any) => v.name === loraSelectedModelVersions.value[row.id])
		if (!selectedModelVersion) {
			return carry
		}
		if (currentFlowLorasInfo.value[selectedModelVersion.files[0].hashes['SHA256'].toLowerCase()]) {
			// Skip current flow LORAs
			return carry
		}
		const item = {
			strength_model: 1,
			model_url: selectedModelVersion.downloadUrl,
			display_name: row.name,
		}
		carry.push(item)
		return carry
	}, [])

	loraConnectionPoints[key].push(...selectedNewLoras)

	console.debug('[DEBUG] newFlowConnectionPoints: ', loraConnectionPoints)
	return loraConnectionPoints
}

function removeCurrentLora(row: ModelApiItem) {
	const selectedModelVersion = row.modelVersions.find((v: any) => v.name === loraSelectedModelVersions.value[row.id])
	if (!selectedModelVersion) {
		return
	}
	const hash: string = selectedModelVersion.files[0].hashes['SHA256'].toLowerCase()
	if (currentFlowLorasInfo.value[hash]) {
		currentFlowLorasInfo.value[hash] = null
	}
	const index = selectedRows.value.indexOf(row)
	if (index !== -1) {
		selectedRows.value.splice(index, 1)
	}
	row.currentFlowLora = false
}


const newFlowNameExists = computed(() => {
	return flowsStore.flows.find((flow: Flow) => flow.name === newFlowName.value)
})
const newFlowNameCharactersValid = computed(() => {
	const re = /^[a-z0-9_-]+$/i // Only letters, numbers, dashes and underscores
	return re.test(newFlowName.value)
})
const newFlowNameValid = computed(() => {
	return newFlowName.value !== '' && newFlowNameCharactersValid && !newFlowNameExists.value
})
const newFlowNameValidationError = computed(() => {
	if (newFlowName.value === '') {
		return 'Flow name is required.'
	}
	if (!newFlowNameCharactersValid.value) {
		return 'Flow name can only contain letters, numbers, dashes and underscores.'
	}
	if (newFlowNameExists.value) {
		return 'Flow name already exists.'
	}
	return ''
})

const hasRemovedCurrentLoras = computed(() => {
	return Object.values(currentFlowLorasInfo.value).some((lora: any) => {
		return lora === null
	})
})
const hasSelectedLoras = computed(() => selectedRows.value.filter((row: ModelApiItem) => {
	if (currentFlowLorasInfo.value[row.modelVersions[0].files[0].hashes['SHA256'].toLowerCase()]) {
		return false
	}
	return true
}).length !== 0)

const canClearSelection = computed(() => {
	return hasSelectedLoras.value || hasRemovedCurrentLoras.value
})
const canApplyAndInstall = computed(() => {
	return (hasSelectedLoras.value || hasRemovedCurrentLoras.value)
		&& newFlowNameValid.value
		&& newDisplayName.value !== ''
		&& newFlowDescription.value !== ''
})
const applyButtonTooltip = computed(() => {
	if (!hasSelectedLoras.value) {
		return 'No LoRAs selected'
	}
	if (!newFlowNameValid.value) {
		return 'Please provide a valid flow name.'
	}
	if (newDisplayName.value === '') {
		return 'Please provide a display name.'
	}
	if (newFlowDescription.value === '') {
		return 'Please provide a description.'
	}
	return ''
})

function applyAndInstall() {
	if (selectedRows.value.length === 0 && !hasRemovedCurrentLoras.value) {
		toast.add({
			title: 'No LoRAs selected',
			description: 'Please select at least one LoRA to apply and install.',
		})
		return
	}

	const params = {
		new_name: newFlowName.value,
		new_display_name: newDisplayName.value,
		new_description: newFlowDescription.value,
		new_license: license.value,
		new_required_memory_gb: requiredMemoryGb.value,
		new_version: version.value,
		new_lora_connection_points: getNewFlowConnectionPoints(),
	}

	console.debug('[DEBUG] Clone flow params: ', params)

	loading.value = true
	flowsStore.cloneFlow(props.flow, params).then(() => {
		flowsStore.fetchFlows()
		const router = useRouter()
		toast.add({
			title: 'Flow clone applied',
			actions: [
				{
					label: 'View flow',
					click: () => {
						router.push('/workflows/' + newFlowName.value)
					},
				},
			],
		})
	}).catch((e) => {
		console.error('Error applying and installing flow: ', e.message || 'Unknown error')
		toast.add({
			title: 'Error applying and installing flow',
			description: 'An error occurred while applying and installing the flow. See the console for more details.',
		})
	}).finally(() => {
		loading.value = false
	})
}

const currentFlowLorasInfo = ref<{[hash: string]: any}>({})
function fetchCurrentFlowLorasInfo(force = false) {
	const flowLoras: LoraPoint[] = props.flow.lora_connect_points[Object.keys(props.flow.lora_connect_points)[0]].connected_loras
	console.debug('Flow LORAs: ', flowLoras)

	Promise.all(
		flowLoras.map((lora: any) => {
			return civitAiStore.fetchFlowLorasByHash(props.flow, token.value, lora.hash)?.then((res: ModelApiItem|any) => {
				// force fetch if clearing current changes
				if (!(lora.hash in currentFlowLorasInfo.value) || force) {
					currentFlowLorasInfo.value[lora.hash] = res
				}
				return res
			})
		})
	).then(() => {
		console.debug('Fetched flow LORAs info: ', currentFlowLorasInfo.value)
	}).catch((err: any) => {
		console.error('Error fetching flow LORAs info: ', err)
		toast.add({
			title: 'Error fetching flow LORAs info',
			description: 'An error occurred while fetching LoRAs info for the flow. See the console for more details.',
		})
	})
}

function fetchLoras(nextPage = false) {
	if (!props.flow || !token.value) {
		return
	}

	loading.value = true
	if (!nextPage) {
		fetchCurrentFlowLorasInfo()
	}

	let nextPageUrl = null
	if (nextPage && loras.value.metadata?.nextPage) {
		nextPageUrl = loras.value.metadata.nextPage
	}

	// @ts-ignore
	return civitAiStore.fetchFlowLoras(props.flow, token.value, 50, nextPageUrl).then((res: any) => {
		console.debug('Fetched flow "' + props.flow.name + '" loras: ', res)

		// Filter-out model versions by original flow base model type
		const modelType = props.flow.lora_connect_points[Object.keys(props.flow.lora_connect_points)[0]].base_model_type
		const items = res.items.reduce((carry: ModelApiItem[], item: ModelApiItem) => {
			item.modelVersions = item.modelVersions.filter((v: any) => v.baseModel === modelType)

			if (item.modelVersions.length > 0) {
				if (!loras.value.items.find((i: ModelApiItem) => i.id === item.id)) {
					carry.push(item)
				}
			}

			return carry
		}, [])

		if (items.length === 0) {
			toast.add({
				title: 'No more supported LoRAs',
				description: 'No supported LoRAs available for the flow.',
			})
		}

		loras.value.items.push(...items)
		loras.value.metadata = res.metadata

		return res
	}).catch((err: any) => {
		console.error('Error fetching flow "' + props.flow.name + '" loras: ', err)
		toast.add({
			title: 'Error fetching flow "' + props.flow.name + '" loras',
			description: 'An error occurred while fetching LoRAs for the flow. See the console for more details.',
		})
	}).finally(() => {
		loading.value = false
	})
}
</script>

<template>
	<UModal v-model="show" fullscreen>
		<div class="p-4 overflow-y-auto relative">
			<UButton
				class="absolute top-3 right-3"
				icon="i-heroicons-x-mark"
				variant="ghost"
				@click="() => show = false" />
			<h2 class="text-xl font-bold">Modify flow</h2>
			<p class="text-sm text-slate-500 my-2">
				Select LoRAs to modify the flow. New Flow will be created and installed with selected LoRAs.
			</p>
			<UAlert
				v-if="!hasCivitAiToken"
				class="my-4"
				title="CivitAI token missing"
				description="Please add a CivitAI token in the settings to use this feature."
				variant="soft"
				color="red">
				<template #actions>
					<ULink to="/settings">
						<UButton class="lg:px-3 py-2"
							icon="i-heroicons-arrow-top-right-on-square-16-solid"
							variant="link"
							color="white">
							Go to Settings
						</UButton>
					</ULink>
				</template>
			</UAlert>

			<div v-else>
				<div class="flex flex-col justify-between w-full md:flex-row md:gap-4 md:items-center lg:items-start">
					<UButton
						class="my-1"
						variant="outline"
						icon="i-heroicons-arrow-down-on-square-stack"
						:loading="loading"
						@click="() => {
							loras = {
								items: [],
								metadata: {},
							}
							currentFlowLorasInfo = {}
							resetFilters()
							fetchLoras()
						}">
						Fetch LoRAs models from CivitAI
					</UButton>
					<div class="flex flex-col gap-2 lg:flex-row md:justify-end items-start w-full">
						<UFormGroup label="New flow name"
							class="flex justify-center flex-col w-full"
							:error="newFlowNameValidationError">
							<UInput
								v-model="newFlowName"
								type="text"
								placeholder="unique_flow_name"
								@input="(e: InputEvent|any) => {
									e.target.value = e.target.value.toLowerCase()
									newFlowName = e.target.value.toLowerCase()
								}" />
						</UFormGroup>
						<UFormGroup label="New display name"
							class="flex justify-center flex-col w-full"
							:error="newDisplayName !== '' ? '' : 'Display name is required.'">
							<UInput v-model="newDisplayName" type="text" placeholder="Display name" />
						</UFormGroup>
						<UFormGroup label="New flow description"
							class="flex justify-center flex-col w-full">
							<UInput v-model="newFlowDescription" type="text" placeholder="Description" />
						</UFormGroup>
						<UFormGroup label="License (optional)"
							class="flex justify-center flex-col w-full">
							<UInput v-model="license" type="text" placeholder="License" />
						</UFormGroup>
						<UFormGroup label="Required memory (GB)"
							class="flex justify-center flex-col w-full">
							<UInput v-model="requiredMemoryGb" type="text" placeholder="Required memory (GB)" />
						</UFormGroup>
						<UFormGroup label="Version"
							class="flex justify-center flex-col w-full">
							<UInput v-model="version" type="text" placeholder="Version" />
						</UFormGroup>
					</div>
				</div>


				<UCard
					class="w-full"
					:ui="{
						base: '',
						ring: '',
						divide: 'divide-y divide-gray-200 dark:divide-gray-700',
						header: { padding: 'px-4 py-5' },
						body: { padding: '', base: 'divide-y divide-gray-200 dark:divide-gray-700' },
						footer: { padding: 'p-4' }
					}">
					<div class="flex flex-col md:flex-row flex-wrap gap-2 justify-between items-center w-full px-4 py-3">
						<div class="flex items-center gap-1.5">
							<UInput
								v-model="filter"
								icon="i-heroicons-magnifying-glass-20-solid"
								placeholder="Filter by name..." />
						</div>
						<div class="flex gap-1.5 items-center">
							<UCheckbox v-if="hasSelectedLoras"
								v-model="keepPreviousLoras"
								label="Keep previous LoRAs"
								class="mr-2" />
							<UButton v-if="canClearSelection"
								variant="outline"
								icon="i-heroicons-x-circle"
								color="orange"
								class="mr-2"
								@click="() => {
									selectedRows.splice(0)
									fetchCurrentFlowLorasInfo(true)
								}">
								Clear selection
							</UButton>
							<UTooltip :text="applyButtonTooltip">
								<UButton
									variant="outline"
									icon="i-heroicons-check-16-solid"
									:disabled="!canApplyAndInstall"
									:loading="loading"
									@click="applyAndInstall">
									Apply and install
								</UButton>
							</UTooltip>
						</div>
					</div>
					<UTable v-model="selectedRows"
						v-model:expand="expand"
						:columns="columnsTable"
						:rows="rows"
						:loading="loading"
						:ui="{
							thead: 'sticky top-0 dark:bg-gray-800 bg-white z-10',
							tr: {
								base: 'dark:hover:bg-slate-800',
							},
						}">

						<template #caption>
							<caption class="text-slate-500 text-sm py-1">Only supported LORAs for the basic model type are listed</caption>
						</template>

						<template #select-header="{ indeterminate, checked, change }">
							<div class="flex items-center h-5">
								<input type="checkbox"
									class="h-4 w-4 dark:checked:bg-current dark:checked:border-transparent dark:indeterminate:bg-current dark:indeterminate:border-transparent disabled:opacity-50 disabled:cursor-not-allowed focus:ring-0 focus:ring-transparent focus:ring-offset-transparent form-checkbox rounded bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 focus-visible:ring-2 focus-visible:ring-primary-500 dark:focus-visible:ring-primary-400 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-gray-900 text-primary-500 dark:text-primary-400"
									aria-label="Select row"
									:checked="checked"
									:indeterminate="indeterminate && hasSelectedLoras"
									@change="(e: any) => change(e.target.checked)">
							</div>
						</template>

						<template #name-data="{ row }">
							<a :href="`https://civitai.com/models/${row.id}`" target="_blank" class="text-blue-500 underline">{{ row.name }}</a>
						</template>
						<template #description-data="{ row }">
							<UPopover>
								<UButton
									color="white"
									label="Description"
									trailing-icon="i-heroicons-chevron-down-20-solid" />

								<template #panel>
									<div class="model-description p-4 max-h-64 max-w-xl overflow-y-auto"
										v-html="row.description" />
								</template>
							</UPopover>
						</template>
						<template #trigger_words-data="{ row }">
							<UPopover>
								<UButton
									color="white"
									:label="`Trigger words (${getModelApiItemTrainedWords(row).length})`"
									trailing-icon="i-heroicons-chevron-down-20-solid" />

								<template #panel>
									<div class="p-4 max-h-64 max-w-xl overflow-y-auto">
										<template v-if="getModelApiItemTrainedWords(row).length === 0">
											<p>No trigger words available for this model version.</p>
										</template>
										<template v-else>
											<UBadge
												v-for="word in getModelApiItemTrainedWords(row)"
												:key="word"
												class="flex flex-wrap gap-3 my-1 whitespace-normal"
												:label="word"
												color="white"
												variant="outline" />
										</template>
									</div>
								</template>
							</UPopover>
						</template>
						<template #nsfw-data="{ row }">
							<UTooltip :text="`NSFW level: ${row.nsfwLevel}`"
								class="pl-4">
								<UIcon :name="row.nsfw ? 'i-heroicons-x-circle' : 'i-heroicons-check-circle'"
									:class="{
										'text-red-500': row.nsfw,
										'text-green-500': !row.nsfw,
									}" />
							</UTooltip>
						</template>
						<template #statsThumbsUpCount-data="{ row }">
							<div class="flex items-center">
								<UIcon
									name="i-heroicons-hand-thumb-up-solid"
									class="text-green-500 mr-1" />
								<span>{{ row.stats.thumbsUpCount }}</span>
							</div>
						</template>
						<template #statsDownloadCount-data="{ row }">
							<div class="flex items-center">
								<UIcon
									name="i-heroicons-arrow-down-circle"
									class="text-blue-500 mr-1" />
								<span>{{ row.stats.downloadCount }}</span>
							</div>
						</template>
						<template #modelVersion-data="{ row }">
							<USelectMenu v-model="loraSelectedModelVersions[row.id]"
								:options="row.modelVersions.map((v: any) => {
									return v.name
								})" />
						</template>
						<template #actions-data="{ row }">
							<UButton v-if="!row?.currentFlowLora"
								:icon="selectedRows.includes(row) ? 'i-heroicons-check-16-solid' : 'i-heroicons-plus-16-solid'"
								variant="outline"
								:color="selectedRows.includes(row) ? 'green' : 'white'"
								@click="() => {
									if (selectedRows.includes(row)) {
										selectedRows.splice(selectedRows.indexOf(row), 1)
										return
									}
									selectedRows.push(row)
								}" />
							<UTooltip v-else
								text="Remove previously selected LoRA">
								<UButton
									icon="i-heroicons-minus-16-solid"
									variant="outline"
									color="orange"
									@click="removeCurrentLora(row)" />
							</UTooltip>
						</template>
						<template #expand="{ row }">
							<div v-if="getModelApiItemImages(row).length > 0"
								class="flex justify-center space-x-2 w-full">
								<UCarousel
									v-slot="{ item }"
									class="my-3"
									:items="getModelApiItemImages(row).map((img: any) => {
										return {
											id: img.id,
											url: img.url,
											type: img?.type || 'image',
										}
									})"
									:ui="{
										item: 'mx-1',
									}">
									<NuxtImg
										v-if="item.type === 'image'"
										:src="item.url"
										:height="256"
										:width="256"
										loading="lazy"
										draggable="false" />
									<video v-else
										controls
										:width="256"
										:height="256">
										<source :src="item.url">
									</video>
								</UCarousel>
							</div>
							<UAlert v-else
								title="No images"
								description="No images available for this model version."
								variant="soft"
								color="amber" />
						</template>
					</UTable>
					<template #footer>
						<div class="flex justify-end">
							<UButton
								class="mr-2"
								variant="outline"
								icon="i-heroicons-arrow-down-on-square-stack"
								color="blue"
								:disabled="loras.items.length === 0 || (loras.items.length > 0 && !loras.metadata.nextPage)"
								:loading="loading"
								@click="() => {
									fetchLoras(true)
								}">
								Load more
							</UButton>
						</div>
					</template>
				</UCard>
			</div>
		</div>
	</UModal>
</template>


<style>
.model-description, .model-description > * {
	white-space: normal;
}
</style>
