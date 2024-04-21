<script setup lang="ts">
defineProps({
	show: {
		type: Boolean,
		required: false,
	},
	flowResult: {
		type: Object,
		required: true,
	},
	outputImgSrc: {
		type: String,
		required: true,
	},
	outputParamIndex: {
		type: Number,
		required: true,
	},
})

const flowStore = useFlowsStore()
// list of flows supported "send to flow" feature
const supportedFlows = computed(
	() => flowStore.flows.filter(flow => flow.name !== flowStore.currentFlow.name)
		.map(flow => ({ label: flow.display_name, value: flow.name }))
)
const selectedFlow = ref(supportedFlows.value[0] || '')
const sending = ref(false)
</script>

<template>
	<UModal v-model="$props.show" class="z-[90]" :transition="false">
		<div class="p-4">
			<h2 class="text-lg text-center mb-4">Send to flow</h2>
			<div class="flex justify-center mb-4">
				<NuxtImg :src="outputImgSrc" class="w-1/2 rounded-lg" :draggable="false" />
			</div>
			<p class="text-sm text-slate-500 text-center mb-4">
				{{
					Object.keys(flowResult.input_params_mapped)
						.filter((key) => {
							return flowResult.input_params_mapped[key] !== ''
						})
						.map((key) => {
							return `${key}: ${flowResult.input_params_mapped[key]}`
						}).join(' | ')
				}}
			</p>
			<p class="text-md text-center text-red-500 mb-4">
				<USelectMenu v-model="selectedFlow" class="w-full" :options="supportedFlows" />
			</p>
			<div class="flex justify-end">
				<UButton
					icon="i-heroicons-arrow-uturn-up-solid"
					color="violet"
					variant="outline"
					:loading="sending"
					@click="() => console.debug('Send to flow')">
					Send
				</UButton>
			</div>
		</div>
	</UModal>
</template>
