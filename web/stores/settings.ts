export const useSettingsStore = defineStore('settingsStore', {
	state: () => ({
		settingsMap: {
			huggingface_auth_token: {
				key: 'huggingface_auth_token',
				value: '',
				sensitive: true,
				admin: true,
			},
			proxy: {
				key: 'proxy',
				value: '',
				sensitive: true,
				admin: true,
			},
			gemini_token: {
				key: 'gemini_token',
				value: '',
				sensitive: true,
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
				sensitive: true,
				admin: true,
			},
			gemini_token_user: {
				key: 'gemini_token',
				value: '',
				sensitive: false,
				admin: false,
			},
		} as VixSettingsMap,
	}),

	actions: {
		loadSettings() {
			const userStore = useUserStore()
			userStore.fetchUserInfo().then(() => {
				return Promise.all(Object.keys(this.settingsMap).map((key) => {
					if (this.settingsMap[key].admin && userStore.isAdmin) {
						return this.getGlobalSetting(this.settingsMap[key].key).then((value) => {
							this.settingsMap[key].value = value
						})
					}
					return this.getUserSetting(this.settingsMap[key].key).then((value) => {
						this.settingsMap[key].value = value
					})
				}))
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
}
