export function buildBackendApiUrl() {
	const config = useRuntimeConfig()
	let prefix = null
	if (config.app.baseURL !== '/') {
		prefix = config.app.baseURL
	}
	return config.app.backendApiUrl !== ''
		? config.app.backendApiUrl + '/api'
		: location.port 
			? `${location.protocol}//${location.hostname}:${location.port}/api`
			: `${location.protocol}//${location.hostname}` + (prefix ? prefix : '') + '/api'
}

export function buildAuthorization() {
	const config = useRuntimeConfig()
	return 'Basic ' + btoa(`${config.app.authUser}:${config.app.authPassword}`)
}
