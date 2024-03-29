export function buildBackendApiUrl() {
	const config = useRuntimeConfig()
	return config.app.backendApiUrl !== ''
		? config.app.backendApiUrl
		: location.port 
			? `${location.protocol}//${location.hostname}:${location.port}`
			: `${location.protocol}//${location.hostname}`
}
