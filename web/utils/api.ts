export function buildBackendApiUrl() {
	const config = useRuntimeConfig()
	return config.app.backendApiUrl !== ''
		? config.app.backendApiUrl
		: location.port 
			? `${location.protocol}//${location.hostname}:${location.port}`
			: `${location.protocol}//${location.hostname}`
}

export function buildAuthorization() {
	const config = useRuntimeConfig()
	return 'Basic ' + btoa(`${config.app.authUser}:${config.app.authPassword}`)
}
