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

const config = useRuntimeConfig()
const nextcloudStore = useNextcloudStore()
const ncSelectedFile = computed<NextcloudFile|null>(() => {
	// @ts-ignore
	if (nextcloudStore.selectedFiles[props.inputParam.name]) {
		// @ts-ignore
		return nextcloudStore.selectedFiles[props.inputParam.name]
	}
	return null
})
const ncSelectedFilePreviewUrl = computed(() => {
	if (!ncSelectedFile.value) {
		return ''
	}
	const domain = window.location.origin
	return `${domain}/index.php/core/preview?fileId=${ncSelectedFile.value?.id}&mimeFallback=true&a=1`
})
const ncSelectedFileSource = computed(() => {
	if (!ncSelectedFile.value) {
		return ''
	}
	return ncSelectedFile.value.source
})

watch(ncSelectedFile, (newFile) => {
	if (newFile) {
		props.inputParamsMap[props.index][props.inputParam.name].value = newFile
		props.inputParamsMap[props.index][props.inputParam.name].image_preview_url = ncSelectedFileSource.value
		props.inputParamsMap[props.index][props.inputParam.name].nc_file = true
	} else {
		props.inputParamsMap[props.index][props.inputParam.name].value = null
		props.inputParamsMap[props.index][props.inputParam.name].image_preview_url = ''
		props.inputParamsMap[props.index][props.inputParam.name].nc_file = false
	}
})

const imagePreviewModalOpen = ref(false)

const imageInput = ref(null)
const imagePreviewUrl = ref('')
const targetImageDimensions = ref({width: 0, height: 0})

// for image-mask type
const imageInpaintMask = ref('')
const imageInpaintMaskData = ref({})
const sourceImageInput: Ref<any> = ref(null)
const sourceInputParamName = props.inputParamsMap[props.index][props.inputParam.name].source_input_name ?? ''
const sourceInputImageParamIndex = props.inputParamsMap.findIndex((inputParam: any) => {
	const key = Object.keys(inputParam)[0]
	if (key === props.inputParamsMap[props.index][props.inputParam.name].source_input_name) {
		return true
	}
})

function loadTargetImageDimensions() {
	try {
		const sourceImageParam: any = props.inputParamsMap.find((inputParam: any) => {
			const key = Object.keys(inputParam)[0]
			if (key === sourceInputParamName) {
				return inputParam[key]
			}
		})
		getImageDimensions(sourceImageParam[sourceInputParamName].value)
	} catch {
		targetImageDimensions.value.width = 0
		targetImageDimensions.value.height = 0
	}
}

onMounted(() => {
	if (props.inputParam.type === 'range_scale') {
		loadTargetImageDimensions()
	}
	if (props.inputParam.type === 'image-mask') {
		watch(imageInpaintMask, (newImageInpaint) => {
			// convert to File object
			const imageInpaintMaskFile = new File([imageInpaintMask.value], `image-mask-${props.inputParam.name}.png`, { type: 'image/png' })
			props.inputParamsMap[props.index][props.inputParam.name].value = imageInpaintMaskFile
			// set and update mask_applied flag to current image-mask inputParam, required for validation
			props.inputParamsMap[props.index][props.inputParam.name].mask_applied = newImageInpaint !== ''
		})
	}
})

if (props.inputParam.type === 'range_scale') {
	watch(props.inputParamsMap, () => {
		loadTargetImageDimensions()
	})
}

 
function createObjectUrl(file?: File) {
	return file ? URL.createObjectURL(file) : ''
}

function removeImagePreview() {
	URL.revokeObjectURL(imagePreviewUrl.value)
	imagePreviewUrl.value = ''
	if (imageInput.value) {
		// @ts-ignore
		imageInput.value.$refs.input.value = ''
	}
	props.inputParamsMap[props.index][props.inputParam.name].value = null
	props.inputParamsMap[props.index][props.inputParam.name].image_preview_url = ''
}

function resetImageMask() {
	URL.revokeObjectURL(imageInpaintMask.value)
	imageInpaintMask.value = ''
	imageInpaintMaskData.value = {}
	props.inputParamsMap[props.index][props.inputParam.name].value = null
	props.inputParamsMap[props.index][props.inputParam.name].mask_applied = false
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
	if (props.inputParam.type === 'image-mask') {
		sourceImageInput.value = props.inputParamsMap[sourceInputImageParamIndex][sourceInputParamName]
		watch(props.inputParamsMap[sourceInputImageParamIndex][sourceInputParamName], (newSourceImageInput) => {
			// Reset the mask on source image change
			imageInpaintMask.value = ''
			imageInpaintMaskData.value = {}
			sourceImageInput.value = newSourceImageInput
		})
	}
})

onBeforeUnmount(() => {
	URL.revokeObjectURL(imagePreviewUrl.value)
	URL.revokeObjectURL(imageInpaintMask.value)
	nextcloudStore.removeSelectedFile(props.inputParam.name)

	if (props.inputParam.type === 'text' && textareaInput.value) {
		// @ts-ignore
		textareaInput.value.$refs.textarea.removeEventListener('keydown', editAttentionListener)
	}
})
</script>

<template>
	<UFormGroup
		v-if="(inputParam?.advanced || false) === advanced"
		class="mb-3"
		:class="{
			'italic': inputParam?.dynamic_lora,
		}"
		:help="formGroupHelp">
		<template #hint>
			<span v-if="!inputParam.optional" class="text-red-300">required</span>
		</template>
		<template #label>
			<div class="flex items-center">
				<UPopover v-if="inputParam?.dynamic_lora && inputParam.trigger_words.length > 0">
					<UButton
						icon="i-heroicons-information-circle"
						variant="ghost"
						size="xs"
						color="gray"
						class="mr-2" />
					<template #panel>
						<div class="p-2 max-w-48 max-h-48 not-italic">
							<h4 class="mb-2 text-center">Trigger words</h4>
							<UBadge
								v-for="triggerWord in inputParam.trigger_words"
								:key="triggerWord"
								color="violet"
								class="mr-1 cursor-pointer"
								@click="() => {
									const clipboard = useCopyToClipboard()
									clipboard.copy(triggerWord)
									const toast = useToast()
									toast.add({
										title: 'Clipboard',
										description: `Trigger word copied to clipboard`,
										timeout: 2000,
									})
								}">
								{{ triggerWord }}
							</UBadge>
						</div>
					</template>
				</UPopover>
				<label class="block font-medium text-gray-700 dark:text-gray-200">
					{{ formGroupLabel }}
				</label>
			</div>
		</template>
		<template #default>
			<UTextarea
				v-if="inputParam.type === 'text'"
				ref="textareaInput"
				size="md"
				:placeholder="inputParam.display_name"
				:required="!inputParam.optional"
				:resize="true"
				:label="inputParam.display_name"
				:value="inputParamsMap[index][inputParam.name].value"
				autoresize
				variant="outline" @input="(event: InputEvent) => {
					const input = event.target as HTMLTextAreaElement
					inputParamsMap[index][inputParam.name].value = input.value
				}" />

			<template v-if="inputParam.type === 'number'">
				<template v-if="inputParam.name === 'seed'">
					<div class="flex items-center">
						<UInput
							v-if="inputParam.type === 'number'"
							v-model="inputParamsMap[index][inputParam.name].value"
							type="number"
							:label="inputParam.display_name"
							:required="!inputParam.optional"
							:max="inputParam.max || 100"
							:min="inputParam.min || 0"
							variant="outline" />
						<UButton
							icon="i-heroicons-arrow-path"
							color="violet"
							variant="outline"
							size="xs"
							class="ml-2"
							@click="() => {
								inputParamsMap[index][inputParam.name].value = Math.floor(Math.random() * 10000000) as number
							}" />
					</div>
				</template>
				<UInput
					v-else
					v-model="inputParamsMap[index][inputParam.name].value"
					type="number"
					:label="inputParam.display_name"
					:required="!inputParam.optional"
					:max="inputParam.max || 100"
					:min="inputParam.min || 0"
					variant="outline" />
			</template>

			<div
				v-if="inputParam.type === 'image'"
				class="flex flex-row flex-grow items-center justify-between">
				<UInput
					ref="imageInput"
					type="file"
					accept="image/*"
					class="w-full"
					variant="outline"
					color="gray"
					:disabled="ncSelectedFile !== null"
					:label="inputParam.display_name"
					@change="(files: FileList) => {
						console.debug('files', files)
						const file = files?.[0]
						inputParamsMap[index][inputParam.name].value = file as File
						imagePreviewUrl = createObjectUrl(file)
						// set the preview url to the inputParamsMap so that it can be used in the image-mask inputParam
						inputParamsMap[index][inputParam.name].image_preview_url = imagePreviewUrl
						if (ncSelectedFile !== null) {
							nextcloudStore.removeSelectedFile(inputParam.name)
						}
						console.debug('inputParamsMap', inputParamsMap)
					}" />
				<UDivider v-if="config.app.isNextcloudIntegration"
					class="mx-2"
					orientation="vertical"
					label="OR" />
				<UButton v-if="config.app.isNextcloudIntegration"
					icon="i-heroicons-cloud-arrow-down"
					variant="outline"
					color="blue"
					:disabled="ncSelectedFile !== null || imagePreviewUrl !== ''"
					:title="ncSelectedFile !== null ? ncSelectedFile.attributes.filename : 'Choose from Nextcloud'"
					@click="() => {
						nextcloudStore.openNextcloudFilePicker(inputParam.name)
					}">
					Choose from Nextcloud
				</UButton>
				<template v-if="ncSelectedFilePreviewUrl !== ''">
					<NuxtImg
						:src="ncSelectedFilePreviewUrl"
						class="h-10 rounded-lg cursor-pointer ml-2"
						@click="() => {
							imagePreviewModalOpen = true
						}" />
					<UButton
						icon="i-heroicons-x-mark"
						variant="outline"
						class="ml-2"
						@click="() => {
							nextcloudStore.removeSelectedFile(inputParam.name)
							if (imagePreviewUrl !== '') {
								removeImagePreview()
							}
						}" />
				</template>
				<template v-else-if="imagePreviewUrl !== ''">
					<NuxtImg
						:src="!imageInpaintMask ? imagePreviewUrl : imageInpaintMask"
						class="h-10 rounded-lg cursor-pointer ml-2"
						@click="() => {
							imagePreviewModalOpen = true
						}" />
					<UButton
						icon="i-heroicons-x-mark"
						variant="outline"
						class="ml-2"
						@click="removeImagePreview" />
				</template>
			</div>

			<div
				v-if="inputParam.type === 'image-mask'"
				class="flex flex-row flex-grow items-center">
				<UButton
					v-if="sourceImageInput"
					icon="i-heroicons-paint-brush-16-solid"
					class="mr-2"
					color="violet"
					variant="outline"
					size="xs"
					:disabled="!sourceImageInput?.value"
					@click="() => {
						imagePreviewModalOpen = true
					}">
					<span class="sm:inline">{{ imageInpaintMask !== '' ? 'Edit mask' : 'Draw mask' }}</span>
				</UButton>
				<div class="preview-over-original relative">
					<NuxtImg
						v-if="sourceImageInput && sourceImageInput?.value"
						:src="sourceImageInput?.image_preview_url"
						class="h-10 rounded-lg cursor-pointer"
						:class="{ absolute: imageInpaintMask !== '' }"
						@click="() => {
							imagePreviewModalOpen = true
						}" />
					<NuxtImg
						v-if="imageInpaintMask"
						:src="imageInpaintMask"
						class="h-10 rounded-lg cursor-pointer opacity-50"
						@click="() => {
							imagePreviewModalOpen = true
						}" />
				</div>
				<span
					v-if="!sourceImageInput || (sourceImageInput && !sourceImageInput?.value)"
					class="text-red-300 text-sm">
					Select source image
				</span>
				<UButton
					v-if="imageInpaintMask"
					icon="i-heroicons-x-mark"
					variant="outline"
					color="violet"
					class="ml-2"
					@click="resetImageMask" />
			</div>
			<template v-if="inputParam.type === 'image' || inputParam.type === 'image-mask'">
				<UModal
					v-model="imagePreviewModalOpen"
					class="z-[90] overflow-y-auto"
					:transition="false"
					fullscreen>
					<UButton
						class="absolute top-4 right-4 z-[100]"
						icon="i-heroicons-x-mark"
						variant="ghost"
						@click="() => imagePreviewModalOpen = false" />
					<div
						v-if="inputParam.type === 'image'"
						class="flex items-center justify-center w-full h-full p-4"
						@click.left="() => imagePreviewModalOpen = false">
						<NuxtImg
							v-if="imagePreviewUrl !== ''"
							class="lg:h-full"
							fit="contain"
							:src="imagePreviewUrl" />
						<NuxtImg 
							v-if="ncSelectedFilePreviewUrl !== ''"
							class="lg:h-full"
							fit="inside"
							:src="ncSelectedFileSource" />
					</div>
					<WorkflowPromptImageInpaint
						v-else
						ref="imageInpaint"
						v-model:image-inpaint-mask="imageInpaintMask"
						v-model:image-inpaint-mask-data="imageInpaintMaskData"
						class="flex items-center justify-center w-full h-full p-4"
						:image-src="sourceImageInput?.image_preview_url" />
				</UModal>
			</template>

			<!-- eslint-disable vue/no-parsing-error -->
			<USelectMenu
				v-if="inputParam.type === 'list'"
				v-model="inputParamsMap[index][inputParam.name].value"
				:placeholder="inputParam.display_name"
				:options="Object.keys(<object>inputParam.options)" /> <!-- eslint-disable-line vue/no-parsing-error -->

			<UCheckbox
				v-if="inputParam.type === 'bool'"
				v-model="inputParamsMap[index][inputParam.name].value"
				:label="inputParam?.display_name" />

			<URange
				v-if="['range', 'range_scale'].includes(inputParam.type)"
				v-model="inputParamsMap[index][inputParam.name].value"
				:label="inputParam.display_name"
				size="sm"
				:min="inputParam.min"
				:max="inputParam.max"
				:step="inputParam.step" />
		</template>
	</UFormGroup>
</template>
