export function buildBackendUrl() {
	const config = useRuntimeConfig()
	let prefix = null
	if (config.app.baseURL !== '/') {
		prefix = config.app.baseURL
	}
	return config.app.backendApiUrl !== ''
		? config.app.backendApiUrl
		: location.port 
			? `${location.protocol}//${location.hostname}:${location.port}`
			: `${location.protocol}//${location.hostname}` + (prefix ? prefix : '')
}

export function buildBackendApiUrl() {
	return buildBackendUrl() + '/api'
}

export function buildAuthorization() {
	const config = useRuntimeConfig()
	return 'Basic ' + btoa(`${config.app.authUser}:${config.app.authPassword}`)
}

export function outputResultSrc(result: any) {
	return `${buildBackendApiUrl()}/tasks/results?task_id=${result.task_id}&node_id=${result.node_id}`
}
