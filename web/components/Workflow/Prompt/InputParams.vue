<script setup lang="ts">
const props = defineProps({
	inputParamsMap: {
		type: Array<any>,
		required: true,
	},
	additionalInputParamsMap: {
		type: Array<any>,
		required: false,
		default: [],
	},
	advanced: {
		type: Boolean,
		default: false,
	},
})

const flowStore = useFlowsStore()
const userStore = useUserStore()
const workersStore = useWorkersStore()
const advancedCollapsed = ref(!props.advanced)

const profilingOptions = defineModel('profilingOptions', { default: {}, type: Object })
const profilingEnabled = defineModel('profilingEnabled', { default: false, type: Boolean })
const profilingOptionsCollapsed = ref(true)
const workersOptions = computed(() => workersStore.workers.map((worker) => ({
	value: worker.worker_id,
	label: `${worker.worker_id} (type: ${worker.device_type}, vram_total: ${formatBytes(worker.vram_total)})`,
})))

onBeforeMount(() => {
	if (!userStore.isAdmin) {
		return
	}
	const profilingOptionsLocal = localStorage.getItem(`profilingOptions_${flowStore.currentFlow?.name}`)
	if (profilingOptionsLocal) {
		profilingOptions.value = JSON.parse(profilingOptionsLocal)
	}
	workersStore.fetchWorkersInfo().then(() => {
		const workerInfo = workersStore.workers.find((worker) => worker.worker_id === profilingOptions.value['X-WORKER-ID']?.value)
		if (!workerInfo) {
			profilingOptions.value['X-WORKER-ID'] = null
		}
	})
})
</script>

<template>
	<div v-if="advanced" class="heading">
		<h4
			class="text-md font-bold cursor-pointer select-none flex items-center mb-3" @click="() => {
				advancedCollapsed = !advancedCollapsed
			}">
			<UIcon
				:name="!advancedCollapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
				class="mr-2" />
			Advanced options
		</h4>
	</div>
	<div v-if="advancedCollapsed">
		<WorkflowPromptInputParam
			v-for="inputParam, index in flowStore.currentFlow.input_params"
			:key="index"
			:input-params-map="inputParamsMap"
			:index="index"
			:input-param="inputParam"
			:advanced="advanced" />
		<WorkflowPromptInputParam
			v-for="(inputParam, index) in additionalInputParamsMap"
			:key="Object.keys(inputParam)[0]"
			:input-params-map="additionalInputParamsMap"
			:index="index"
			:input-param="inputParam[Object.keys(inputParam)[0]]"
			:advanced="advanced" />

		<template v-if="userStore.isAdmin && advanced">
			<div class="max-h-96 overflow-y-auto mt-5">
				<div class="heading">
					<h4
						class="text-md font-bold cursor-pointer select-none flex items-center mb-3" @click="() => {
							profilingOptionsCollapsed = !profilingOptionsCollapsed
						}">
						<UIcon
							:name="profilingOptionsCollapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
							class="mr-2" />
						<UIcon name="i-mdi-bug-outline" class="mr-2" />
						Execution settings
					</h4>
				</div>
				<div v-if="!profilingOptionsCollapsed" class="p-4">
					<UCheckbox v-model="profilingEnabled"
						label="Enable Execution settings"
						class="mb-3" />
					<UFormGroup v-for="key in Object.keys(profilingOptions)" :key="key" :label="key">
						<div v-if="key === 'X-WORKER-ID'" class="flex items-center w-full max-w-xs">
							<USelectMenu
								v-model="profilingOptions[key]"
								:options="workersOptions"
								placeholder="Select worker"
								class="w-full my-3" />
							<UButton
								icon="i-heroicons-x-mark"
								variant="outline"
								size="sm"
								color="orange"
								class="ml-2"
								@click="() => profilingOptions[key] = null" />
							<UButton
								icon="i-heroicons-arrow-path-solid"
								variant="outline"
								size="sm"
								color="blue"
								class="ml-2"
								@click="() => {
									workersStore.fetchWorkersInfo().then(() => {
										profilingOptions[key] = workersOptions.find((worker) => worker.value === profilingOptions[key]?.value)
									})
								}" />
						</div>
						<UInput v-else
							v-model="profilingOptions[key]"
							placeholder="Enter value"
							class="my-3" />
					</UFormGroup>
				</div>
			</div>
		</template>
	</div>
</template>
