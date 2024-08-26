<script setup lang="ts">
const props = defineProps({
	imageSrc: {
		type: String,
		required: true,
	},
})

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
	visible: false,
})
const minDistance = ref(5)
const isDrawing = ref(false)
const imageWithMask = ref(null)

function applyMask() {
	if (!stageRef.value || !imageLayerRef.value || !maskLayerRef.value) {
		console.error('Could not get stage, image layer or mask layer')
		return
	}

	const stage = stageRef.value.getNode()
	const imageLayer = imageLayerRef.value.getNode()

	// Get image data from the original image layer
	const imageContext = imageLayer.canvas._canvas.getContext('2d')
	imageContext.clearRect(0, 0, stage.width(), stage.height())
	const imageData = imageContext.getImageData(0, 0, stage.width(), stage.height())

	// Create an off-screen canvas for the mask
	const maskCanvas = document.createElement('canvas')
	maskCanvas.width = stage.width()
	maskCanvas.height = stage.height()
	const maskContext: CanvasRenderingContext2D|null = maskCanvas.getContext('2d')

	if (!maskContext) {
		console.error('Could not get 2d context for mask canvas')
		return
	}

	// Draw the circles as a mask on the maskContext
	circles.value.forEach((circle: any) => {
		maskContext.beginPath()
		maskContext.arc(circle.x, circle.y, circle.radius, 0, Math.PI * 2, true)
		maskContext.closePath()
		maskContext.fillStyle = 'rgba(0, 0, 0, 0)'
		maskContext.fill()
	})

	// Get mask data (this contains the alpha information where circles were drawn)
	const maskData = maskContext.getImageData(0, 0, maskCanvas.width, maskCanvas.height)

	// Iterate through each pixel and adjust the alpha channel
	for (let i = 0; i < imageData.data.length; i += 4) {
		const maskAlpha = maskData.data[i + 3] // Alpha value from mask
		if (maskAlpha > 0) {
			// Make the corresponding pixel in the image fully transparent
			imageData.data[i + 3] = 0
		}
	}

	// Put the modified image data back onto the original image layer
	imageContext.putImageData(imageData, 0, 0)

	const uri = stage.toDataURL()
	imageWithMask.value = uri
	console.log(uri)
}

function startDrawing(e: any) {
	// start drawing only on left mouse button click
	if (e.evt.button !== 0) return
	isDrawing.value = true
	lastPosition.value = e.target.getStage().getPointerPosition()
	createCircle(lastPosition.value)
}

function createCircle(pos: any) {
	const newCircle = {
		x: pos.x,
		y: pos.y,
		radius: brushRadius.value,  // Use the brush radius
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

function drawMultipleCircles(e: MouseEvent|any) {
	// Update hover circle position
	moveHoverCircle(e)

	if (!isDrawing.value) return

	const pos = e.target.getStage().getPointerPosition()
	const distance = calculateDistance(lastPosition.value, pos)

	// Check if the mouse moved enough to create a new circle
	if (distance >= minDistance.value) {
		createCircle(pos)
		lastPosition.value = pos  // Update the last position
	}
}

function finishDrawing() {
	isDrawing.value = false
}

function resetMask() {
	circles.value = []
	imageWithMask.value = null
}

function moveHoverCircle(e: MouseEvent|any) {
	const pos = e.target.getStage().getPointerPosition()
	hoverCircle.value.x = pos.x
	hoverCircle.value.y = pos.y
}
function hideHoverCircle() {
	hoverCircle.value.visible = false
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
		fitImageToCanvas()
	}
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
})
</script>

<template>
	<div class="image-inpaint flex flex-col w-full">
		<div class="canvas flex flex-col items-center justify-center mb-3 relative w-full">
			<p class="text-sm my-2 text-slate-500">Select the target area for image inpaint</p>
			<NuxtImg v-if="imageWithMask"
				class="lg:h-full"
				fit="inside"
				:width="flowsStore.$state.outputMaxSize"
				:height="flowsStore.$state.outputMaxSize"
				draggable="false"
				:src="imageWithMask" />
			<v-stage v-if="imageWithMask === null"
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
		<div class="actions mb-3 w-full max-w-[320px]">
			<UButton
				class="mr-3"
				size="sm"
				icon="i-heroicons-clipboard-document-check-16-solid"
				variant="soft"
				@click="applyMask">
				Apply mask to image
			</UButton>
			<UButton
				size="sm"
				icon="i-heroicons-arrow-turn-up-left-20-solid"
				variant="soft"
				color="orange"
				@click="resetMask">
				Reset mask
			</UButton>
		</div>
		<div class="options w-full max-w-[320px]">
			<UFormGroup label="Brush radius" class="mb-3 text-sm">
				<URange v-model="brushRadius" :min="1" :max="100" size="sm" class="my-2" />
				<span>value: {{ brushRadius }}</span>
			</UFormGroup>
		</div>
	</div>
</template>
