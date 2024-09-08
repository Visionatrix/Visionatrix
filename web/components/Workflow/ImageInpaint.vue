<script setup lang="ts">
const props = defineProps({
	imageSrc: {
		type: String,
		required: true,
	},
	edgeSize: {
		type: Number,
		default: 0,
	},
})

const imageInpaintMask = defineModel('imageInpaintMask', { default: '', type: String })
const imageInpaintMaskData = defineModel('imageInpaintMaskData', { default: {}, type: Object })

const flowsStore = useFlowsStore()

const stageRef: any = ref(null)
const imageLayerRef: any = ref(null)
const maskLayerRef: any = ref(null)
const image: any = ref(null)
const brushRadius = ref(30)
const circles: any = ref([])
const stageConfig = ref({
	width: flowsStore.$state.outputMaxSize,
	height: flowsStore.$state.outputMaxSize,
})
const imageConfig: any = ref(null)
const lastPosition = ref({ x: 0, y: 0 })
const hoverCircle = ref({
	x: 0,
	y: 0,
	radius: brushRadius.value,
	fill: 'rgba(255, 255, 255, 0.5)',  // White with half opacity
	stroke: null,
	strokeWidth: 0,
	visible: false,
})
const minDistance = ref(5)
const isDrawing = ref(false)

const undoStack = ref<Array<Array<any>>>([])
const redoStack = ref<Array<Array<any>>>([])

function applyMask() {
	if (!stageRef.value || !maskLayerRef.value) {
		console.error('Could not get stage, image layer, or mask layer')
		return
	}

	const stage = stageRef.value.getNode()

	// Get the original image dimensions
	const imageWidth = image.value ? image.value.width : stage.width()
	const imageHeight = image.value ? image.value.height : stage.height()

	// Create a canvas for the mask
	const maskCanvas = document.createElement('canvas')
	maskCanvas.width = imageWidth
	maskCanvas.height = imageHeight
	const maskCtx = maskCanvas.getContext('2d')
	if (!maskCtx) {
		console.error('Could not get 2d context for mask canvas')
		return
	}

	// Fill the canvas with black background
	maskCtx.fillStyle = 'black'
	maskCtx.fillRect(0, 0, imageWidth, imageHeight)

	// Scale the circles to match the image dimensions, then draw them on the mask canvas
	const scaleX = imageWidth / stage.width()
	const scaleY = imageHeight / stage.height()

	maskCtx.fillStyle = 'white'
	circles.value.forEach((circle: any) => {
		maskCtx.beginPath()
		maskCtx.arc(
			circle.x * scaleX,
			circle.y * scaleY,
			circle.radius * Math.max(scaleX, scaleY),
			0,
			Math.PI * 2,
			true
		)
		maskCtx.closePath()
		maskCtx.fill()
	})

	// Generate the final image with the applied mask
	const maskUri = maskCanvas.toDataURL('image/png', 1.0)
	if (maskUri) {
		saveCanvasState()
		imageInpaintMask.value = maskUri
		hoverCircle.value.visible = false
		isDrawing.value = false
	} else {
		console.error('Could not get data URI for masked image')
	}
}

function getTargetPos(e: MouseEvent | TouchEvent | any) {
	const stage = stageRef.value.getNode()
	if (e.type.startsWith('touch')) {
		const touch = e.evt.touches[0] || e.evt.changedTouches[0]
		return {
			x: touch.clientX - stage.getContainer().offsetLeft,
			y: touch.clientY - stage.getContainer().offsetTop
		}
	}
	return stage.getPointerPosition()
}

function startDrawing(e: MouseEvent | TouchEvent | any) {
	// start drawing only on left mouse button click
	if (e.type === 'mousedown' && e.evt.button !== 0) return

	isDrawing.value = true
	lastPosition.value = getTargetPos(e)

	saveState() // Save the current state before drawing

	createCircle(lastPosition.value)
}

function createCircle(pos: any) {
	const newCircle = {
		x: pos.x,
		y: pos.y,
		radius: brushRadius.value,
		fill: 'rgba(255, 255, 255, 1)',
	}

	// Check if the new circle fully covers any existing circles
	circles.value = circles.value.filter((circle: any) => {
		const distance = calculateDistance({ x: circle.x, y: circle.y }, pos)
		return !(distance + circle.radius <= newCircle.radius)
	})

	// Add the new circle to the list
	circles.value.push(newCircle)
}

function calculateDistance(pos1: any, pos2: any) {
	return Math.sqrt(
		Math.pow(pos2.x - pos1.x, 2) + Math.pow(pos2.y - pos1.y, 2)
	)
}

function drawMultipleCircles(e: MouseEvent | TouchEvent | any) {
	// Prevent default behavior for touch events to avoid scrolling
	if (e.type.startsWith('touch')) {
		e.evt.preventDefault()
	}

	// Update hover circle position
	moveHoverCircle(e)

	if (!isDrawing.value) return

	const pos = getTargetPos(e)
	const distance = calculateDistance(lastPosition.value, getTargetPos(e))

	// Check if the mouse moved enough to create a new circle
	if (distance >= minDistance.value) {
		createCircle(pos)
		lastPosition.value = pos  // Update the last position
	}
}

function saveState() {
	undoStack.value.push([...circles.value])
	redoStack.value = []
}

function saveCanvasState() {
	imageInpaintMaskData.value = {
		circles: [...circles.value],
		brushRadius: brushRadius.value,
		undoStack: undoStack.value,
		redoStack: redoStack.value,
	}
}

function loadCanvasState() {
	if (imageInpaintMaskData.value !== null) {
		circles.value = imageInpaintMaskData.value.circles || []
		brushRadius.value = imageInpaintMaskData.value.brushRadius || 30
		undoStack.value = imageInpaintMaskData.value.undoStack || []
		redoStack.value = imageInpaintMaskData.value.redoStack || []
	}
}

function undo() {
	if (undoStack.value.length === 0) return

	redoStack.value.push([...circles.value])
	circles.value = undoStack.value.pop() || []
}

function redo() {
	if (redoStack.value.length === 0) return

	undoStack.value.push([...circles.value])
	circles.value = redoStack.value.pop() || []
}

function finishDrawing() {
	isDrawing.value = false
}

function editMask() {
	// reset applied image to revert back to drawing from the previous state
	imageInpaintMask.value = ''
}

function resetMask() {
	saveState()
	circles.value = []
	imageInpaintMask.value = ''
}

const canUndo = computed(() => undoStack.value.length > 0)
const canRedo = computed(() => redoStack.value.length > 0)

function moveHoverCircle(e: MouseEvent | TouchEvent | any) {
	const pos = getTargetPos(e)
	hoverCircle.value.x = pos.x
	hoverCircle.value.y = pos.y
}

function hideHoverCircle() {
	hoverCircle.value.visible = false
	isDrawing.value = false
}

function showHoverCircle() {
	hoverCircle.value.visible = true
	hoverCircle.value.radius = brushRadius.value
}

function loadImage() {
	const imageObj = new Image()
	imageObj.src = props.imageSrc
	imageObj.onload = () => {
		image.value = imageObj
		updateStageDimensions()
		fitImageToCanvas()
	}
}

function updateStageDimensions() {
	if (!image.value) return

	const windowWidth = window.innerWidth
	const windowHeight = window.innerHeight
	const imageRatio = image.value.width / image.value.height
	
	let newWidth, newHeight

	// Set maximum dimensions (you can adjust these values as needed)
	const maxWidth = Math.min(windowWidth * 0.9, 1200) // 90% of window width or 1200px, whichever is smaller
	const maxHeight = Math.min(windowHeight * 0.8, flowsStore.outputMaxSize) // 80% of window height or 800px, whichever is smaller

	if (imageRatio > maxWidth / maxHeight) {
		// Image is wider than it is tall
		newWidth = maxWidth
		newHeight = newWidth / imageRatio
	} else {
		// Image is taller than it is wide
		newHeight = maxHeight
		newWidth = newHeight * imageRatio
	}

	stageConfig.value = {
		width: Math.floor(newWidth),
		height: Math.floor(newHeight),
	}

	fitImageToCanvas()
}

function fitImageToCanvas() {
	const stageWidth = stageConfig.value.width
	const stageHeight = stageConfig.value.height
	const imageWidth = image.value.width
	const imageHeight = image.value.height

	const scaleX = stageWidth / imageWidth
	const scaleY = stageHeight / imageHeight
	const scale = Math.min(scaleX, scaleY)

	imageConfig.value = {
		x: 0,
		y: 0,
		width: imageWidth * scale,
		height: imageHeight * scale,
	}
}

onBeforeMount(() => {
	loadImage()
	loadCanvasState()
})

onMounted(() => {
	if (stageRef.value) {
		const stage = stageRef.value.getNode()
		stage.on('touchstart', startDrawing)
		stage.on('touchmove', drawMultipleCircles)
		stage.on('touchend', finishDrawing)
		stage.on('touchcancel', hideHoverCircle)
	}
})

onBeforeUnmount(() => {
	if (stageRef.value) {
		const stage = stageRef.value.getNode()

		stage.off('touchstart')
		stage.off('touchmove')
		stage.off('touchend')
		stage.off('touchcancel')
	}

	saveCanvasState()
})
</script>

<template>
	<div class="image-mask flex flex-col w-full">
		<div class="canvas flex flex-col items-center justify-center mb-3 w-full">
			<p class="text-sm my-2 text-slate-500">Select the target area for image inpaint</p>
			<div class="preview-over-original relative">
				<NuxtImg v-if="imageSrc && imageSrc !== '' && imageInpaintMask !== ''"
					:src="imageSrc"
					fit="inside"
					:width="stageConfig.width"
					:height="stageConfig.height"
					draggable="false"
					:class="{ absolute: imageInpaintMask !== '' }"
					@click="() => {
						imagePreviewModalOpen = true
					}" />
				<NuxtImg v-if="imageInpaintMask"
					:src="imageInpaintMask"
					fit="inside"
					:width="stageConfig.width"
					:height="stageConfig.height"
					draggable="false"
					class="opacity-50"
					@click="() => {
						imagePreviewModalOpen = true
					}" />
			</div>
			<v-stage v-if="imageInpaintMask === ''"
				ref="stageRef"
				:config="stageConfig"
				@mousedown="startDrawing"
				@mousemove="drawMultipleCircles"
				@mouseup="finishDrawing"
				@mouseleave="hideHoverCircle"
				@mouseenter="showHoverCircle">
				<!-- Background Image Layer -->
				<v-layer ref="imageLayerRef">
					<v-image :image="image" :config="stageConfig" />
				</v-layer>

				<!-- Mask Drawing Layer -->
				<v-layer ref="maskLayerRef">
					<v-circle
						v-for="(circle, index) in circles"
						:key="index"
						:config="circle" />
					<v-circle
						v-if="hoverCircle.visible"
						:config="hoverCircle" />
				</v-layer>
			</v-stage>
		</div>
		<div class="actions flex items-center justify-center mb-3 mx-auto">
			<UButton
				class="mr-2"
				size="xs"
				icon="i-heroicons-clipboard-document-check-16-solid"
				variant="soft"
				:disabled="circles.length === 0 || imageInpaintMask !== ''"
				@click="applyMask">
				Apply
			</UButton>
			<UButton
				class="mr-2"
				size="xs"
				icon="i-heroicons-arrow-uturn-left-16-solid"
				variant="soft"
				color="cyan"
				:disabled="!canUndo || imageInpaintMask !== ''"
				@click="undo" />
			<UButton
				class="mr-2"
				size="xs"
				icon="i-heroicons-arrow-uturn-right-16-solid"
				variant="soft"
				color="cyan"
				:disabled="!canRedo || imageInpaintMask !== ''"
				@click="redo" />
			<UButton
				class="mr-2"
				size="xs"
				icon="i-heroicons-arrow-turn-up-left-20-solid"
				variant="soft"
				:disabled="circles.length === 0 && imageInpaintMask === ''"
				color="red"
				@click="resetMask">
				Reset
			</UButton>
			<UButton
				size="xs"
				icon="i-heroicons-pencil-solid"
				variant="soft"
				:disabled="imageInpaintMask === ''"
				color="orange"
				@click="editMask">
				Edit
			</UButton>
		</div>
		<div class="options w-full max-w-[320px]">
			<UFormGroup
				class="mb-3 text-sm"
				:hint="`value: ${ brushRadius }`"
				label="Brush radius">
				<URange
					v-model="brushRadius"
					:min="1"
					:max="100"
					size="sm"
					class="my-2"
					:disabled="imageInpaintMask !== ''" />
			</UFormGroup>
		</div>
	</div>
</template>
