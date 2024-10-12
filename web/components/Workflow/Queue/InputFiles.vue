<script setup lang="ts">
defineProps({
	running: {
		type: Object as PropType<FlowRunning>,
		required: true,
	},
})

const img = useImage()
const queueImageInputSrc = function (task_id: string, index: number) {
	return `${buildBackendApiUrl()}/tasks/inputs?task_id=${task_id}&input_index=${index}`
}

const isModalOpen = ref(false)
const modalImageSrc = ref('')
const modalImageIndex = ref(0)
const collapsed = ref(true)
</script>

<template>
	<div v-if="$props.running && $props.running.input_files && Object.keys($props.running.input_files)?.length > 0"
		class="ml-2 mt-2 mb-5" :class="{ 'mb-10': Object.keys($props.running.input_files)?.length > 1 && !collapsed }">
		<h4 class="mb-3 font-bold cursor-pointer select-none flex items-center text-sm"
			@click="() => collapsed = !collapsed">
			<UIcon :name="collapsed ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-up'"
				class="mr-2" />
			<span>
				Input files ({{ Object.keys($props.running.input_files)?.length }})
			</span>
		</h4>
		<template v-if="!collapsed">
			<NuxtImg
				v-if="Object.keys($props.running.input_files)?.length === 1"
				class="mb-5 rounded-lg cursor-pointer"
				fit="outside"
				loading="lazy"
				:placeholder="img(`${buildBackendApiUrl()}/vix_logo.png`, { f: 'png', blur: 3, q: 50 })"
				:src="queueImageInputSrc($props.running.task_id, 0)"
				@click="() => {
					modalImageSrc = queueImageInputSrc($props.running.task_id, 0)
					modalImageIndex = 0
					isModalOpen = true
				}" />
			<UCarousel v-if="Object.keys($props.running.input_files)?.length > 1"
				v-slot="{ item }"
				:items="Object.keys($props.running.input_files).map((value: any) => {
					return { task_id: running.task_id, index: value as number }
				})"
				:ui="{
					item: 'basis-full md:basis-1/2',
					indicators: {
						wrapper: 'relative bottom-0 mt-4'
					}
				}"
				:page="1"
				indicators>
				<div class="flex flex-col basis-full">
					<NuxtImg
						class="rounded-lg cursor-pointer"
						fit="outside"
						loading="lazy"
						:placeholder="img(`${buildBackendApiUrl()}/vix_logo.png`, { f: 'png', blur: 3, q: 50 })"
						:src="queueImageInputSrc(item.task_id, item.index)"
						@click="() => {
							modalImageSrc = queueImageInputSrc($props.running.task_id, item.index)
							modalImageIndex = item.index
							isModalOpen = true
						}" />
				</div>
			</UCarousel>
			<UModal v-model="isModalOpen" class="z-[90]" :transition="false" fullscreen>
				<UButton class="absolute top-4 right-4"
					icon="i-heroicons-x-mark"
					variant="ghost"
					@click="() => isModalOpen = false" />
				<div class="flex items-center justify-center w-full h-full p-4"
					@click.left="() => isModalOpen = false">
					<NuxtImg v-if="modalImageSrc"
						class="lg:h-full"
						fit="inside"
						loading="lazy"
						placeholder="/vix_logo.png"
						:src="modalImageSrc" />
				</div>
			</UModal>
		</template>
	</div>
</template>
