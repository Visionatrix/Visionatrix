<script setup lang="ts">
const route = useRoute()

const flowStore = useFlowsStore()

flowStore.setCurrentFlow(<string>route.params.name)

const settingUp = computed(() => flowStore.flowInstallingByName(<string>route.params.name) || false)
const installing = computed(() => flowStore.flowInstallingByName(<string>route.params.name) || false)

const deleting = ref(false)
function deleteFlow() {
	deleting.value = true
	flowStore.deleteFlow(flowStore.currentFlow).then(() => {
		deleting.value = false
	})
}

const collapsedCard = ref(false)
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<template v-if="!flowStore.loading.flows_available && !flowStore.loading.flows_installed && flowStore.currentFlow">
			<div class="flex flex-col items-center lg:flex-row lg:items-start justify-between">
				<div class="flex flex-col w-full lg:mr-5">
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

						<div v-if="!collapsedCard" class="p-0">
							<p class="flex flex-row items-center text-sm text-slate-400 mb-2">
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
								<UIcon name="i-heroicons-scale" class="mr-1" />
								<a v-if="flowStore.currentFlow?.license" class="hover:underline"
									:href="flowStore.currentFlow?.license"
									rel="noopener"
									target="_blank">
									License
								</a>
								<span v-else>No license</span>
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
							<p v-if="flowStore.currentFlow?.models?.length > 0"
								class="flex flex-row flex-wrap items-center text-md mb-2">
								<UIcon name="i-heroicons-arrow-down-on-square-stack" class="mr-1" />
								<b>Models ({{ flowStore.currentFlow?.models.length }}):</b>&nbsp;
								<UBadge v-for="model in flowStore.currentFlow?.models"
									class="m-1"
									color="white"
									variant="solid">
									<a class="hover:underline underline-offset-4"
										:href="model.homepage"
										rel="noopener" target="_blank">
										{{ model.name }}
									</a>
								</UBadge>
							</p>
							<p class="flex flex-row items-center text-md">
								<b>Installed:</b>&nbsp;
								<UIcon :name="flowStore.isFlowInstalled(<string>route.params.name) ?
									'i-heroicons-check-badge'
									: 'i-heroicons-x-mark'"
									class="mx-1" />
								<span :class="{
									'text-green-500': flowStore.isFlowInstalled(<string>route.params.name),
									'text-red-500': !flowStore.isFlowInstalled(<string>route.params.name),
									}">
									{{ flowStore.isFlowInstalled(<string>route.params.name) ? 'Yes' : 'No' }}
								</span>
							</p>
						</div>

						<template v-if="!collapsedCard" #footer>
							<div class="flex justify-end">
								<UTooltip v-if="!flowStore.isFlowInstalled(<string>route.params.name)"
									text="Setup flow dependencies and configure it in ComfyUI"
									:popper="{ placement: 'top' }" :open-delay="500">
									<UButton icon="i-heroicons-arrow-down-tray"
										class="mx-3"
										color="primary"
										variant="outline"
										:loading="settingUp"
										@click="() => flowStore.setupFlow(flowStore.currentFlow)">
										{{ installing ? `${installing?.progress.toFixed(0)}% Setting up` : 'Setup flow' }}
									</UButton>
								</UTooltip>
								<UTooltip v-if="flowStore.isFlowInstalled(<string>route.params.name)"
									text="Delete flow (models are kept)"
									:popper="{ placement: 'top' }" :open-delay="500">
									<UButton icon="i-heroicons-trash"
										color="red"
										variant="outline"
										:loading="deleting"
										@click="deleteFlow">
										Delete flow
									</UButton>
								</UTooltip>
							</div>
						</template>
					</UCard>
					<div class="prompt-wrapper">
						<WorkflowPrompt v-if="!deleting && flowStore.isFlowInstalled(<string>route.params.name)" />
						<!-- <WorkflowPromptHistory v-if="!deleting && flowStore.isFlowInstalled(<string>route.params.name)" /> -->
					</div>
				</div>
				<WorkflowOutput v-if="!deleting && flowStore.isFlowInstalled(<string>route.params.name)" />
			</div>
		</template>
		<template v-else>
			<USkeleton class="w-full h-80" />
		</template>
	</AppContainer>
</template>
