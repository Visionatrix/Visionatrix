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

const formGroupLabel = computed(() => {
	return props.inputParam.type !== 'bool' ? props.inputParam.display_name : ''
})
const formGroupHelp = computed(() => {
	return ['range'].includes(props.inputParam.type) ? `value: ${props.inputParamsMap[props.index][props.inputParam.name].value}` : ''
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
</script>

<template>
	<UFormGroup
		v-if="(inputParam?.advanced || false) === advanced && !['image', 'image-mask', 'range_scale'].includes(inputParam.type)"
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
