export const useWorkersStore = defineStore('workersStore', {
	state: () => ({
		loading: false,
		workers: <WorkerInfo[]>[],
	}),

	actions: {
		async fetchWorkersInfo() {
			const { $apiFetch } = useNuxtApp()
			this.loading = true
			return await $apiFetch('/workers_info')
				.then((res: any) => {
					this.workers = <WorkerInfo[]>res
					console.debug(`workers (${this.workers.length}): `, this.workers)
				}).finally(() => {
					this.loading = false
				})
		},

		startPolling() {
			this.fetchWorkersInfo()
			setInterval(() => {
				this.fetchWorkersInfo()
			}, 3000)
		},
	},

})

export interface WorkerInfo {
	device_name: string
	device_type: string
	embedded_version: string
	id: number
	last_seen: string
	os: string
	ram_free: number
	ram_total: number
	torch_vram_free: number
	torch_vram_total: number
	version: string
	vram_free: number
	vram_total: number
	worker_id: string
}
