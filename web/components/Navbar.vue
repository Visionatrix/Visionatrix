<script setup lang="ts">
const colorMode = useColorMode()

function toggleColorMode() {
	if (colorMode.preference === 'system') {
		colorMode.preference = 'light'
	} else if (colorMode.preference === 'light') {
		colorMode.preference = 'dark'
	} else {
		colorMode.preference = 'system'
	}
}

const themingToggleIconClass = computed(() => {
	if (colorMode.preference === 'system') {
		return 'i-heroicons-computer-desktop-20-solid'
	}
	if (colorMode.preference === 'light') {
		return 'i-heroicons-sun-solid'
	}
	if (colorMode.preference === 'dark') {
		return 'i-heroicons-moon-solid'
	}
	return 'i-heroicons-computer-desktop-20-solid'
})

const userStore = useUserStore()
const settingsStore = useSettingsStore()
</script>

<template>
	<AppContainer class="w-full z-[60]">
		<header class="flex w-full flex-col lg:flex-row justify-between items-center my-5">
			<div class="flex w-full items-center justify-between">
				<ULink to="/" class="text-lg mr-3">
					<span class="font-bold text-neutral-400 hover:text-neutral-300 mr-1">Visionatrix</span>
				</ULink>
				<div class="flex items-center">
					<UTooltip v-if="userStore.isAdmin && settingsStore.localSettings.showComfyUiNavbarButton"
						text="Open ComfyUI">
						<UButton 
							class="lg:px-3 py-2"
							icon="i-heroicons-rectangle-group-16-solid"
							variant="ghost"
							color="white"
							:to="buildBackendUrl() + '/comfy'"
							target="_blank" />
					</UTooltip>

					<ULink to="/settings">
						<UButton class="lg:px-3 py-2" icon="i-heroicons-cog-6-tooth-20-solid" variant="ghost" color="white" />
					</ULink>

					<NotificationsPopover />

					<UButton
						:icon="themingToggleIconClass"
						variant="ghost"
						color="white"
						class="flex lg:px-3 py-2 text-black dark:text-white hover:bg-transparent"
						@click="toggleColorMode" />
				</div>
			</div>
		</header>
	</AppContainer>
</template>
