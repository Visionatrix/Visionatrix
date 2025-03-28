export const useFederatedStore = defineStore('federatedStore', {
	state: () => ({
		loading: false,
		instances: <FederationInstance[]>[],
		interval: null as any,
	}),

	actions: {
		async loadFederationInstances() {
			const { $apiFetch } = useNuxtApp()
			this.loading = true
			return await $apiFetch('/federation/instances')
				.then((res: any) => {
					this.instances = <FederationInstance[]>res
				}).finally(() => {
					this.loading = false
				})
		},

		startPolling() {
			this.loadFederationInstances()
			this.interval = setInterval(() => {
				this.loadFederationInstances()
			}, 3000)
		},

		stopPolling() {
			clearInterval(this.interval)
		},

		registerFederationInstance(params: any) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch('/federation/instance', {
				method: 'POST',
				body: JSON.stringify({
					instance_name: params.instance_name,
					url_address: params.url_address,
					username: params.username,
					password: params.password,
					enabled: params.enabled,
				}),
			})
		},

		updateFederationInstance(params: any) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch(`/federation/instance?instance_name=${params.instance_name}`, {
				method: 'PUT',
				body: JSON.stringify({
					url_address: params.url_address,
					username: params.username,
					password: params.password,
					enabled: params.enabled,
				}),
			})
		},

		deleteFederationInstance(instance_name: string) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch(`/federation/instance?instance_name=${instance_name}`, {
				method: 'DELETE',
			}).then(() => {
				this.loadFederationInstances()
			})
		},
	},
})

export interface FederationInstance {
	instance_name: string
	url_address: string
	username: string
	password: string
	enabled: boolean
	created_at?: string
}
