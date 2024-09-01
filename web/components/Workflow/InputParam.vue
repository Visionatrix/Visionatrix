<script setup lang="ts">
import { editAttention } from '~/utils/editAttention'

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
const imageInpaintWithMask = ref('')
const imageInpaintEdgeSizeEnabled = ref(true)
const imageInpaintMaskData = ref({})

const targetImageDimensions = ref({width: 0, height: 0})

function loadTargetImageDimensions() {
	try {
		const sourceInputParamName = props.inputParamsMap[props.index][props.inputParam.name].source_input_name
		const sourceImageParam: any = props.inputParamsMap.find((inputParam: any) => {
			const key = Object.keys(inputParam)[0]
			if (key === sourceInputParamName) {
				return inputParam[key]
			}
		})
		getImageDimensions(sourceImageParam[sourceInputParamName].value)
	} catch (err) {
		targetImageDimensions.value.width = 0
		targetImageDimensions.value.height = 0
	}
}

onMounted(() => {
	if (props.inputParam.type === 'range_scale') {
		loadTargetImageDimensions()
	}
})

if (props.inputParam.type === 'range_scale') {
	watch(props.inputParamsMap, () => {
		loadTargetImageDimensions()
	})
}

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

function getImageDimensions(file: File) {
	if (!(file instanceof File)) {
		targetImageDimensions.value.width = 0
		targetImageDimensions.value.height = 0
		return
	}
	const objectUrl = URL.createObjectURL(file)
	const img = new Image()
	img.onload = function() {
		targetImageDimensions.value.width = img.naturalWidth
		targetImageDimensions.value.height = img.naturalHeight
		URL.revokeObjectURL(img.src)
	}
	img.src = objectUrl
}

const formGroupHelp = computed(() => {
	if (props.inputParam.type === 'range_scale') {
		const scaleFactor = props.inputParamsMap[props.index][props.inputParam.name].value as number
		return `value: ${scaleFactor}x (${targetImageDimensions.value.width}x${targetImageDimensions.value.height} -> ${(targetImageDimensions.value.width * scaleFactor).toFixed(0)}x${(targetImageDimensions.value.height * scaleFactor).toFixed(0)})`
	}
	return ['range', 'range_scale'].includes(props.inputParam.type) ? `value: ${props.inputParamsMap[props.index][props.inputParam.name].value}` : ''
})

onBeforeUnmount(() => {
	URL.revokeObjectURL(imagePreviewUrl.value)
})

const textareaInput = ref(null)

function editAttentionListener(event: any) {
	const updatedText = editAttention(event)
	if (updatedText) {
		props.inputParamsMap[props.index][props.inputParam.name].value = updatedText
	}
}

// add event listener for textarea keydown for editAttention feature
onMounted(() => {
	if (props.inputParam.type === 'text' && textareaInput.value) {
		// @ts-ignore
		textareaInput.value.$refs.textarea.addEventListener('keydown', editAttentionListener)
	}
})

onBeforeUnmount(() => {
	if (props.inputParam.type === 'text' && textareaInput.value) {
		// @ts-ignore
		textareaInput.value.$refs.textarea.removeEventListener('keydown', editAttentionListener)
	}
})

if (props.inputParam.type === 'image-inpaint') {
	watch(imageInpaintWithMask, (newImageInpaint) => {
		// convert to File object
		const imageInpaintWithMaskFile = new File([imageInpaintWithMask.value], 'image-inpaint-masked.png', { type: 'image/png' })
		props.inputParamsMap[props.index][props.inputParam.name].value = imageInpaintWithMaskFile
		// set and update mask_applied flag to current image-inpaint inputParam, required for validation
		props.inputParamsMap[props.index][props.inputParam.name].mask_applied = newImageInpaint !== ''
	})
	watch(imageInpaintEdgeSizeEnabled, (newValue) => {
		console.debug('imageInpaintEdgeSizeEnabled changed to ', newValue)
		// set edge_size_enabled flag to current image-inpaint inputParam
		props.inputParamsMap[props.index][props.inputParam.name].edge_size_enabled = newValue
	})
}

</script>

<template>
	<UFormGroup v-if="(inputParam?.advanced || false) === advanced"
		:label="formGroupLabel" class="mb-3"
		:help="formGroupHelp">
		<template #hint>
			<span v-if="!inputParam.optional" class="text-red-300">required</span>
		</template>
		<template #default>
			<UTextarea v-if="inputParam.type === 'text'"
				ref="textareaInput"
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

			<template v-if="inputParam.type === 'number'">
				<template v-if="inputParam.name === 'seed'">
					<div class="flex items-center">
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
						<UButton icon="i-heroicons-arrow-path"
							color="violet"
							variant="outline"
							size="xs"
							class="ml-2"
							@click="() => {
								inputParamsMap[index][inputParam.name].value = Math.floor(Math.random() * 10000000) as number
							}" />
					</div>
				</template>
				<UInput v-else
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
			</template>

			<div v-if="inputParam.type === 'image' || inputParam.type === 'image-inpaint'"
				class="flex flex-row flex-grow items-center justify-between">
				<UInput ref="imageInput"
					type="file"
					accept="image/*"
					class="w-full"
					:label="inputParam.display_name"
					@change="(files: FileList) => {
						console.debug('files', files)
						const file = files?.[0]
						inputParamsMap[index][inputParam.name].value = file as File
						imagePreviewUrl = createObjectUrl(file)
						console.debug('inputParamsMap', inputParamsMap)
						if (inputParam.type === 'image-inpaint') {
							// Force open modal to draw the mask
							imagePreviewModalOpen = true
							// Reset previous masked image
							imageInpaintWithMask = ''
							// Reset the previous drawn mask and undo/redo history
							imageInpaintMaskData = {}
						}
					}" />
				<NuxtImg v-if="imagePreviewUrl !== ''"
					:src="!imageInpaintWithMask ? imagePreviewUrl : imageInpaintWithMask"
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
			<template v-if="inputParam.type === 'image' || inputParam.type === 'image-inpaint'">
				<UModal v-model="imagePreviewModalOpen"
					class="z-[90] overflow-y-auto"
					:transition="false"
					fullscreen>
					<UButton class="absolute top-4 right-4 z-[100]"
						icon="i-heroicons-x-mark"
						variant="ghost"
						@click="() => imagePreviewModalOpen = false" />
					<div v-if="inputParam.type === 'image'"
						class="flex items-center justify-center w-full h-full p-4"
						@click.left="() => imagePreviewModalOpen = false">
						<NuxtImg 
							class="lg:h-full"
							fit="inside"
							:src="imagePreviewUrl" />
					</div>
					<WorkflowImageInpaint v-else
						ref="imageInpaint"
						v-model:image-inpaint-with-mask="imageInpaintWithMask"
						v-model:edge-size-enabled="imageInpaintEdgeSizeEnabled"
						v-model:image-inpaint-mask-data="imageInpaintMaskData"
						:edge-size="inputParam?.edge_size"
						class="flex items-center justify-center w-full h-full p-4"
						:image-src="imagePreviewUrl" />
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

			<URange v-if="['range', 'range_scale'].includes(inputParam.type)"
				v-model="inputParamsMap[index][inputParam.name].value"
				:label="inputParam.display_name"
				size="sm"
				:min="inputParam.min"
				:max="inputParam.max"
				:step="inputParam.step" />
		</template>
	</UFormGroup>
</template>
