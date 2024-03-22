export const useSystemStore = defineStore('systemStore', {
	state: () => ({
		loading: false,
		stats: <Stats>{},
	}),

	getters: {
		gpusVramUsage(state) {
			return state.stats.devices.reduce((acc, gpu_device: DeviceStats) => {
				acc.vram_total += gpu_device.vram_total
				acc.vram_free += gpu_device.vram_free
				return acc
			}, {
				vram_total: 0,
				vram_free: 0,
			})
		},
	},

	actions: {
		async fetchStats() {
			this.loading = true
			return await $fetch(`${buildBackendApiUrl()}/system_stats`)
				.then((res: any) => {
					this.stats = <Stats>res
					console.debug(`Total VRAM usage: ${this.gpusVramUsage.vram_free}/${this.gpusVramUsage.vram_total} (${(this.gpusVramUsage.vram_free / this.gpusVramUsage.vram_total * 100).toFixed(2)}%)`)
				}).finally(() => {
					this.loading = false
				})
		},

		startStatsPolling() {
			this.fetchStats()
			setInterval(() => {
				this.fetchStats()
			}, 3000)
		},
	},

})

export interface SystemStats {
	os: string
	python_version: string
	embedded_version: string
}

export interface DeviceStats {
	name: string
	type: string
	index: number
	vram_total: number
	vram_free: number
	torch_vram_total: number
	torch_vram_free: number
}

export interface Stats {
	system: SystemStats
	devices: DeviceStats[]
}
