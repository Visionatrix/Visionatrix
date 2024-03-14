import type { Task } from "vitest"

export const useFlowsStore = defineStore('flowsStore', {
	state: () => ({
		loading: {
			flows_available: false,
			flows_installed: false,
			tasks_history: false,
			current_flow: true,
		},
		page: 1,
		pageSize: 6,
		running: <FlowRunning[]>[],
		installing: <FlowInstalling[]>[],
		resultsPage: 1,
		resultsPageSize: 5,
		flow_results_filter: '',
		flow_results: <FlowResult[]>[],
		flows_available: <Flow[]>[],
		flows_installed: <Flow[]>[],
		current_flow: <Flow>{},
		showNotificationChip: false,
	}),
	getters: {
		flows(state): Flow[] {
			return [
				...state.flows_available,
				...state.flows_installed,
			]
		},
		paginatedFlows(state) {
			const start = (state.page - 1) * state.pageSize
			const end = start + state.pageSize
			return [
				...state.flows_available,
				...state.flows_installed,
			].slice(start, end)
		},
		flowByName() {
			return (name: string) => this.flows.find(flow => flow.name === name)
		},
		flowResultsByName(state) {
			return (name: string) => {
				if (state.flow_results_filter !== '') {
					return state.flow_results.filter(flow => flow.flow_name === name && flow.prompt.includes(state.flow_results_filter))
				}
				return state.flow_results.filter(flow => flow.flow_name === name)
			}
		},
		flowResultsByNamePaginated(state) {
			return (name: string) => {
				const start = (state.resultsPage - 1) * state.resultsPageSize
				const end = start + state.resultsPageSize
				if (state.flow_results_filter !== '') {
					return state.flow_results.filter(flow => flow.flow_name === name && flow.prompt.includes(state.flow_results_filter)).reverse().slice(start, end)
				}
				return state.flow_results.filter(flow => flow.flow_name === name).reverse().slice(start, end)
			}
		},
		flowInstallingByName(state) {
			return (name: string) => state.installing.find(flow => flow.flow_name === name) ?? null
		},
		flowsRunningByName(state) {
			return (name: string) => state.running.filter(flow => flow.flow_name === name) ?? null
		},
		currentFlow(state): Flow {
			return state.current_flow
		},
		isFlowRunning(state) {
			return (flow_name: string) => state.running.find(flow => flow.flow_name === flow_name)
		},
		isFlowInstalled(state) {
			return (name: string) => state.flows_installed.filter(flow => flow.name === name).length > 0
		},
	},
	actions: {
		async fetchFlows() {
			await Promise.all([
				this.fetchFlowsAvailable(),
				this.fetchFlowsInstalled(),
			])
			.then(() => {
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
			const config = useRuntimeConfig()
			console.debug('fetching flows: ' + config.app.backendApiUrl + '/flows-available')
			this.loading.flows_available = true
			const flows = await $fetch(`${config.app.backendApiUrl}/flows-available`, {
				method: 'GET',
				timeout: 15000,
			}).then((res) => {
				console.debug('available_flows: ', res)
				this.loading.flows_available = false
				this.flows_available = <Flow[]>res
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
			const config = useRuntimeConfig()
			console.debug('fetching installed flows')
			this.loading.flows_installed = true
			const flows = await $fetch(`${config.app.backendApiUrl}/flows-installed`, {
				method: 'GET',
				timeout: 15000,
			}).then((res) => {
				console.debug('installed_flows: ', res)
				this.loading.flows_installed = false
				this.flows_installed = <Flow[]>res
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
			const config = useRuntimeConfig()
			this.loading.tasks_history = true
			return await $fetch(`${config.app.backendApiUrl}/tasks-progress`, {
				method: 'GET',
			}).then((res) => {
				this.loading.tasks_history = false
				return <TasksHistory>res
			})
		},

		initFlowResultsData(res: TasksHistory) {
			console.debug('tasks_history:', res)
			// Load running flows from tasks history
			const runningFlows = <FlowRunning[]>Object.keys(res).filter(task_id => {
				const task = <TaskHistoryItem>res[task_id]
				return task.progress < 100
			}).map(task_id => {
				const task = <TaskHistoryItem>res[task_id]
				return <FlowRunning>{
					client_id: task.prompt_id,
					task_id: task_id,
					flow_name: task.name,
					progress: task.progress,
					input_prompt: <string>task.input_params?.prompt || '',
					seed: <string>task.input_params?.seed || ''
				}
			})
			if (runningFlows && runningFlows.length > 0) {
				console.debug('loading running flows:', runningFlows)
				this.running = <FlowRunning[]>runningFlows ?? []
			}

			// Load finished flows results from tasks history
			const finishedFlows = <FlowResult[]>Object.keys(res).filter(task_id => {
				const task = <TaskHistoryItem>res[task_id]
				return task.progress === 100
			}).map(task_id => {
				const task = <TaskHistoryItem>res[task_id]
				const flow = <Flow>this.flowByName(task.name)
				return <FlowResult>{
					task_id: task_id,
					flow_name: task.name,
					output_params: flow.output_params,
					prompt: task.input_params?.prompt || '',
					input_params_mapped: task.input_params || null,
				}
			})
			console.debug('loading finished flows:', finishedFlows)
			this.flow_results = <FlowResult[]>finishedFlows
		},

		async setupFlow(flow: Flow) {
			const config = useRuntimeConfig()
			return await $fetch(`${config.app.backendApiUrl}/flow?name=${flow.name}`, {
				method: 'PUT',
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

		async getFlowsInstallProgress() {
			const config = useRuntimeConfig()
			return await $fetch(`${config.app.backendApiUrl}/flow-progress-install`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
				},
			})
		},

		async deleteFlow(flow: Flow) {
			const config = useRuntimeConfig()
			const response = await $fetch(`${config.app.backendApiUrl}/flow?name=${flow.name}`, {
				method: 'DELETE',
				headers: {
					'Content-Type': 'application/json',
				},
			}).then((res) => {
				console.debug(res)
				this.fetchFlows()
			})
			return response
		},

		async runFlow(flow: Flow, input_params: FlowInputParam[]|any[]) {
			console.debug('running flow:', JSON.stringify(input_params[0]['prompt']))
			console.debug('seed:', JSON.stringify(input_params.filter(param => param['seed'])[0]['seed']))
			console.debug('input_params:', JSON.stringify(input_params.map((param: any) => {
				const paramName = Object.keys(param)[0]
				if (['text', 'list'].includes(param[paramName].type))
					return { [paramName]: param[paramName].value }
			})))

			const config = useRuntimeConfig()
			const formData = new FormData()

			// Map input_params to an object key=input_param_name, value=input_param_value
			const input_params_mapped: any = {}
			input_params.forEach(param => {
				const paramName = Object.keys(param)[0]
				if (param[paramName].type !== 'image')
					input_params_mapped[paramName] = param[paramName].value
			})
			console.debug('input_params_mapped:', input_params_mapped)

			formData.append('name', flow.name)
			formData.append('input_params', JSON.stringify(input_params_mapped))

			console.debug('form_data:', formData)

			const file_input_params = input_params.filter(param => {
				const paramName = Object.keys(param)[0]
				return param[paramName].type === 'image'
			})
			console.debug('file_input_params:', file_input_params)
			if (file_input_params.length > 0) {
				file_input_params.forEach(param => {
					const paramName = Object.keys(param)[0]
					console.debug('file:', param[paramName].value)
					formData.append('files', param[paramName].value)
				})
			}


			return await $fetch(`${config.app.backendApiUrl}/task`, {
				method: 'POST',
				headers: {
					'Access-Control-Allow-Origin': '*',
				},
				body: formData,
			}).then((res: any) => {
				// Adding started flow to running list
				this.running.push({
					client_id: res?.client_id,
					task_id: res?.task_id,
					flow_name: flow.name,
					progress: 0,
					input_prompt: input_params_mapped['prompt'],
					seed: input_params_mapped['seed'] ?? '',
					input_params_mapped: input_params_mapped,
				})
				// Start polling for flow progress changes
				this.startFlowProgressPolling(res?.task_id)
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

		async cancelRunningFlows(flow_name: string) {
			const config = useRuntimeConfig()
			return await $fetch(`${config.app.backendApiUrl}/tasks-queue?name=${flow_name}`, {
				method: 'DELETE',
			}).then((res: any) => {
				if (res.error !== '') {
					const toast = useToast()
					toast.add({
						title: `Failed to cancel ${flow_name} running flows`,
						description: res.error,
						timeout: 5000,
					})
					return
				}
			}).finally(() => {
				this.running = this.running.filter(flow => flow.flow_name !== flow_name)
			})
		},

		async cancelRunningFlow(running: FlowRunning) {
			const config = useRuntimeConfig()
			return await $fetch(`${config.app.backendApiUrl}/task-queue?task_id=${running.task_id}`, {
				method: 'DELETE',
				headers: {
					'Content-Type': 'application/json',
				},
			}).then((res: any) => {
				if (res.error !== '') {
					const toast = useToast()
					toast.add({
						title: 'Failed to cancel running flow',
						description: res.error,
						timeout: 5000,
					})
					return
				}
				this.running = this.running.filter(flow => flow.task_id !== running.task_id)
			})
		},

		async getFlowProgress(task_id: string): Promise<FlowProgress> {
			const config = useRuntimeConfig()
			return await $fetch(`${config.app.backendApiUrl}/task-progress?task_id=${task_id}`, {
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
					title: `${this.current_flow.display_name} - Workflows - AI Media Wizard`,
					meta: [
						{
							name: 'description',
							content: 'Workflows - AI Media Wizard',
						},
					],
				})
			}
			this.loading.current_flow = false
		},

		async restorePollingProcesses() {
			// Restore installing flow polling
			await this.getFlowsInstallProgress().then((progress: any) => {
				Object.keys(progress).forEach(flow_name => {
					if (progress[flow_name].progress < 100) {
						this.installing.push({
							flow_name: flow_name,
							progress: <number> progress[flow_name].progress
						})
						this.startFlowInstallingPolling(flow_name)
					}
				})
			})
			// Restore running flow polling
			this.running.forEach(flow => {
				this.startFlowProgressPolling(flow.task_id)
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
					if (!flowInstalling || !(flow_name in progress)) {
						clearInterval(interval)
						failedAttempts++
						return
					}
					flowInstalling.progress = <number> progress[flow_name].progress
					if (progress[flow_name].error) {
						clearInterval(interval)
						flowInstalling.error = progress[flow_name].error
					}
					if (progress[flow_name].progress === 100) {
						clearInterval(interval)
						// Remove finished flow from installing list
						this.installing = this.installing.filter(flow => flow.flow_name !== flow_name)
						this.fetchFlows()
					}
				}).catch ((e) => {
					console.debug(e)
					failedAttempts++
				})
			}, 3000)
		},

		startFlowProgressPolling(task_id: string) {
			this.showNotificationChip = true
			const interval = setInterval(async () => {
				await this.getFlowProgress(task_id).then((progress) => {
					const runningFlow = this.running.find(flow => flow.task_id === task_id)
					if (!runningFlow) {
						console.debug('flow not found: ', task_id)
						clearInterval(interval)
						return
					}
					runningFlow.progress = <number>progress.progress
					if (progress.progress === 100) {
						clearInterval(interval)
						// Remove finished flow from running list
						this.running = this.running.filter(flow => flow.task_id !== task_id)
						// Save flow results history
						const flow = <Flow>this.flowByName(runningFlow.flow_name)
						this.flow_results.push({
							task_id: task_id,
							flow_name: flow.name,
							output_params: flow.output_params,
							prompt: runningFlow?.input_prompt,
							input_params_mapped: runningFlow.input_params_mapped,
						})
					}
				}).catch(() => {
					clearInterval(interval)
					this.running = this.running.filter(flow => flow.task_id !== task_id)
				})
			}, 3000)
		},

		deleteFlowHistory(task_id: string) {
			const config = useRuntimeConfig()
			$fetch(`${config.app.backendApiUrl}/task?task_id=${task_id}`, {
				method: 'DELETE',
				headers: {
					'Content-Type': 'application/json',
				},
			}).then((res: any) => {
				if (res.error !== '') {
					const toast = useToast()
					toast.add({
						title: 'Failed to delete flow history item',
						description: res.error,
						timeout: 5000,
					})
					return
				}
				this.flow_results = this.flow_results.filter(flow => flow.task_id !== task_id)
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
	comfy_flow: string
	models: Model[]
	input_params: FlowInputParam[]
	output_params: FlowOutputParam[]
	available?: boolean
}

export interface Model {
	name: string
	save_path: string
	url: string
	license: string
	homepage: string
	hash: string
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
}

export interface FlowOutputParam {
	type: string
	comfy_node_id: number
}

export interface FlowInstalling {
	flow_name: string
	progress: number
	error?: string
}

export interface FlowRunning {
	client_id: string
	task_id: string
	flow_name: string
	input_prompt?: any
	progress: number
	seed?: string
	input_params_mapped: TaskHistoryInputParam
}

export interface FlowProgress {
	progress: number
	error?: string
	flow?: any
	comfy_flow?: any
}

export interface FlowResult {
	task_id: string
	flow_name: string
	output_params: FlowOutputParam[]
	prompt?: any
	input_params_mapped: TaskHistoryInputParam
}

export interface TasksHistory {
	[task_id: string]: TaskHistoryItem
}

export interface TaskHistoryInputParam {
	[name: string]: any
}

export interface TaskHistoryItem {
	name: string
	input_params: TaskHistoryInputParam
	progress: number
	error?: string
	prompt_id?: string
}
