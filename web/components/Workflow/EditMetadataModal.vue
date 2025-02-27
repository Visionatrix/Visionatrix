<script setup lang="ts">
const props = defineProps<{ flow: Flow }>()
const show = defineModel('show', { default: false, type: Boolean })

const flowsStore = useFlowsStore()
const toast = useToast()

const updating = ref(false)

const newDisplayName = ref(props.flow.display_name)
const newFlowDescription = ref(props.flow.description)
const license = ref(props.flow.license)
const requiredMemoryGb = ref(props.flow.required_memory_gb || 0)
const version = ref(props.flow.version)

const newMetadataValid = computed(() => {
	return newDisplayName.value !== '' && newFlowDescription.value !== ''
})

function updateMetadata() {
	updating.value = true
	flowsStore.updateFlowMetadata(props.flow, {
		display_name: newDisplayName.value,
		description: newFlowDescription.value,
		license: license.value,
		required_memory_gb: requiredMemoryGb.value,
		version: version.value,
	}).then(() => {
		show.value = false
		toast.add({
			title: 'Flow metadata updated',
			description: 'Flow metadata has been updated successfully.',
		})
	}).catch((err) => {
		console.debug('Failed to update flow metadata:', err)
		toast.add({
			title: 'Flow metadata update failed',
			description: err?.details ?? 'Failed to update flow metadata. Please try again.',
		})
	}).finally(() => {
		updating.value = false
	})
}
</script>

<template>
	<UModal v-model="show">
		<div class="p-4 overflow-y-auto relative">
			<h2 class="font-bold">Edit flow metadata</h2>

			<div class="flex flex-col gap-2 mt-3">
				<UFormGroup label="New display name"
					class="flex justify-center flex-col w-full"
					:error="newDisplayName !== '' ? '' : 'Display name is required.'">
					<UInput v-model="newDisplayName" type="text" placeholder="Display name" />
				</UFormGroup>
				<UFormGroup label="New flow description"
					class="flex justify-center flex-col w-full">
					<UTextarea v-model="newFlowDescription" placeholder="Description" />
				</UFormGroup>
				<UFormGroup label="License (optional)"
					class="flex justify-center flex-col w-full">
					<UInput v-model="license" type="text" placeholder="License" />
				</UFormGroup>
				<UFormGroup label="Required memory (GB)"
					class="flex justify-center flex-col w-full">
					<UInput v-model="requiredMemoryGb" type="text" placeholder="Required memory (GB)" />
				</UFormGroup>
				<UFormGroup label="Version"
					class="flex justify-center flex-col w-full">
					<UInput v-model="version" type="text" placeholder="Version" />
				</UFormGroup>
			</div>

			<div class="flex justify-end mt-3">
				<UButton
					class="mr-2"
					variant="soft"
					color="white"
					@click="show = false">
					Cancel
				</UButton>
				<UButton
					variant="soft"
					color="primary"
					:loading="updating"
					:disabled="!newMetadataValid"
					@click="updateMetadata">
					Save
				</UButton>
			</div>
		</div>
	</UModal>
</template>
