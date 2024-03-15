<script setup lang="ts">
defineProps({
	inputParam: {
		type: Object,
		required: true,
	},
	index: {
		type: Number,
		required: true,
	},
	inputParamsMap: {
		type: Object,
		required: true,
	},
	advanced: {
		type: Boolean,
		default: false,
	}
})

function createObjectUrl(file: File) {
	return URL.createObjectURL(file)
}

const imagePreviewUrl = ref('')
</script>

<template>
	<UFormGroup v-if="(inputParam?.advanced || false) === advanced"
		:label="inputParam.display_name" class="mb-3">
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
				variant="outline" @input="(event: InputEvent) => {
					const input = event.target as HTMLInputElement
					inputParamsMap[index][inputParam.name].value = input.value
				}" />

			<div class="flex flex-row flex-grow items-center justify-between">
				<UInput v-if="inputParam.type === 'image'"
					type="file"
					accept="image/*"
					class="mr-2 w-full"
					:label="inputParam.display_name"
					@change="(event: Event) => {
						const input = event.target as HTMLInputElement
						const file = input.files?.[0]
						inputParamsMap[index][inputParam.name].value = <File>file
						imagePreviewUrl = file ? createObjectUrl(file) : ''
						console.debug('inputParamsMap', inputParamsMap)
					}" />
				<NuxtImg v-if="imagePreviewUrl !== ''"
					:src="imagePreviewUrl"
					class="w-10 h-10 rounded-lg" />
			</div>

			<USelectMenu v-if="inputParam.type === 'list'"
				v-model="inputParamsMap[index][inputParam.name].value"
				:placeholder="inputParam.display_name"
				:options="Object.keys(<object>inputParam.options)" />

			<UCheckbox v-if="inputParam.type === 'bool'"
				v-model="inputParamsMap[index][inputParam.name].value"
				:label="inputParam?.display_name" />

			<URange v-if="inputParam.type === 'range'"
				:label="inputParam.display_name"
				size="sm"
				:min="inputParam.min"
				:max="inputParam.max"
				:step="inputParam.step"
				v-model="inputParamsMap[index][inputParam.name].value" />
		</template>
	</UFormGroup>
</template>
