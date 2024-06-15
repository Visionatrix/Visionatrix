<script setup lang="ts">
const route = useRoute()

const flowStore = useFlowsStore()

flowStore.setCurrentFlow(route.params.name as string)

const installing = computed(() => flowStore.flowInstallingByName(route.params.name as string) || false)
const installingLoading = computed(() => installing.value !== false && installing.value?.error === '')
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
function deleteFlow() {
	deleting.value = true
	flowStore.deleteFlow(flowStore.currentFlow).then(() => {
		deleting.value = false
	})
}

const collapsedCard = ref(false)

const workflowPrompt = ref<any>(null)
const copyPromptInputs = function (inputs: any[]) {
	workflowPrompt.value?.copyPromptInputs(inputs)
}

const userStore = useUserStore()
</script>

<template>
	<AppContainer>
		<template v-if="!flowStore.loading.flows_available && !flowStore.loading.flows_installed && flowStore.currentFlow && !flowStore.$state.loading.tasks_history">
			<div class="flex flex-col lg:flex-row flex-grow items-start w-full">
				<div class="card-wrapper w-full lg:pr-5">
					<UCard as="div" class="w-full mb-5">
						<template #header>
							<h2 class="text-xl font-bold cursor-pointer select-none flex items-center" @click="() => {
								collapsedCard = !collapsedCard
							}">
								<UIcon :name="collapsedCard ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
									class="mr-2" />
								{{ flowStore.currentFlow?.display_name }}
							</h2>
						</template>

						<div v-if="!collapsedCard" class="p-0 text-sm">
							<p class="flex flex-row items-center text-slate-400 mb-2">
								{{ flowStore.currentFlow?.description }}
							</p>
							<p class="flex flex-row flex-wrap items-center text-md mb-2">
								<UIcon name="i-heroicons-user-16-solid" class="mr-1" />
								<b>Author:</b>&nbsp;
								<a class="hover:underline text-md"
									:href="flowStore.currentFlow?.homepage"
									rel="noopener"
									target="_blank">
									{{ flowStore.currentFlow?.author }}
								</a>
							</p>
							<p class="flex flex-row items-center text-md mb-2">
								<UIcon name="i-heroicons-document-text" class="mr-1" />
								<a v-if="flowStore.currentFlow?.documentation" class="hover:underline"
									:href="flowStore.currentFlow?.documentation"
									rel="noopener"
									target="_blank">
									Documentation
								</a>
								<span v-else>No documentation</span>
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
							<p v-if="flowStore.currentFlow?.models?.length > 0"
								class="flex flex-row flex-wrap items-center text-md">
								<UIcon name="i-heroicons-arrow-down-on-square-stack" class="mr-1" />
								<b>Models ({{ flowStore.currentFlow?.models.length }}):</b>&nbsp;
								<UBadge v-for="model in flowStore.currentFlow?.models"
									:key="model.name"
									class="m-1"
									color="white"
									variant="solid">
									<UTooltip
										text="Gated model requires auth token for download"
										:popper="{ placement: 'top' }">
										<UIcon
											v-if="!model.gated"
											name="i-heroicons-key"
											class="mr-1" />
									</UTooltip>
									<a class="hover:underline underline-offset-4"
										:href="model.homepage"
										rel="noopener" target="_blank">
										{{ model.name }}
									</a>
								</UBadge>
							</p>
						</div>

						<template v-if="!collapsedCard" #footer>
							<div v-if="userStore.isAdmin" class="flex justify-end">
								<div class="flex flex-row items-center justify-center text-sm mr-2">
									<UIcon :name="flowStore.isFlowInstalled(route.params.name as string) ?
											'i-heroicons-check-badge'
											: 'i-heroicons-x-mark'"
										class="mx-1" />
									<span :class="{
										'text-green-500': flowStore.isFlowInstalled(route.params.name as string),
										'text-red-500': !flowStore.isFlowInstalled(route.params.name as string),
									}">
										{{ flowStore.isFlowInstalled(route.params.name as string) ? 'Installed' : 'Not installed' }}
									</span>
								</div>
								<UTooltip v-if="!flowStore.isFlowInstalled(route.params.name as string)"
									text="Setup flow dependencies and configure it in ComfyUI"
									:popper="{ placement: 'top' }" :open-delay="500">
									<UButton icon="i-heroicons-arrow-down-tray"
										class="mx-3"
										color="primary"
										variant="outline"
										:loading="installingLoading"
										@click="() => flowStore.setupFlow(flowStore.currentFlow)">
										{{ setupButtonText }}
									</UButton>
								</UTooltip>
								<UDropdown v-if="flowStore.isFlowInstalled(route.params.name as string)" :items="[
									[{
										label: 'Delete flow',
										icon: 'i-heroicons-trash',
										click: deleteFlow,
									}]
								]" mode="click" label="Actions" :popper="{ placement: 'bottom-end' }">
									<UButton color="white" label="Actions" trailing-icon="i-heroicons-chevron-down-20-solid" />
								</UDropdown>
							</div>
							<div v-else>
								<div class="text-sm flex justify-end">
									<div class="flex flex-row items-center justify-center text-sm mr-3">
										<UIcon :name="flowStore.isFlowInstalled(route.params.name as string) ?
												'i-heroicons-check-badge'
												: 'i-heroicons-x-mark'"
											class="mx-1" />
										<span :class="{
											'text-green-500': flowStore.isFlowInstalled(route.params.name as string),
											'text-red-500': !flowStore.isFlowInstalled(route.params.name as string),
										}">
											{{ flowStore.isFlowInstalled(route.params.name as string) ? 'Installed' : 'Not installed' }}
										</span>
									</div>
									<div class="text-right">
										<p class="text-orange-500">Only admin can manage workflows.</p>
										<span class="text-slate-500">Ask your admin to setup this workflow</span>
									</div>
								</div>
							</div>
						</template>
					</UCard>
				</div>
				<div class="prompt-wrapper w-full">
					<WorkflowPrompt v-if="!deleting && flowStore.isFlowInstalled(route.params.name as string)"
						ref="workflowPrompt" />
				</div>
			</div>
			<WorkflowQueue v-if="!deleting && flowStore.isFlowInstalled(route.params.name as string)" />
			<WorkflowOutput v-if="!deleting
					&& flowStore.isFlowInstalled(route.params.name as string) 
					|| flowStore.flowResultsByName(route.params.name as string).length > 0"
				@copy-prompt-inputs="(inputs: any[]) => copyPromptInputs(inputs)" />
		</template>
		<template v-else>
			<UProgress class="mb-3" />
			<USkeleton class="w-full h-80" />
		</template>
	</AppContainer>
</template>
