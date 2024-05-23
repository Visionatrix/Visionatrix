export function buildBackendApiUrl() {
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

export function buildAuthorization() {
	const config = useRuntimeConfig()
	return 'Basic ' + btoa(`${config.app.authUser}:${config.app.authPassword}`)
}
