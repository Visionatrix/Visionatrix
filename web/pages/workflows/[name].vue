<script setup lang="ts">
const route = useRoute()

const flowStore = useFlowsStore()

flowStore.setCurrentFlow(route.params.name as string)

const installing = computed(() => flowStore.flowInstallingByName(route.params.name as string))
const installingLoading = computed(() => installing.value && installing.value?.progress < 100 || false)
const cancellingInstall = ref(false)
const setupButtonText = computed(() => {
	if (installing.value) {
		if ('error' in installing.value && installing.value?.error !== '') {
			return `${installing.value.progress.toFixed(0)}% Error setting up`
		} else {
			return `${installing.value.progress.toFixed(0)}% Setting up`
		}
	} else {
		return 'Setup flow'
	}
})

const deleting = ref(false)
const showConfirmDelete = ref(false)

const flowActions = computed(() => {
	const actions = [
		[{
			label: 'Delete flow',
			icon: 'i-heroicons-trash',
			click: deleteFlow,
		}]
	]

	if (flowStore?.currentFlow?.new_version_available !== '') {
		actions[0].unshift({
			label: `Update to ${flowStore.currentFlow.new_version_available}`,
			icon: 'i-heroicons-arrow-path',
			click: () => {
				flowStore.updateFlow(flowStore.currentFlow)
			},
		})
	}

	return actions
})

function _deleteFlow(flow: Flow, isFlowPrivate = false) {
	deleting.value = true
	flowStore.deleteFlow(flow).then(() => {
		if (isFlowPrivate) {
			const router = useRouter()
			router.push('/')
		}
	}).finally(() => {
		deleting.value = false
		showConfirmDelete.value = false
	})
}

function deleteFlow() {
	const isFlowPrivate = flowStore.currentFlow?.private || false
	if (isFlowPrivate) {
		showConfirmDelete.value = true
		return
	}
	_deleteFlow(flowStore.currentFlow, isFlowPrivate)
}

const collapsedCard = ref(false)

const workflowPrompt = ref<any>(null)
const copyPromptInputs = function (inputs: any[]) {
	workflowPrompt.value?.copyPromptInputs(inputs)
}

const userStore = useUserStore()

const installedModelsSize = computed(() => {
	return flowStore.currentFlow?.models.filter((model) => model.installed).reduce((acc, model: Model) => acc + model?.file_size || 0, 0)
})
const totalModelsSize = computed(() => {
	return flowStore.currentFlow?.models.reduce((acc, model: Model) => acc + model?.file_size || 0, 0)
})
const modelsSize = computed(() => {
	if (!installedModelsSize.value && !totalModelsSize.value) {
		return ''
	}
	if (installedModelsSize.value === totalModelsSize.value) {
		return ` - ${formatBytes(totalModelsSize.value)}`
	}
	return ` - ${formatBytes(installedModelsSize.value)} / ${formatBytes(totalModelsSize.value)}`
})
</script>

<template>
	<AppContainer>
		<template v-if="!flowStore.loading.flows_available && !flowStore.loading.flows_installed && flowStore.currentFlow && !flowStore.$state.loading.tasks_history">
			<div class="flex flex-col lg:flex-row flex-grow items-start w-full">
				<div class="card-wrapper w-full lg:pr-5">
					<UCard as="div" class="w-full mb-5">
						<template #header>
							<h2
								class="text-xl font-bold cursor-pointer select-none flex items-center" @click="() => {
									collapsedCard = !collapsedCard
								}">
								<UTooltip
									v-if="flowStore.currentFlow?.private || false"
									text="This flow is local, manually added">
									<UIcon
										name="i-heroicons-lock-closed"
										class="mr-2"
										:class="{
											'text-stone-500': !flowStore.currentFlow?.is_supported_by_workers
										}" />
								</UTooltip>
								<UIcon
									:name="collapsedCard ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
									class="mr-2" />
								<UTooltip :text="flowStore.currentFlow?.is_supported_by_workers ? '' : 'No workers capable of running this flow'"
									:popper="{ placement: 'top' }">
									<span :class="{
										'text-stone-500': !flowStore.currentFlow?.is_supported_by_workers
									}">
										{{ flowStore.currentFlow?.display_name }}
									</span>
								</UTooltip>
							</h2>
						</template>

						<div v-if="!collapsedCard" class="p-0 text-sm">
							<p class="flex flex-row items-center text-slate-400 mb-2">
								{{ flowStore.currentFlow?.description }}
							</p>
							<p class="flex flex-row flex-wrap items-center text-md mb-2">
								<UIcon name="i-heroicons-user-16-solid" class="mr-1" />
								<b>Author:</b>&nbsp;
								<a
									class="hover:underline text-md"
									:href="flowStore.currentFlow?.homepage"
									rel="noopener"
									target="_blank">
									{{ flowStore.currentFlow?.author }}
								</a>
							</p>
							<p class="flex flex-row items-center text-md mb-2">
								<UIcon name="i-heroicons-document-text" class="mr-1" />
								<a
									v-if="flowStore.currentFlow?.documentation" class="hover:underline"
									:href="flowStore.currentFlow?.documentation"
									rel="noopener"
									target="_blank">
									Documentation
								</a>
								<span v-else>No documentation</span>
							</p>
							<p class="flex flex-row items-center text-md mb-2">
								<UIcon name="i-heroicons-clock" class="mr-1" />
								<b>Version:</b>&nbsp;
								<span>{{ flowStore.currentFlow?.version }}</span>
								<span v-if="flowStore.currentFlow?.new_version_available !== ''">
									&nbsp;(new version available: {{ flowStore.currentFlow?.new_version_available }})
								</span>
							</p>
							<p class="flex flex-row items-center text-md mb-2">
								<UIcon name="i-heroicons-tag" class="mr-1" />
								<b>Tags:</b>&nbsp;
								<template v-if="flowStore.currentFlow?.tags.length > 0">
									<UBadge
										v-for="tag in flowStore.currentFlow?.tags"
										:key="tag"
										:label="tag"
										color="white"
										variant="solid"
										class="m-1" />
								</template>
								<template v-else>
									<UBadge label="No tags" color="white" variant="solid" class="m-1" />
								</template>
							</p>
							<p
								v-if="flowStore.currentFlow?.models?.length > 0"
								class="flex flex-row flex-wrap items-center text-md mb-2">
								<UIcon name="i-heroicons-arrow-down-on-square-stack" class="mr-1" />
								<UTooltip
									:text="totalModelsSize - installedModelsSize > 0 ? `${formatBytes(totalModelsSize - installedModelsSize)} to download` : 'All models installed'"
									:popper="{ placement: 'top' }">
									<b>Models ({{ flowStore.currentFlow?.models.length }}{{ modelsSize }}):</b>&nbsp;
								</UTooltip>
								<UBadge
									v-for="model in flowStore.currentFlow?.models"
									:key="model.name"
									class="m-1"
									color="white"
									variant="solid">
									<UTooltip :text="model.installed ? 'Model installed' : 'Model not installed'">
										<UIcon
											:name="model.installed ? 'i-heroicons-check-circle-20-solid' : 'i-heroicons-x-mark-20-solid'"
											:class="model.installed ? 'text-green-500' : 'text-orange-500'" />
									</UTooltip>
									<UTooltip
										v-if="model.gated"
										text="Gated model, requires auth token for download"
										:popper="{ placement: 'top' }">
										<UIcon
											name="i-heroicons-key"
											class="mr-1" />
									</UTooltip>
									<a
										class="hover:underline underline-offset-4"
										:href="model.homepage"
										rel="noopener" target="_blank">
										{{ model.name }}
									</a>
									<span v-if="model.file_size">
										({{ formatBytes(model.file_size) }})
									</span>
								</UBadge>
							</p>
							<p class="flex flex-row items-center mb-2">
								<UIcon name="i-mdi-help-network-outline" class="mr-1" />
								<b>Platforms:</b>&nbsp;
								<UTooltip text="Linux">
									<UIcon name="i-mdi-linux" class="mr-1" />
								</UTooltip>
								<UTooltip text="Microsoft Windows">
									<UIcon name="i-mdi-microsoft-windows" class="mr-1" />
								</UTooltip>
								<UTooltip v-if="flowStore.currentFlow.is_macos_supported" text="macOS">
									<UIcon name="i-mdi-apple" class="mr-1" />
								</UTooltip>
								<UTooltip v-if="flowStore.currentFlow?.required_memory_gb"
									class="flex flex-row items-center"
									text="Required VRAM memory (GB)">
									(<UIcon name="i-mdi-memory" class="mr-1" />
									<span>{{ flowStore.currentFlow?.required_memory_gb }} GB</span>)
								</UTooltip>
							</p>
							<p
								v-if="flowStore.currentFlow?.requires?.length > 0"
								class="flex flex-row flex-wrap items-center text-md">
								<b>Requires:</b>&nbsp;
								<UBadge
									v-for="requirement in flowStore.currentFlow?.requires"
									:key="requirement"
									class="m-1"
									color="yellow"
									variant="outline">
									{{ requirement }}
								</UBadge>
							</p>
						</div>

						<template v-if="!collapsedCard" #footer>
							<div v-if="userStore.isAdmin" class="flex justify-end">
								<div class="flex flex-row items-center justify-center text-sm mr-2">
									<UIcon
										:name="flowStore.isFlowInstalled(route.params.name as string) ?
											'i-heroicons-check-badge'
											: 'i-heroicons-x-mark'"
										class="mx-1" />
									<span
										:class="{
											'text-green-500': flowStore.isFlowInstalled(route.params.name as string),
											'text-red-500': !flowStore.isFlowInstalled(route.params.name as string),
											'text-stone-500': flowStore.isFlowInstalled(route.params.name as string) && !flowStore.currentFlow?.is_supported_by_workers
										}">
										{{ 
											flowStore.isFlowInstalled(route.params.name as string)
												? flowStore.currentFlow?.is_supported_by_workers
													? 'Installed'
													: 'Installed (no workers)'
												: 'Not installed' 
										}}
									</span>
								</div>
								<UTooltip
									v-if="!flowStore.isFlowInstalled(route.params.name as string)"
									text="Setup flow dependencies and configure it in ComfyUI"
									:popper="{ placement: 'top' }" :open-delay="500">
									<UButton
										icon="i-heroicons-arrow-down-tray"
										class="mx-3"
										color="primary"
										variant="outline"
										:loading="installingLoading"
										@click="() => flowStore.setupFlow(flowStore.currentFlow)">
										{{ setupButtonText }}
									</UButton>
								</UTooltip>
								<UTooltip
									v-if="!flowStore.isFlowInstalled(route.params.name as string) && installingLoading"
									text="Cancel flow installation"
									:popper="{ placement: 'top' }" :open-delay="500">
									<UButton
										icon="i-heroicons-stop"
										variant="outline"
										color="orange"
										:loading="cancellingInstall"
										@click="() => {
											cancellingInstall = true
											flowStore.cancelFlowSetup(flowStore.currentFlow).then(() => {
												cancellingInstall = false
											})
										}">
										Cancel
									</UButton>
								</UTooltip>
								<UDropdown
									v-if="flowStore.isFlowInstalled(route.params.name as string)"
									:items="flowActions"
									mode="click"
									label="Actions"
									:popper="{ placement: 'bottom-end' }">
									<UButton color="white" label="Actions" trailing-icon="i-heroicons-chevron-down-20-solid" />
								</UDropdown>
							</div>
							<div v-else>
								<div class="text-sm flex justify-end">
									<div class="flex flex-row items-center justify-center text-sm mr-3">
										<UIcon
											:name="flowStore.isFlowInstalled(route.params.name as string) ?
												'i-heroicons-check-badge'
												: 'i-heroicons-x-mark'"
											class="mx-1" />
										<span
											:class="{
												'text-green-500': flowStore.isFlowInstalled(route.params.name as string),
												'text-red-500': !flowStore.isFlowInstalled(route.params.name as string),
											}">
											{{ flowStore.isFlowInstalled(route.params.name as string) ? 'Installed' : 'Not installed' }}
										</span>
									</div>
									<div v-if="!flowStore.isFlowInstalled(route.params.name as string)" class="text-right">
										<p class="text-orange-500">Only admin can manage workflows.</p>
										<span class="text-slate-500">Ask your admin to setup this workflow</span>
									</div>
								</div>
							</div>
						</template>
					</UCard>
				</div>
				<div class="prompt-wrapper w-full">
					<WorkflowPrompt
						v-if="!deleting && flowStore.isFlowInstalled(route.params.name as string)"
						ref="workflowPrompt" />
				</div>
			</div>
			<WorkflowQueue v-if="!deleting && flowStore.isFlowInstalled(route.params.name as string)" />
			<WorkflowOutput
				v-if="!deleting
					&& flowStore.isFlowInstalled(route.params.name as string) 
					|| flowStore.flowResultsByName(route.params.name as string).length > 0"
				@copy-prompt-inputs="(inputs: any[]) => copyPromptInputs(inputs)" />
		</template>
		<template v-else>
			<UProgress class="mb-3" />
		</template>
		<UModal
			v-model="showConfirmDelete"
			prevent-close>
			<UCard :ui="{ ring: '', divide: 'divide-y divide-gray-100 dark:divide-gray-800' }">
				<template #header>
					<div class="flex items-center justify-between">
						<h3 class="text-base font-semibold leading-6 text-gray-900 dark:text-white">
							Confirm workflow deletion
						</h3>
						<UButton color="gray" variant="ghost" icon="i-heroicons-x-mark-20-solid" class="-my-1" @click="showConfirmDelete = false" />
					</div>
				</template>

				<p class="pb-2">
					Are you sure you want to delete the <b>private</b> workflow <b>{{ flowStore.currentFlow?.display_name }}</b>?
				</p>

				<div class="flex justify-end items-center">
					<UButton
						icon="i-heroicons-x-mark-16-solid"
						variant="outline"
						color="green"
						class="mr-2"
						@click="showConfirmDelete = false">
						Cancel
					</UButton>
					<UButton
						icon="i-heroicons-trash"
						variant="outline"
						color="red"
						@click="_deleteFlow(flowStore.currentFlow, flowStore.currentFlow?.private || false)">
						Delete
					</UButton>
				</div>
			</UCard>
		</UModal>
	</AppContainer>
</template>
