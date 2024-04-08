<script setup lang="ts">
const props = defineProps({
	inputParam: {
		type: Object,
		required: true,
	},
	index: {
		type: Number,
		required: true,
	},
	inputParamsMap: {
		type: Array<any[]>,
		required: true,
	},
	advanced: {
		type: Boolean,
		default: false,
	}
})

// eslint-disable-next-line
function createObjectUrl(file?: File) {
	return file ? URL.createObjectURL(file) : ''
}

const imageInput = ref(null)
const imagePreviewUrl = ref('')
const imagePreviewModalOpen = ref(false)

function removeImagePreview() {
	URL.revokeObjectURL(imagePreviewUrl.value)
	imagePreviewUrl.value = ''
	if (imageInput) {
		// @ts-ignore
		imageInput.value.$refs.input.value = ''
	}
	props.inputParamsMap[props.index][props.inputParam.name].value = null
}

const formGroupLabel = computed(() => {
	return props.inputParam.type !== 'bool' ? props.inputParam.display_name : ''
})

onBeforeUnmount(() => {
	URL.revokeObjectURL(imagePreviewUrl.value)
})
</script>

<template>
	<UFormGroup v-if="(inputParam?.advanced || false) === advanced"
		:label="formGroupLabel" class="mb-3">
		<template #hint>
			<span v-if="!inputParam.optional" class="text-red-300">required</span>
		</template>
		<template #default>
			<UTextarea v-if="inputParam.type === 'text'"
				size="md"
				:placeholder="inputParam.display_name"
				:required="!inputParam.optional"
				:resize="true"
				:label="inputParam.display_name"
				:value="inputParamsMap[index][inputParam.name].value"
				variant="outline" @input="(event: InputEvent) => {
					const input = event.target as HTMLTextAreaElement
					inputParamsMap[index][inputParam.name].value = input.value
				}" />

			<UInput v-if="inputParam.type === 'number'"
				type="number"
				:label="inputParam.display_name"
				:required="!inputParam.optional"
				:value="inputParamsMap[index][inputParam.name].value"
				:max="inputParam.max || 100"
				:min="inputParam.min || 0"
				variant="outline" @input="(event: InputEvent) => {
					const input = event.target as HTMLInputElement
					inputParamsMap[index][inputParam.name].value = input.value
				}" />

			<div class="flex flex-row flex-grow items-center justify-between">
				<UInput v-if="inputParam.type === 'image'"
					ref="imageInput"
					type="file"
					accept="image/*"
					class="w-full"
					:label="inputParam.display_name"
					@change="(event: Event) => {
						const input = event.target as HTMLInputElement
						const file = input.files?.[0]
						inputParamsMap[index][inputParam.name].value = file as File
						imagePreviewUrl = createObjectUrl(file)
						console.debug('inputParamsMap', inputParamsMap)
					}" />
				<NuxtImg v-if="imagePreviewUrl !== ''"
					:src="imagePreviewUrl"
					class="w-10 h-10 rounded-lg cursor-pointer ml-2"
					@click="() => {
						imagePreviewModalOpen = true
					}" />
				<UButton v-if="imagePreviewUrl !== ''"
					icon="i-heroicons-x-mark"
					variant="outline"
					class="ml-2"
					@click="removeImagePreview" />
			</div>
			<template v-if="inputParam.type === 'image'">
				<UModal v-model="imagePreviewModalOpen"
					class="z-[90]"
					:transition="false"
					fullscreen>
					<UButton class="absolute top-4 right-4"
						icon="i-heroicons-x-mark"
						variant="ghost"
						@click="() => imagePreviewModalOpen = false" />
					<div class="flex items-center justify-center w-full h-full p-4"
						@click.left="() => imagePreviewModalOpen = false">
						<NuxtImg v-if="imagePreviewUrl"
							class="lg:h-full"
							fit="inside"
							:src="imagePreviewUrl" />
					</div>
				</UModal>
			</template>

			<!-- eslint-disable vue/no-parsing-error -->
			<USelectMenu v-if="inputParam.type === 'list'"
				v-model="inputParamsMap[index][inputParam.name].value"
				:placeholder="inputParam.display_name"
				:options="Object.keys(<object>inputParam.options)" /> <!-- eslint-disable-line vue/no-parsing-error -->

			<UCheckbox v-if="inputParam.type === 'bool'"
				v-model="inputParamsMap[index][inputParam.name].value"
				:label="inputParam?.display_name" />

			<URange v-if="inputParam.type === 'range'"
				v-model="inputParamsMap[index][inputParam.name].value"
				:label="inputParam.display_name"
				size="sm"
				:min="inputParam.min"
				:max="inputParam.max"
				:step="inputParam.step" />
		</template>
	</UFormGroup>
</template>
