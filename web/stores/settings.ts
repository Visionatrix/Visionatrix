export const useSettingsStore = defineStore('settingsStore', {
	state: () => ({
		links: [
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
			{
				label: 'ComfyUI',
				icon: 'i-heroicons-rectangle-group-16-solid',
				to: '/settings/comfyui',
			},
		],
		settingsMap: {
			huggingface_auth_token: {
				key: 'huggingface_auth_token',
				value: '',
				sensitive: true,
				admin: true,
			},
			google_proxy: {
				key: 'google_proxy',
				value: '',
				sensitive: true,
				admin: true,
			},
			google_api_key: {
				key: 'google_api_key',
				value: '',
				sensitive: true,
				admin: true,
			},
			google_api_key_user: {
				key: 'google_api_key',
				value: '',
				sensitive: false,
				admin: false,
			},
			gemini_model: {
				key: 'gemini_model',
				value: '',
				options: ['gemini-1.5-flash-002', 'gemini-1.5-pro-002'],
				sensitive: false,
				admin: true,
			},
			ollama_url: {
				key: 'ollama_url',
				value: '',
				sensitive: true,
				admin: true,
			},
			ollama_vision_model: {
				key: 'ollama_vision_model',
				value: '',
				sensitive: false,
				admin: true,
				loading: false,
				options: [] as OllamaModelItem[],
			},
			ollama_llm_model: {
				key: 'ollama_llm_model',
				value: '',
				sensitive: false,
				admin: true,
				loading: false,
				options: [] as OllamaModelItem[],
			},
			ollama_keepalive: {
				key: 'ollama_keepalive',
				value: '',
				sensitive: true,
				admin: true,
			},
			translations_provider: {
				key: 'translations_provider',
				value: '',
				options: ['ollama', 'gemini'],
				sensitive: false,
				admin: true,
			},
			comfyui_models_folder: {
				key: 'comfyui_models_folder',
				value: '',
				sensitive: false,
				admin: true,
			},
			civitai_auth_token: {
				key: 'civitai_auth_token',
				value: '',
				sensitive: true,
				admin: true,
			},
		} as VixSettingsMap,
		localSettings: {
			showComfyUiNavbarButton: true,
		},
		isNextcloudIntegration: false,
		ollamaFetchError: '',
	}),

	actions: {
		async fetchAllSettings() {
			const userStore = useUserStore()
			userStore.fetchUserInfo().then(async () => {
				const allSettings = await this.getAllSettings()
				console.debug('[DEBUG] All settings:', allSettings)
				Object.keys(allSettings).forEach((key: string) => {
					if (this.settingsMap[key + '_user']) {
						this.settingsMap[key + '_user'].value = allSettings[key]
					} else if (this.settingsMap[key]) {
						this.settingsMap[key].value = allSettings[key]
					}
				})
			})
		},

		async fetchAllGlobalSettings() {
			const userStore = useUserStore()
			userStore.fetchUserInfo().then(async () => {
				if (!userStore.isAdmin) {
					return
				}
				const allGlobalSettings = await this.getAllGlobalSettings()
				console.debug('[DEBUG] All global settings:', allGlobalSettings)
				Object.keys(allGlobalSettings).forEach((key: string) => {
					if (this.settingsMap[key]) {
						this.settingsMap[key].value = allGlobalSettings[key]
					}
				})
			})
		},

		async fetchAllUserSettings() {
			const userStore = useUserStore()
			userStore.fetchUserInfo().then(async () => {
				const allUserSettings = await this.getAllUserSettings()
				console.debug('[DEBUG] All user settings:', allUserSettings)
				Object.keys(allUserSettings).forEach((key: string) => {
					const userSettingKey = key + '_user'
					if (this.settingsMap[userSettingKey]) {
						this.settingsMap[userSettingKey].value = allUserSettings[key]
					}
				})
			})
		},

		loadAllSettings() {
			return Promise.all([
				this.fetchAllUserSettings(),
				this.fetchAllGlobalSettings(),
				this.getOllamaModelsList(),
			])
		},

		getAllSettings(): Promise<SavedSetting> {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch('/settings/get_all', {
				method: 'GET',
			})
		},

		getAllGlobalSettings(): Promise<SavedSetting> {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch('/settings/global_all', {
				method: 'GET',
			})
		},

		getAllUserSettings(): Promise<SavedSetting> {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch('/settings/user_all', {
				method: 'GET',
			})
		},

		getGlobalSetting(key: string) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch(`/settings/global?key=${key}`, {
				method: 'GET',
			})
		},

		saveGlobalSetting(key: string, value: any, sensitive: boolean) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch('/settings/global', {
				method: 'POST',
				body: JSON.stringify({
					key,
					value,
					sensitive,
				}),
			})
		},

		getUserSetting(key: string) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch(`/settings/user?key=${key}`, {
				method: 'GET',
			})
		},

		saveUserSetting(key: string, value: any) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch('/settings/user', {
				method: 'POST',
				body: JSON.stringify({
					key,
					value,
				}),
			})
		},

		getComfyUiFolderListing() {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch('/settings/comfyui/folders', {
				method: 'GET',
			})
		},

		performComfyUiAutoconfig(models_dir: string) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch('/settings/comfyui/folders/autoconfig', {
				method: 'POST',
				body: {
					models_dir,
				},
			})
		},

		getOrphanModelsList() {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch('/models/orphan', {
				method: 'GET',
			}).then((res: any) => {
				console.debug('[DEBUG] Orphan models:', res)
				return res
			})
		},

		getOllamaModelsList() {
			const { $apiFetch } = useNuxtApp()
			this.settingsMap.ollama_vision_model.loading = true
			this.settingsMap.ollama_llm_model.loading = true
			return $apiFetch('/settings/ollama/models', {
				method: 'GET',
			}).then((res: any) => {
				console.debug('[DEBUG] Ollama models:', res)
				this.ollamaFetchError = ''
				this.settingsMap.ollama_vision_model.options = res || []
				this.settingsMap.ollama_llm_model.options = res || []
				return res
			}).catch((err) => {
				console.debug('[DEBUG] Ollama models fetch error:', err)
				this.ollamaFetchError = err || 'Failed to fetch Ollama models list'
			}).finally(() => {
				this.settingsMap.ollama_vision_model.loading = false
				this.settingsMap.ollama_llm_model.loading = false
			})
		},

		deleteOrphanModel(full_path: string, creation_time: number) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch(`/models/orphan?full_orphan_path=${full_path}&file_creation_time=${creation_time}`, {
				method: 'DELETE',
			})
		},

		loadLocalSettings() {
			const localSettings = localStorage.getItem('localSettings')
			if (localSettings) {
				this.localSettings = JSON.parse(localSettings)
			}

			const config = useRuntimeConfig()
			if (config.app.isNextcloudIntegration && config.app.isNextcloudIntegration === 'true') {
				this.isNextcloudIntegration = true
			}
		},

		saveLocalSettings() {
			localStorage.setItem('localSettings', JSON.stringify(this.localSettings))
		},
	},
})

export interface VixSettingsMap {
	[key: string]: VixSetting
}

export interface VixSetting {
	key: string
	value: any
	sensitive: boolean
	admin: boolean
	options?: any[]
	loading?: boolean
}

export interface SavedSetting {
	[key: string]: any
}

export interface ComfyUiFolder {
	full_path: string
	create_time: string
	total_size: number
}

export interface ComfyUiFolderListing {
	[key: string]: ComfyUiFolder[]
}

export interface ResModelHashes {
	[key: string]: string
}

export interface ResModelRegEx {
	input_value: string
	input_name: string
}

export interface ResModel {
	name: string
	types: string[]
	filename: string
	url: string
	homepage: string
	hash: string
	hashes: ResModelHashes
	regexes: ResModelRegEx[]
	gated: boolean
}

export interface OrphanModel {
	path: string
	full_path: string
	size: number
	creation_time: number
	res_model: ResModel
	possible_flows: string[]
}

export interface OllamaModelItem {
	model: string
	size: string
	modified_at: string
}
