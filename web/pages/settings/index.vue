<script setup lang="ts">
useHead({
	title: 'Settings - Visionatrix',
	meta: [
		{
			name: 'description',
			content: 'Settings - Visionatrix',
		},
	],
})

const links = [
	{
		label: 'Settings',
		icon: 'i-heroicons-cog-6-tooth-20-solid',
		to: '/settings',
	},
	{
		label: 'Workers information',
		icon: 'i-heroicons-chart-bar-16-solid',
		to: '/settings/workers',
	},
]

const userStore = useUserStore()
const settingsStore = useSettingsStore()
const toast = useToast()

function saveChanges() {
	console.debug('Saving settings', settingsStore.settingsMap)
	Promise.all(Object.keys(settingsStore.settingsMap).map((key) => {
		if (settingsStore.settingsMap[key].admin && userStore.isAdmin) {
			return settingsStore.saveGlobalSetting(settingsStore.settingsMap[key].key, settingsStore.settingsMap[key].value, settingsStore.settingsMap[key].sensitive)
		}
		return settingsStore.saveUserSetting(settingsStore.settingsMap[key].key, settingsStore.settingsMap[key].value)
	})).then(() => {
		toast.add({
			title: 'Settings saved',
			description: 'Settings saved successfully',
		})
	}).catch((error) => {
		toast.add({
			title: 'Error saving setting',
			description: error.message,
		})
	})
}

const flowsStore = useFlowsStore()
const flowFileInput = ref(null)
const uploadingFlow = ref(false)

function uploadFlow() {
	// @ts-ignore
	const file = flowFileInput.value.$refs.input.files[0] || null
	if (!file) {
		toast.add({
			title: 'No file selected',
			description: 'Please select a file to upload',
		})
		return
	}

	uploadingFlow.value = true
	flowsStore.uploadFlow(file).then((res: any) => {
		console.debug('uploadFlow', res)
		if (res && 'detail' in res && res?.detail !== '') {
			toast.add({
				title: 'Error uploading flow',
				description: res.detail,
			})
			return
		} else {
			toast.add({
				title: 'Flow uploaded',
				description: 'Flow uploaded successfully',
			})
		}
		// @ts-ignore
		flowFileInput.value.$refs.input.value = ''
	}).catch((e) => {
		console.debug('uploadFlow error', e)
		toast.add({
			title: 'Error uploading flow',
			description: e.message,
		})
	}).finally(() => {
		uploadingFlow.value = false
	})
}

watch(() => flowsStore.outputMaxSize, () => {
	flowsStore.saveUserOptions()
})

onBeforeMount(() => {
	settingsStore.loadAllSettings()
})
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<div class="flex flex-col md:flex-row">
			<UVerticalNavigation :links="links" class="md:w-1/5" />
			<div class="px-5 pb-5 md:w-4/5">
				<div v-if="userStore.isAdmin" class="admin-settings mb-3">
					<h3 class="mb-3 text-xl font-bold">Admin preferences (global settings)</h3>
					<div class="flex items-center">
						<UIcon name="i-heroicons-question-mark-circle" class="mr-2 text-amber-400" />
						<p class="text-amber-400">
							<span>Access tokens are required for&nbsp;</span>
							<a class="hover:underline underline-offset-4" href="https://visionatrix.github.io/VixFlowsDocs/GatedModels.html" target="_blank">gated models</a>.
						</p>
					</div>
					<UFormGroup
						size="md"
						class="py-3"
						label="Huggingface Auth token"
						description="Bearer authentication token from your Huggingface account to allow downloading gated models with limited access.">
						<UInput
							v-model="settingsStore.settingsMap['huggingface_auth_token'].value"
							placeholder="Huggingface Auth token"
							class="w-full"
							type="password"
							icon="i-heroicons-shield-check"
							size="md"
							autocomplete="off"
						/>
					</UFormGroup>

					<UDivider class="mt-3" label="Gemini" />
					<p class="text-slate text-sm text-orange-300 dark:text-orange-100 text-center">Can be used by flows and as a translation provider</p>
					<UFormGroup
						size="md"
						class="py-3"
						label="Google API key">
						<template #description>
							Global Google API key, required for Flows, e.g. where ComfyUI-Gemini Node is used.
							Instruction how to obtain key <a class="hover:underline font-bold" href="https://ai.google.dev/gemini-api/docs/api-key">here</a>.
						</template>
						<UInput
							v-model="settingsStore.settingsMap['google_api_key'].value"
							placeholder="Google API key"
							class="w-full"
							type="password"
							icon="i-heroicons-shield-check"
							size="md"
							autocomplete="off"
						/>
					</UFormGroup>
					<UFormGroup
						size="md"
						class="py-3"
						label="Gemini model"
						description="Override Gemini model to use.">
						<div class="flex items-center">
							<USelect
								v-model="settingsStore.settingsMap.gemini_model.value"
								color="white"
								variant="outline"
								placeholder="Select Gemini model"
								:options="settingsStore.settingsMap.gemini_model.options" />
							<UButton
								v-if="settingsStore.settingsMap.gemini_model.value"
								icon="i-heroicons-x-mark"
								variant="outline"
								color="white"
								class="ml-2"
								@click="() => settingsStore.settingsMap.gemini_model.value = ''" />
						</div>
					</UFormGroup>
					<UFormGroup
						size="md"
						class="py-3"
						label="Proxy (for Google)">
						<template #description>
							Proxy to access Gemini configuration <a class="hover:underline font-bold" href="https://visionatrix.github.io/VixFlowsDocs/AdminManual/Installation/proxy_gemini/">string</a>.
						</template>
						<UInput
							v-model="settingsStore.settingsMap.google_proxy.value"
							placeholder="Proxy"
							class="w-full"
							type="text"
							size="md"
							autocomplete="off"
						/>
					</UFormGroup>

					<UDivider class="mt-3" label="Ollama" />
					<p class="text-slate text-sm text-orange-300 dark:text-orange-100 text-center">Can be used by flows and as a translation provider</p>
					<UFormGroup
						size="md"
						class="py-3"
						label="Ollama URL"
						description="URL to server where Ollama is running.">
						<UInput
							v-model="settingsStore.settingsMap.ollama_url.value"
							placeholder="Ollama URL"
							class="w-full"
							type="text"
							size="md"
							autocomplete="off"
						/>
					</UFormGroup>
					<UFormGroup
						size="md"
						class="py-3"
						label="Ollama Vision Model"
						description="Override Ollama Vision model used by default.">
						<UInput
							v-model="settingsStore.settingsMap.ollama_vision_model.value"
							placeholder="Ollama Vision Model"
							class="w-full"
							type="text"
							size="md"
							autocomplete="off"
						/>
					</UFormGroup>
					<UFormGroup
						size="md"
						class="py-3"
						label="Ollama LLM Model"
						description="Override Ollama LLM model used by default.">
						<UInput
							v-model="settingsStore.settingsMap.ollama_llm_model.value"
							placeholder="Ollama Vision Model"
							class="w-full"
							type="text"
							size="md"
							autocomplete="off"
						/>
					</UFormGroup>
					<UFormGroup
						size="md"
						class="py-3"
						label="Ollama Keepalive"
						description="Set Ollama keepalive time (e.g. 30s) for how long the model is kept in memory.">
						<UInput
							v-model="settingsStore.settingsMap.ollama_keepalive.value"
							placeholder="Ollama LLM Model"
							class="w-full"
							type="text"
							size="md"
							autocomplete="off"
						/>
					</UFormGroup>

					<UDivider class="mt-3" label="Prompt translations" />
					<UFormGroup
						size="md"
						class="py-3"
						label="Translations provider"
						description="Prompt translations provider. Empty if not enabled.">
						<div class="flex items-center">
							<USelect
								v-model="settingsStore.settingsMap.translations_provider.value"
								color="white"
								variant="outline"
								placeholder="Select translations provider"
								:options="settingsStore.settingsMap.translations_provider.options" />
							<UButton
								v-if="settingsStore.settingsMap.translations_provider.value"
								icon="i-heroicons-x-mark"
								variant="outline"
								color="white"
								class="ml-2"
								@click="() => settingsStore.settingsMap.translations_provider.value = ''" />
						</div>
					</UFormGroup>
				</div>
				<div v-if="userStore.isAdmin" class="upload-flow mb-5 py-4 rounded-md">
					<h4 class="mb-3 font-bold">Upload Flow</h4>
					<p class="text-gray-400 text-sm mb-3">
						Upload a Visionatrix workflow file (.json) to add it to the available flows.
						On successful upload of the valid workflow file, the installation will start automatically.
					</p>
					<div class="flex items-center space-x-3">
						<UInput
							ref="flowFileInput"
							type="file"
							accept=".json"
							class="w-auto" />
						<UButton
							icon="i-heroicons-arrow-up-tray-16-solid"
							variant="outline"
							:loading="uploadingFlow"
							@click="uploadFlow">
							Upload Flow
						</UButton>
					</div>
				</div>
				<div class="user-settings mb-3">
					<h3 class="mb-3 text-xl font-bold">User preferences (overrides global)</h3>
					<UFormGroup
						size="md"
						class="py-3"
						label="Google API key">
						<template #description>
							Google API key, required for Flows, e.g. where ComfyUI-Gemini Node is used.
							Instruction how to obtain key <a class="hover:underline font-bold" href="https://ai.google.dev/gemini-api/docs/api-key">here</a>.
						</template>
						<UInput
							v-model="settingsStore.settingsMap.google_api_key_user.value"
							placeholder="Google API key"
							class="w-full"
							type="password"
							icon="i-heroicons-shield-check"
							size="md"
							autocomplete="off"
						/>
					</UFormGroup>

					<UDivider class="mt-3" label="UI preferences" />
					<p class="text-slate text-sm text-orange-300 dark:text-orange-100 text-center">Stored in browser local storage</p>

					<UFormGroup
						size="md"
						class="py-3"
						label="Outputs maximum image size"
						description="To keep the output seamless, we limit the size of the outputs (512px by default).">
						<USelectMenu
							v-model="flowsStore.$state.outputMaxSize"
							:options="['512', '768', '1024', '1536', '2048']" />
					</UFormGroup>
				</div>
				<UButton
					icon="i-heroicons-check-16-solid"
					@click="saveChanges">
					Save
				</UButton>
			</div>
		</div>
	</AppContainer>
</template>
