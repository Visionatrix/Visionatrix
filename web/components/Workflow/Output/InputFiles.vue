<script setup lang="ts">
defineProps({
	flowResult: {
		type: Object as PropType<FlowResult>,
		required: true,
	},
})

const flowStore = useFlowsStore()

const img = useImage()
const outputInputFileImageSrc = (task_id: string, index: number) => {
	return `${buildBackendApiUrl()}/tasks/inputs?task_id=${task_id}&input_index=${index}`
}

const isModalOpen = ref(false)
const modalImageSrc = ref('')
const modalImageIndex = ref(0)
</script>

<template>
	<div v-if="flowResult.showInputFiles" class="w-full h-full p-1">
		<NuxtImg
			v-if="Object.keys(flowResult.input_files)?.length === 1"
			class="mb-5 mx-auto rounded-lg cursor-pointer max-h-screen"
			fit="outside"
			loading="lazy"
			:placeholder="img(`${buildBackendApiUrl()}/vix_logo.png`, { f: 'png', blur: 3, q: 50 })"
			:src="outputInputFileImageSrc(flowResult.task_id, 0)"
			@click="() => {
				modalImageSrc = outputInputFileImageSrc(flowResult.task_id, 0)
				modalImageIndex = 0
				isModalOpen = true
			}" />
		<UCarousel
			v-if="Object.keys(flowResult.input_files)?.length > 1"
			v-slot="{ item }"
			:items="Object.keys(flowResult.input_files).map((value: any) => {
				return { task_id: flowResult.task_id, index: value as number }
			})"
			:ui="{
				item: 'basis-full md:basis-1/2',
				indicators: {
					wrapper: 'relative bottom-0 mt-4'
				}
			}"
			:page="1"
			indicators>
			<div class="flex flex-col basis-full justify-between mx-2">
				<NuxtImg
					:class="`mb-2 h-100 max-h-[${flowStore.$state.outputMaxSize}px] mx-auto rounded-lg cursor-pointer`"
					fit="outside"
					loading="lazy"
					draggable="false"
					:src="outputInputFileImageSrc(item.task_id, item.index)"
					@click="() => {
						modalImageSrc = outputInputFileImageSrc(flowResult.task_id, item.index)
						modalImageIndex = item.index
						isModalOpen = true
					}" />
			</div>
		</UCarousel>
		<UModal v-model="isModalOpen" class="z-[90]" :transition="false" fullscreen>
			<UButton
				class="absolute top-4 right-4"
				icon="i-heroicons-x-mark"
				variant="ghost"
				@click="() => isModalOpen = false" />
			<div
				class="flex items-center justify-center w-full h-full p-4"
				@click.left="() => isModalOpen = false">
				<NuxtImg
					v-if="modalImageSrc"
					class="lg:h-full"
					fit="inside"
					loading="lazy"
					placeholder="/vix_logo.png"
					:src="modalImageSrc" />
			</div>
		</UModal>
	</div>
</template>
