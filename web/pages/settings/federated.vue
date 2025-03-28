<script setup lang="ts">
useHead({
	title: 'Federated settings - Visionatrix',
	meta: [
		{
			name: 'description',
			content: 'Federated settings - Visionatrix',
		},
	],
})

const userStore = useUserStore()
const settingsStore = useSettingsStore()
const federatedStore = useFederatedStore()
const toast = useToast()

onMounted(() => {
	federatedStore.startPolling()
})

onBeforeUnmount(() => {
	federatedStore.stopPolling()
})

const tableHeadersMap = [
	{
		id: 'actions',
		label: 'Actions',
		sortable: false,
	},
	{
		id: 'instance_name',
		label: 'Instance name',
		sortable: true,
	},
	{
		id: 'url_address',
		label: 'URL address',
		sortable: true,
	},
	{
		id: 'username',
		label: 'Username',
		sortable: true,
	},
	{
		id: 'enabled',
		label: 'Enabled',
		sortable: true,
	},
	{
		id: 'created_at',
		label: 'Created at',
		sortable: true,
	},
]

const columns = tableHeadersMap.map((header) => {
	return {
		key: header.id,
		label: header.label,
		sortable: header.sortable,
		class: '',
	}
})

const rows = computed(() => federatedStore.$state.instances)

const showRegisterModal = ref(false)
const deleting = ref(false)
const editingInstance = ref<FederationInstance | null>(null)
const newInstanceName = ref('')
const newInstanceUrl = ref('')
const newInstanceUsername = ref('')
const newInstancePassword = ref('')
const newInstanceEnabled = ref(false)

watch(showRegisterModal, (value) => {
	if (!value) {
		newInstanceName.value = ''
		newInstanceUrl.value = ''
		newInstanceUsername.value = ''
		newInstancePassword.value = ''
		newInstanceEnabled.value = false
	}
	if (editingInstance.value && !value) {
		editingInstance.value = null
	}
})
watch(editingInstance, (value) => {
	if (value !== null) {
		newInstanceName.value = value.instance_name
		newInstanceUrl.value = value.url_address
		newInstanceUsername.value = value.username
		newInstancePassword.value = value.password
		newInstanceEnabled.value = value.enabled
	}
})

const registerNewInstanceValid = computed(() => {
	return newInstanceName.value.length > 0
		&& newInstanceUrl.value.length > 0
		&& newInstanceUsername.value.length > 0
		&& newInstancePassword.value.length > 0
})

const registerOrUpdateLoading = ref(false)
function handleRegisterOrEditInstance() {
	registerOrUpdateLoading.value = true
	if (editingInstance.value !== null) {
		// Update instance
		federatedStore.updateFederationInstance({
			...editingInstance.value,
			instance_name: newInstanceName.value,
			url_address: newInstanceUrl.value,
			username: newInstanceUsername.value,
			password: newInstancePassword.value,
			enabled: newInstanceEnabled.value,
		}).then(() => {
			showRegisterModal.value = false
			editingInstance.value = null
		}).catch((res) => {
			console.error(res)
			toast.add({
				title: 'Error',
				description: res.details ? res.details : 'Failed to update federated instance. Check console for more details.',
			})
		}).finally(() => {
			registerOrUpdateLoading.value = false
		})
	} else {
		// Register new instance
		federatedStore.registerFederationInstance({
			instance_name: newInstanceName.value,
			url_address: newInstanceUrl.value,
			username: newInstanceUsername.value,
			password: newInstancePassword.value,
			enabled: newInstanceEnabled.value,
		}).then(() => {
			federatedStore.loadFederationInstances()
			showRegisterModal.value = false
		}).catch((res) => {
			console.error(res)
			toast.add({
				title: 'Error',
				description: res.details ? res.details : 'Failed to register new federated instance. Check console for more details.',
			})
		}).finally(() => {
			registerOrUpdateLoading.value = false
		})
	}
}
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<div class="flex flex-col md:flex-row">
			<UVerticalNavigation :links="settingsStore.links" class="md:w-1/5" />
			<div class="px-5 pb-5 md:w-4/5">
				<div v-if="userStore.isAdmin" class="admin-settings mb-3">
					<h3 class="mb-3 text-xl font-bold">Federated settings</h3>

					<UFormGroup
						size="md"
						class="py-3"
						label="Federated instances">

						<UButton
							class="my-3"
							variant="outline"
							icon="i-heroicons-plus-16-solid"
							color="cyan"
							@click="() => { showRegisterModal = true }">
							Register new instance
						</UButton>

						<UTable
							:columns="columns"
							:rows="rows">
							<template #instance_name-data="{ row }">
								{{ row.instance_name }}
							</template>
							<template #url_address-data="{ row }">
								{{ row.url_address }}
							</template>
							<template #username-data="{ row }">
								{{ row.username }}
							</template>
							<template #enabled-data="{ row }">
								<UBadge
									variant="soft"
									:color="row.enabled ? 'green' : 'red'">
									{{ row.enabled ? 'Yes' : 'No' }}
								</UBadge>
							</template>
							<template #created_at-data="{ row }">
								{{ new Date(row.created_at).toLocaleString() }}
							</template>
							<template #actions-data="{ row }">
								<div class="flex items-center gap-2">
									<UButton
										icon="i-heroicons-pencil-16-solid"
										variant="outline"
										color="cyan"
										size="sm"
										@click="() => {
											editingInstance = {
												...row,
											}
											showRegisterModal = true
										}">
										Edit
									</UButton>
									<UButton
										icon="i-heroicons-trash-16-solid"
										variant="outline"
										color="red"
										size="sm"
										:loading="deleting"
										@click="() => {
											deleting = true
											federatedStore.deleteFederationInstance(row.instance_name)
												.catch((res) => {
													console.error(res)
													toast.add({
														title: 'Error',
														description: res.details ? res.details : 'Failed to delete federated instance. Check console for more details.',
													})
												}).finally(() => {
													deleting = false
												})
										}">
										Delete
									</UButton>
								</div>
							</template>
						</UTable>

						<UModal v-model="showRegisterModal" :transition="false">
							<div class="p-4 overflow-y-auto">
								<h2 class="font-bold">
									{{ editingInstance !== null ? 'Edit instance' : 'Register new instance' }}
								</h2>

								<div class="flex flex-col gap-2 mt-3">
									<UFormGroup label="Instance name"
										class="flex justify-center flex-col w-full"
										:error="!newInstanceName || newInstanceName.length === 0 ? 'Instance name is required' : ''">
										<UInput v-model="newInstanceName" type="text" placeholder="Instance name" />
									</UFormGroup>
									<UFormGroup label="URL address"
										class="flex justify-center flex-col w-full"
										:error="!newInstanceUrl || newInstanceUrl.length === 0 ? 'URL address is required' : ''">
										<UInput v-model="newInstanceUrl" type="text" placeholder="URL address" />
									</UFormGroup>
									<UFormGroup label="Username"
										class="flex justify-center flex-col w-full"
										:error="!newInstanceUsername || newInstanceUsername.length === 0 ? 'Username is required' : ''">
										<UInput v-model="newInstanceUsername" type="text" placeholder="Username" />
									</UFormGroup>
									<UFormGroup label="Password"
										class="flex justify-center flex-col w-full"
										:error="!newInstancePassword || newInstancePassword.length === 0 ? 'Password is required' : ''">
										<UInput v-model="newInstancePassword" type="password"  placeholder="Password" autocomplete="off" />
									</UFormGroup>
									<UFormGroup label="Enabled"
										class="flex justify-center flex-col w-full">
										<UCheckbox v-model="newInstanceEnabled" :label="editingInstance !== null ? 'Enabled' : 'Enable after register'" />
									</UFormGroup>
								</div>

								<div class="flex justify-end mt-3">
									<UButton
										class="mr-2"
										variant="soft"
										color="white"
										@click="() => { showRegisterModal = false }">
										Cancel
									</UButton>
									<UButton
										variant="solid"
										color="cyan"
										:loading="registerOrUpdateLoading"
										:disabled="!registerNewInstanceValid"
										@click="handleRegisterOrEditInstance">
										{{ editingInstance !== null ? 'Update' : 'Register' }}
									</UButton>
								</div>
							</div>
						</UModal>
					</UFormGroup>
				</div>
			</div>
		</div>
	</AppContainer>
</template>
