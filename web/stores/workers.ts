export const useWorkersStore = defineStore('workersStore', {
	state: () => ({
		loading: false,
		workers: <WorkerInfo[]>[],
		interval: null as any,
	}),

	actions: {
		async loadWorkers() {
			const { $apiFetch } = useNuxtApp()
			return await $apiFetch('/workers/info')
				.then((res: any) => {
					this.workers = <WorkerInfo[]>res
				})
		},

		async fetchWorkersInfo() {
			this.loading = true
			return this.loadWorkers().finally(() => {
				this.loading = false
			})
		},

		deleteWorker(worker_ids: string[]) {
			const { $apiFetch } = useNuxtApp()
			const worker_id = Array.isArray(worker_ids) ? worker_ids.map(id => `worker_id=${id}`).join('&') : `worker_id=${worker_ids}`
			return $apiFetch(`/workers?${worker_id}`, {
				method: 'DELETE',
			}).then((res: any) => {
				if (res?.detail !== '') {
					console.error('Error deleting workers: ', res.detail)
				} else {
					this.workers = this.workers.filter(worker => worker.worker_id !== worker_id)
				}
				return res
			}).catch((res: any) => {
				console.error('Error deleting workers: ', res?.detail)
				return res
			})
		},

		startPolling() {
			this.fetchWorkersInfo()
			this.interval = setInterval(() => {
				this.loadWorkers()
			}, 3000)
		},

		stopPolling() {
			clearInterval(this.interval)
		},

		async setTasksToGive(worker_id: string, tasks_to_give: any[]) {
			const { $apiFetch } = useNuxtApp()
			return await $apiFetch('/workers/tasks', {
				method: 'POST',
				body: JSON.stringify({ worker_id, tasks_to_give }),
			}).then((res: any) => {
				if (res?.error !== '') {
					console.error(`Error setting tasks to give for ${worker_id}: `, res.error)
				}
			}).catch((res: any) => {
				console.error(`Error setting tasks to give for ${worker_id}: `, res.error)
			})
		},

		updateWorkerOptions(worker_id: string, options: any) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch('/workers/settings', {
				method: 'POST',
				body: JSON.stringify({ worker_id, ...options }),
			}).catch((res: any) => {
				console.error(`Error updating worker options for ${worker_id}: `, res.error)
				return res
			})
		}
	},
})

export interface WorkerInfo {
	worker_status?: string
	device_name: string
	device_type: string
	embedded_version: string
	last_seen: string
	tasks_to_give: string[]
	os: string
	ram_free: number
	ram_total: number
	torch_vram_free: number
	torch_vram_total: number
	version: string
	vram_free: number
	vram_total: number
	worker_id: string
	worker_version: string
	user_id: string
	pytorch_version: string
	engine_details: {
		disable_smart_memory: boolean
		vram_state: string
		cache_type: string
		cache_size: number
		vae_cpu: boolean
		reserve_vram: number
	}
	federated_instance_name: string
	empty_task_requests_count: number
	smart_memory: boolean
	cache_type: string
	cache_size: number
	vae_cpu: boolean
	reserve_vram: number
}
