export const useFlowsStore = defineStore('flowsStore', {
	state: () => ({
		loading: {
			flows_available: false,
			flows_installed: false,
			tasks_history: false,
			current_flow: true,
		},
		page: 1,
		pageSize: 9,
		running: <FlowRunning[]>[],
		installing: <FlowInstalling[]>[],
		resultsPage: 1,
		resultsPageSize: 5,
		flow_results_filter: '',
		flow_results: <FlowResult[]>[],
		flows_available: <Flow[]>[],
		flows_installed: <Flow[]>[],
		flows_tags_filter: <string[]>[],
		sub_flows: <Flow[]>[],
		flows_favorite: <string[]>[],
		current_flow: <Flow>{},
		showNotificationChip: false,
		runningInterval: <any>{},
	}),
	getters: {
		flows(state): Flow[] {
			if (state.flows_tags_filter.length > 0) {
				return [
					...state.flows_installed,
					...state.flows_available,
				].filter(flow => state.flows_tags_filter.every(tag => flow.tags.includes(tag)))
			}
			return [
				...state.flows_installed,
				...state.flows_available,
			]
		},
		flowsTags(state): string[] {
			const flows = [
				...state.flows_installed,
				...state.flows_available,
			]
			return Array.from(new Set(flows.flatMap(flow => flow.tags)))
		},
		paginatedFlows(state) {
			if (state.flows_tags_filter.length > 0) {
				return paginate([
					...state.flows_installed,
					...state.flows_available,
				].filter(flow => state.flows_tags_filter.every(tag => flow.tags.includes(tag))), state.page, state.pageSize) as Flow[]
			}
			return paginate([
				...state.flows_installed,
				...state.flows_available,
			], state.page, state.pageSize) as Flow[]
		},
		flowByName() {
			return (name: string) => this.flows.find(flow => flow.name === name)
		},
		flowResultsByName(state) {
			return (name: string) => {
				if (state.flow_results_filter !== '') {
					return state.flow_results.filter(task => task.flow_name === name && task.input_params_mapped['prompt'].value.includes(state.flow_results_filter))
				}
				return state.flow_results.filter(task => task.flow_name === name)
			}
		},
		flowResultsByNamePaginated(state) {
			return (name: string) => {
				if (state.flow_results_filter !== '') {
					return paginate(state.flow_results.filter(task => task.flow_name === name && task.input_params_mapped['prompt'].value.includes(state.flow_results_filter) && task.parent_task_id === null).reverse(), state.resultsPage, state.resultsPageSize) as FlowResult[]
				}
				return paginate(state.flow_results.filter(task => task.flow_name === name && task.parent_task_id === null).reverse(), state.resultsPage, state.resultsPageSize) as FlowResult[]
			}
		},
		flowInstallingByName(state) {
			return (name: string) => state.installing.find(flow => flow.flow_name === name) ?? null
		},
		flowsRunningByName(state) {
			return (name: string) => state.running.filter(flow => flow.flow_name === name) ?? null
		},
		flowsRunningByNameWithErrors(state) {
			return (name: string) => state.running.filter(flow => flow.flow_name === name && flow.error) ?? null
		},
		currentFlow(state): Flow {
			return state.current_flow
		},
		isFlowFavorite(state) {
			return (name: string) => state.flows_favorite.includes(name)
		},
		isFlowInstalled(state) {
			return (name: string) => state.flows_installed.filter(flow => flow.name === name).length > 0 && state.installing.filter(flow => flow.flow_name === name).length === 0
		},
	},
	actions: {
		async fetchFlows() {
			await Promise.all([
				this.fetchFlowsAvailable(),
				this.fetchFlowsInstalled(),
			])
				.then(() => {
					this.loadFavorites()
					this.loadUserOptions()
					this.fetchFlowResults().then((tasks_history) => {
						this.initFlowResultsData(tasks_history)
					}).then(() => {
						this.restorePollingProcesses()
					})
				})
				.then(() => {
					const route = useRoute()
					if (route.params.name) {
						this.loading.current_flow = true
						this.setCurrentFlow(<string>route.params.name)
					}
				})
		},

		async fetchFlowsAvailable() {
			const { $apiFetch } = useNuxtApp()
			this.loading.flows_available = true
			const flows = await $apiFetch('/flows/not-installed', {
				method: 'GET',
				timeout: 15000,
			}).then((res) => {
				console.debug('not_installed: ', res)
				this.loading.flows_available = false
				this.flows_available = <Flow[]>res
				this.flows_available.sort(this.sortByFlowNameCallback)
			}).catch((e) => {
				console.debug('error fetching flows:', e)
				this.loading.flows_available = false
				const toast = useToast()
				toast.add({
					title: 'Failed to fetch available flows',
					description: e.message,
					timeout: 0,
				})
			})
			return flows
		},

		async fetchFlowsInstalled() {
			const { $apiFetch } = useNuxtApp()
			console.debug('fetching installed flows')
			this.loading.flows_installed = true
			const flows = await $apiFetch('/flows/installed', {
				method: 'GET',
				timeout: 15000,
			}).then((res) => {
				console.debug('installed_flows: ', res)
				this.loading.flows_installed = false
				this.flows_installed = <Flow[]>res
				this.flows_installed.sort(this.sortByFlowNameCallback)
			}).catch((e) => {
				console.debug('error fetching installed flows:', e)
				this.loading.flows_installed = false
				const toast = useToast()
				toast.add({
					title: 'Failed to fetch installed flows',
					description: e.message,
					timeout: 0,
				})
			})
			return flows
		},

		async fetchFlowResults(): Promise<TasksHistory> {
			const { $apiFetch } = useNuxtApp()
			this.loading.tasks_history = true
			return await $apiFetch('/tasks/progress', {
				method: 'GET',
			}).then((res) => {
				this.loading.tasks_history = false
				return <TasksHistory>res
			})
		},

		initFlowResultsData(res: TasksHistory) {
			console.debug('tasks_history:', res)

			const runningFlows: FlowRunning[] = []
			const finishedFlows: FlowResult[] = []

			Object.keys(res).forEach((task_id) => {
				const task = <TaskHistoryItem>res[task_id]
				const input_params_mapped_updated: any = {}
				Object.keys(task.input_params).forEach((key) => {
					if (key === 'seed') {
						input_params_mapped_updated[key] = {
							value: task.input_params[key],
							display_name: 'Seed',
						}
					} else {
						input_params_mapped_updated[key] = {
							value: task.input_params[key],
							display_name: this.flows_installed.find(flow => flow.name === task.name)?.input_params.find(param => param.name === key)?.display_name,
						}
					}
				})
				if (task.progress < 100) {
					runningFlows.push(<FlowRunning>{
						task_id: task_id,
						flow_name: task.name,
						progress: task.progress,
						input_files: task.input_files || [],
						input_params_mapped: input_params_mapped_updated || null,
						error: task?.error || null,
						outputs: task.outputs,
						execution_time: task.execution_time || null,
						child_tasks: task.child_tasks || [],
						parent_task_id: task.parent_task_id,
					})
				} else if (task.progress === 100) {
					finishedFlows.push(<FlowResult>{
						task_id: task_id,
						flow_name: task.name,
						outputs: task.outputs,
						input_params_mapped: input_params_mapped_updated || null,
						execution_time: task.execution_time || 0,
						child_tasks: task.child_tasks || [],
						parent_task_id: task.parent_task_id,
						progress: task.progress,
					}) // TODO: refactor to use TaskHistoryItem common task structure in all places
				}
			})
			if (runningFlows && runningFlows.length > 0) {
				console.debug('loading running flows:', runningFlows)
				this.running = <FlowRunning[]>runningFlows ?? []
			}
			console.debug('loading finished flows:', finishedFlows)
			this.flow_results = <FlowResult[]>finishedFlows ?? []
		},

		async setupFlow(flow: Flow) {
			const { $apiFetch } = useNuxtApp()
			return await $apiFetch(`/flows/flow?name=${flow.name}`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
			}).then((res) => {
				console.debug(res)
				this.installing.push({
					flow_name: flow.name,
					progress: 0,
				})
				this.startFlowInstallingPolling(flow.name)
			}).catch((e) => {
				console.debug(e)
				const toast = useToast()
				toast.add({
					title: 'Failed to setup flow - ' + flow.display_name,
					description: e.message,
					timeout: 5000,
				})
			})
		},

		async updateFlow(flow: Flow) {
			const { $apiFetch } = useNuxtApp()
			return await $apiFetch(`/flows/flow-update?name=${flow.name}`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
			}).then(() => {
				this.installing.push({
					flow_name: flow.name,
					progress: 0,
				})
				this.startFlowInstallingPolling(flow.name)
			}).catch((e) => {
				console.debug(e)
				const toast = useToast()
				toast.add({
					title: 'Failed to update flow - ' + flow.display_name,
					description: e.message,
					timeout: 5000,
				})
			})
		},

		async cancelFlowSetup(flow: Flow) {
			const { $apiFetch } = useNuxtApp()
			return await $apiFetch(`/flows/install-progress?name=${flow.name}`, {
				method: 'DELETE',
			}).then(() => {
				this.installing = this.installing.filter(f => f.flow_name !== flow.name)
				if (this.installing.length === 0 && this.running.length === 0) {
					this.showNotificationChip = false
				}
			})
		},

		async getFlowsInstallProgress() {
			const { $apiFetch } = useNuxtApp()
			return await $apiFetch('/flows/install-progress', {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
				},
			})
		},

		async uploadFlow(flow: File) {
			const { $apiFetch } = useNuxtApp()
			const formData = new FormData()
			formData.append('flow_file', flow)
			return await $apiFetch('/flows/flow', {
				method: 'PUT',
				body: formData,
			}).then((res: any) => {
				if (res && res.details === '') {
					this.fetchFlows()
				}
				return res
			})
		},

		async deleteFlow(flow: Flow) {
			const { $apiFetch } = useNuxtApp()
			const response = await $apiFetch(`/flows/flow?name=${flow.name}`, {
				method: 'DELETE',
				headers: {
					'Content-Type': 'application/json',
				},
			}).then(() => {
				this.fetchFlows()
			})
			return response
		},

		async runFlow(flow: Flow, input_params: FlowInputParam[]|any[], count: number = 1, child_task: boolean = false) {
			const formData = new FormData()

			console.debug('input_params:', input_params)

			const input_params_mapped: any = {}
			input_params.forEach(param => {
				const paramName = Object.keys(param)[0]
				if (param[paramName].type !== 'image' && param[paramName].value !== '')
					input_params_mapped[paramName] = param[paramName].value
			})
			console.debug('input_params_mapped:', input_params_mapped)

			formData.append('name', flow.name)
			formData.append('count', count.toString())
			formData.append('input_params', JSON.stringify(input_params_mapped))


			const file_input_params = input_params.filter(param => {
				const paramName = Object.keys(param)[0]
				return param[paramName].type === 'image'
					&& (param[paramName].value instanceof File || typeof param[paramName].value === 'string')
			})
			console.debug('file_input_params:', file_input_params)
			if (file_input_params.length > 0) {
				file_input_params.forEach(param => {
					const paramName = Object.keys(param)[0]
					console.debug('file:', param[paramName].value)
					formData.append('files', param[paramName].value)
				})
			}

			if (child_task) {
				formData.append('child_task', '1')
			}

			console.debug('form_data:', formData)

			const { $apiFetch } = useNuxtApp()
			const input_params_mapped_updated: any = {}
			Object.keys(input_params_mapped).forEach((key) => {
				input_params_mapped_updated[key] = {
					value: input_params_mapped[key],
					display_name: flow.input_params.find(param => param.name === key)?.display_name,
				}
			})
			return await $apiFetch('/tasks/create', {
				method: 'POST',
				headers: {
					'Access-Control-Allow-Origin': '*',
				},
				body: formData,
			}).then((res: any) => {
				// Adding started flow to running list
				res.tasks_ids.forEach((task_id: number, index: number) => {
					this.running.push({
						task_id: task_id.toString(),
						flow_name: flow.name,
						progress: 0,
						input_params_mapped: {
							...input_params_mapped_updated,
							seed: {
								value: Number(input_params_mapped['seed']) + index,
								display_name: 'Seed',
							},
						},
						outputs: [], // outputs are dynamic and populated later by polling task progress
					})
				})
				console.debug('running:', this.running)
				this.startFlowProgressPolling(flow.name)
			}).catch((e) => {
				console.debug(e)
				const toast = useToast()
				toast.add({
					title: 'Failed to run flow - ' + flow.display_name,
					description: e.message,
					timeout: 5000,
				})
			})
		},

		async fetchSubFlows(input_type: string) {
			if (this.sub_flows.length > 0) {
				return
			}
			const { $apiFetch } = useNuxtApp()
			return $apiFetch(`/flows/subflows?input_type=${input_type}`).then((res) => {
				this.sub_flows = <Flow[]>res
			})
		},

		async restartFlow(running: FlowRunning) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch(`/tasks/restart?task_id=${running.task_id}`, {
				method: 'POST',
			}).then((res: any) => {
				if (res && res.details !== '') {
					const toast = useToast()
					toast.add({
						title: 'Failed to restart flow',
						description: res.details,
						timeout: 5000,
					})
					return
				}
				const runningFlow = this.running.find(flow => flow.task_id === running.task_id)
				if (!runningFlow) {
					return
				}
				runningFlow.error = ''
				runningFlow.progress = 0
				this.startFlowProgressPolling(running.flow_name)
			})
		},

		async deleteFlowResults(flow_name: string) {
			const { $apiFetch } = useNuxtApp()
			return await $apiFetch(`/tasks/clear?name=${flow_name}`, {
				method: 'DELETE',
			}).then((res: any) => {
				if (res && res?.details !== '') {
					const toast = useToast()
					toast.add({
						title: 'Failed to delete flow results',
						description: res.details,
						timeout: 5000,
					})
					return
				}
				this.flow_results = this.flow_results.filter(flow => flow.flow_name !== flow_name)
			})
		},

		async cancelRunningFlows(flow_name: string) {
			const { $apiFetch } = useNuxtApp()
			return await $apiFetch(`/tasks/queue?name=${flow_name}`, {
				method: 'DELETE',
			}).then((res: any) => {
				if (res && res.details !== '') {
					const toast = useToast()
					toast.add({
						title: `Failed to cancel ${flow_name} running flows`,
						description: res.details,
						timeout: 5000,
					})
					return
				}
			}).finally(() => {
				this.running = this.running.filter(flow => flow.flow_name !== flow_name)
				if (this.running.length === 0) {
					this.showNotificationChip = false
				}
			})
		},

		async cancelRunningFlow(running: FlowRunning) {
			const { $apiFetch } = useNuxtApp()
			return await $apiFetch(`/tasks/queue/${running.task_id}`, {
				method: 'DELETE',
				headers: {
					'Content-Type': 'application/json',
				},
			}).then((res: any) => {
				if (res && res.details !== '') {
					const toast = useToast()
					toast.add({
						title: 'Failed to cancel running flow',
						description: res.details,
						timeout: 5000,
					})
					return
				}
				this.running = this.running.filter(flow => flow.task_id !== running.task_id)
				if (this.running.length === 0) {
					this.showNotificationChip = false
				}
			})
		},

		async getFlowsProgress(flow_name?: string): Promise<TasksHistory> {
			const { $apiFetch } = useNuxtApp()
			const url = flow_name ? `/tasks/progress-summary?name=${flow_name}` : '/tasks/progress'
			return await $apiFetch(url, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
				},
			})
		},

		async fetchFlowComfy(task_id: string) {
			const { $apiFetch } = useNuxtApp()
			return await $apiFetch(`/tasks/progress/${task_id}`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
				},
			})
		},

		setCurrentFlow(name: string) {
			this.current_flow = <Flow>this.flowByName(name)
			if (this.current_flow) {
				useHead({
					title: `${this.current_flow.display_name} - Workflows - Visionatrix`,
					meta: [
						{
							name: 'description',
							content: 'Workflows - Visionatrix',
						},
					],
				})
			} else {
				const installingFlow = this.installing.find(flow => flow.flow_name === name)
				if (installingFlow) {
					this.current_flow = <Flow>installingFlow?.flow
				}
			}
			this.loading.current_flow = false
		},

		async restorePollingProcesses() {
			// Restore installing flow polling
			await this.getFlowsInstallProgress().then((progress: any) => {
				progress.forEach((installing_progress: FlowInstallingProgress) => {
					if (installing_progress.progress < 100) {
						this.installing.push({
							flow_name: installing_progress.name,
							progress: installing_progress.progress,
							flow: installing_progress?.flow || null,
						})
						this.startFlowInstallingPolling(installing_progress.name)
					}
				})
			})
			Array.from(new Set(this.running.map(flow => flow.flow_name))).forEach(flow_name => {
				this.startFlowProgressPolling(flow_name)
			})
		},

		startFlowInstallingPolling(flow_name: string) {
			if (this.installing.length === 0) {
				return
			}
			let failedAttempts = 0
			this.showNotificationChip = true
			const interval = setInterval(async () => {
				await this.getFlowsInstallProgress().then((progress: any) => {
					if (failedAttempts > 3) {
						clearInterval(interval)
						return
					}

					const flowInstalling = this.flowInstallingByName(flow_name)
					const newProgress = progress.find((p: any) => p.name === flow_name)
					if (!flowInstalling || !newProgress) {
						clearInterval(interval)
						failedAttempts++
						return
					}
					flowInstalling.progress = <number> newProgress.progress
					if (newProgress.error) {
						clearInterval(interval)
						flowInstalling.error = newProgress.error
						const toast = useToast()
						toast.add({
							title: 'Failed to install flow - ' + flow_name,
							description: newProgress.error,
							timeout: 8000,
						})
					}
					if (newProgress.progress === 100) {
						clearInterval(interval)
						// Remove finished flow from installing list
						this.installing = this.installing.filter(flow => flow.flow_name !== flow_name)
						this.fetchFlows()
					}
				}).catch((e) => {
					console.debug(e)
					failedAttempts++
				})
			}, 3000)
		},

		startFlowProgressPolling(flow_name: string) {
			this.showNotificationChip = true
			if (flow_name in this.runningInterval
				&& this.runningInterval[flow_name] !== null
				&& this.running.some(flow => flow.flow_name === flow_name)
			) {
				// Polling already running for this flow
				return
			}
			this.runningInterval[flow_name] = setInterval(async () => {
				await this.getFlowsProgress(flow_name).then((progress: TasksHistory[]|any) => {
					Object.keys(progress).forEach((task_id: string) => {
						const runningFlow = this.running.find(flow => Number(flow.task_id) === Number(task_id))
						if (!runningFlow) {
							return
						}
						runningFlow.progress = <number>progress[task_id].progress
						if (progress[task_id].error && progress[task_id].error !== '') {
							runningFlow.error = progress[task_id].error
							return
						}
						if (progress[task_id].execution_time) {
							runningFlow.execution_time = progress[task_id].execution_time
						}
						// update input_params_mapped with new values
						Object.keys(progress[task_id].input_params).forEach((key) => {
							runningFlow.input_params_mapped[key].value = progress[task_id].input_params[key]
						})
						// update input_files
						if (progress[task_id].input_files) {
							runningFlow.input_files = progress[task_id].input_files
						}
						if (progress[task_id].progress === 100) {
							// Remove finished flow from running list
							this.running = this.running.filter(flow => Number(flow.task_id) !== Number(task_id))
							if (this.running.filter(flow => flow.flow_name === flow_name).length === 0) {
								this.showNotificationChip = false
								clearInterval(this.runningInterval[flow_name])
								this.runningInterval[flow_name] = null
							}
							// Save flow results history
							const flow = <Flow>this.flowByName(runningFlow.flow_name)
							const flowResult = <FlowResult>{
								task_id: task_id.toString(),
								flow_name: flow.name,
								outputs: progress[task_id].outputs,
								input_params_mapped: runningFlow.input_params_mapped,
								execution_time: progress[task_id]?.execution_time || 0,
								child_tasks: progress[task_id].child_tasks || [],
								parent_task_id: progress[task_id].parent_task_id,
								progress: progress[task_id].progress,
							}
							this.flow_results.push(flowResult)
						}

						if (progress[task_id].parent_task_id) {
							this.updateChildTasksTillRootParent(progress[task_id].parent_task_id, progress[task_id])
						}
					})
				}).catch((e): any => {
					console.debug('Failed to fetch running flow progress: ', e)
					clearInterval(this.runningInterval[flow_name])
					this.runningInterval[flow_name] = null
				})
			}, 3000)
		},

		updateChildTasksTillRootParent(parentTaskId: number|null, task: TaskHistoryItem|FlowResult|any) {
			if (parentTaskId === null) {
				return
			}
			const parentTask = this.flow_results.find(flowResult => Number(flowResult.task_id) === Number(parentTaskId))
			if (parentTask) {
				parentTask.child_tasks = [task]
				this.updateChildTasksTillRootParent(parentTask.parent_task_id, parentTask)
			}
		},

		deleteFlowHistory(task_id: string) {
			const { $apiFetch } = useNuxtApp()
			return $apiFetch(`/tasks/task?task_id=${task_id}`, {
				method: 'DELETE',
				headers: {
					'Content-Type': 'application/json',
				},
			}).then((res: any) => {
				if (res && res?.details !== '') {
					const toast = useToast()
					toast.add({
						title: 'Failed to delete flow history item',
						description: res.details,
						timeout: 5000,
					})
					return
				}
				this.flow_results = this.flow_results.filter(flow => flow.task_id !== task_id)
			})
		},

		loadFavorites() {
			const favorite_flows = localStorage.getItem('favorite_flows')
			if (favorite_flows) {
				this.flows_favorite = JSON.parse(favorite_flows).filter((fav: string) => {
					return this.flows_installed.find(flow => flow.name === fav)
				})
				// If there are were filtered out flows that are not installed anymore - update local storage
				if (this.flows_favorite.length !== JSON.parse(favorite_flows).length) {
					localStorage.setItem('favorite_flows', JSON.stringify(this.flows_favorite))
				}
				this.flows_installed.sort(this.sortByFavoriteCallback)
			}
		},

		markFlowFavorite(flow: Flow) {
			const favorite = this.flows_favorite.find(fav => fav === flow.name)
			if (favorite) {
				this.flows_favorite = this.flows_favorite.filter(fav => fav !== flow.name)
				this.flows_installed.sort(this.sortByFlowNameCallback)
			} else {
				this.flows_favorite.push(flow.name)
				this.flows_installed.sort(this.sortByFavoriteCallback)
			}
			localStorage.setItem('favorite_flows', JSON.stringify(this.flows_favorite))
		},

		sortByFlowNameCallback(a: Flow, b: Flow) {
			if (a.name.split(' ')[0].toLowerCase() > b.name.split(' ')[0].toLowerCase()) {
				return -1
			} else if (a.name.split(' ')[0].toLowerCase() < b.name.split(' ')[0].toLowerCase()) {
				return 1
			} else {
				return 0
			}
		},

		sortByFavoriteCallback(a: Flow, b: Flow) {
			const favoriteA = this.flows_favorite.find(fav => fav === a.name)
			const favoriteB = this.flows_favorite.find(fav => fav === b.name)
			if (favoriteA && !favoriteB) {
				return -1
			} else if (!favoriteA && favoriteB) {
				return 1
			} else {
				return 0
			}
		},

		loadUserOptions() {
			const user_options = localStorage.getItem('user_options')
			if (user_options) {
				const options = JSON.parse(user_options)
				this.resultsPageSize = Number(options.resultsPageSize)
			}
		},

		saveUserOptions() {
			localStorage.setItem('user_options', JSON.stringify({
				resultsPageSize: this.resultsPageSize,
			}))
		},

		downloadFlowComfy(flow_name: string, task_id: string) {
			this.fetchFlowComfy(task_id).then((res: any) => {
				console.debug('downloadFlowComfy', res.flow_comfy)
				const blob = new Blob([JSON.stringify(res.flow_comfy, null, 2)], { type: 'application/json' })
				const url = window.URL.createObjectURL(blob)
				const a = document.createElement('a')
				a.href = url
				a.download = `${flow_name}_comfy_flow_${task_id}.json`
				a.click()
				window.URL.revokeObjectURL(url)
			})
		},
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useFlowsStore, import.meta.hot))
}


export interface Flow {
	id: string
	name: string
	display_name: string
	description: string
	author: string
	homepage: string
	license: string
	documentation: string
	models: Model[]
	input_params: FlowInputParam[]
	tags: string[]
	version: string
	private: boolean
	requires: string[]
	new_version_available?: string
	is_seed_supported: boolean
	is_count_supported: boolean
}

export interface Model {
	name: string
	save_path: string
	url: string
	license: string
	homepage: string
	hash: string
	gated: boolean
}

export interface FlowInputParam {
	id: any
	name: string
	display_name: string
	type: string
	optional: boolean
	options?: any[]
	advanced?: boolean
	default?: any
	min?: number
	max?: number
	step?: number
	source_input_name?: string
}

export interface FlowOutputParam {
	type: string
	comfy_node_id: number
}

export interface FlowInstalling {
	flow_name: string
	progress: number
	error?: string
	flow?: Flow
}

export interface FlowInstallingProgress {
	name: string
	flow: Flow,
	flow_comfy: any
	progress: number
	error: string
	started_at: string
	updated_at: string
	finished_at: string
}

export interface FlowRunning {
	task_id: string
	flow_name: string
	progress: number
	input_files?: TaskInputFile
	input_params_mapped: TaskHistoryInputParam
	outputs: FlowOutputParam[]
	error?: string
	execution_time?: number
	parent_task_id?: number
	child_tasks?: TaskHistoryItem[]
}

export interface FlowProgress {
	task_id: string
	progress: number
	error?: string
	flow?: any
	name: string
	flow_comfy?: any
	outputs: FlowOutputParam[]
	parent_task_id?: number
	execution_time?: number
}

export interface FlowResult {
	task_id: string
	flow_name: string
	outputs: FlowOutputParam[]
	input_params_mapped: TaskHistoryInputParam
	execution_time: number
	parent_task_id: number
	child_tasks: TaskHistoryItem[]
	progress: number
}

export interface TasksHistory {
	[task_id: string]: TaskHistoryItem
}

export interface TaskInputFile {
	[index: number]: TaskInputFileData
}

export interface TaskInputFileData {
	file_name: string
	file_size: string
}

export interface TaskHistoryInputParam {
	[name: string]: any
}

export interface TaskHistoryItem {
	child_tasks: TaskHistoryItem[]
	created_at: string
	error?: string
	execution_time: number
	finished_at: string
	flow_comfy: any
	input_files: TaskInputFile
	input_params: TaskHistoryInputParam
	locked_at: string
	name: string
	outputs: FlowOutputParam[]
	parent_task_id: number
	parent_task_node_id: number
	progress: number
	task_id: number
	updated_at: string
	user_id: string
	worker_id: string
}
