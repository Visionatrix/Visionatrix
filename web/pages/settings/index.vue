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

const settingsStore = useSettingsStore()

function saveChanges() {
	console.debug('Saving settings', settingsStore.settingsMap.value)
	Promise.all(Object.keys(settingsStore.settingsMap.value).map((key) => {
		if (settingsStore.settingsMap[key].admin && userStore.isAdmin) {
			return settingsStore.saveGlobalSetting(settingsStore.settingsMap[key].key, settingsStore.settingsMap.value[key].value, settingsStore.settingsMap.value[key].sensitive)
		}
		return settingsStore.saveUserSetting(settingsStore.settingsMap[key].key, settingsStore.settingsMap.value[key].value)
	})).then(() => {
		const toast = useToast()
		toast.add({
			title: 'Settings saved',
			description: 'Settings saved successfully',
		})
	}).catch((error) => {
		const toast = useToast()
		toast.add({
			title: 'Error saving setting',
			description: error.message,
		})
	})
}

const userStore = useUserStore()
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<div class="flex flex-col md:flex-row">
			<UVerticalNavigation :links="links" class="md:w-1/5" />
			<div class="px-5 md:w-4/5">
				<h2 class="mb-3 text-xl">Settings</h2>
				<div v-if="userStore.isAdmin" class="admin-settings mb-3">
					<h3 class="mb-3">Admin settings</h3>
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
						description="Bearer authentication token from your Huggingface account to allow downloading gated models with limited access">
						<UInput
							v-model="settingsStore.settingsMap['huggingface_auth_token'].value"
							placeholder="Huggingface Auth token"
							class="w-full"
							type="password"
							icon="i-heroicons-shield-check"
							size="md"
						/>
					</UFormGroup>
					<UFormGroup
						size="md"
						class="py-3"
						label="Gemini API key"
						description="Global Gemini API key, required for Flows where ComfyUI-Gemini Node is used">
						<UInput
							v-model="settingsStore.settingsMap['gemini_token'].value"
							placeholder="Gemini API key"
							class="w-full"
							type="password"
							icon="i-heroicons-shield-check"
							size="md"
						/>
					</UFormGroup>
				</div>
				<div class="user-settings mb-3">
					<h3 class="mb-3">User settings</h3>
					<UFormGroup
						size="md"
						class="py-3"
						label="Proxy"
						description="Proxy configuration string">
						<UInput
							v-model="settingsStore.settingsMap['proxy'].value"
							placeholder="Proxy"
							class="w-full"
							type="password"
							icon="i-heroicons-shield-check"
							size="md"
						/>
					</UFormGroup>
					<UFormGroup
						size="md"
						class="py-3"
						label="Gemini API key"
						description="Gemini API key, required for Flows where ComfyUI-Gemini Node is used">
						<UInput
							v-model="settingsStore.settingsMap['gemini_token_user'].value"
							placeholder="Gemini API key"
							class="w-full"
							type="password"
							icon="i-heroicons-shield-check"
							size="md"
						/>
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