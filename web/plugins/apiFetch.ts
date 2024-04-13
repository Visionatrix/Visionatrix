export default defineNuxtPlugin(() => {
	const config = useRuntimeConfig()

	const $apiFetch = $fetch.create({
		baseURL: buildBackendApiUrl(),
		onRequest({ options }) {
			if (config.app.authUser && config.app.authPassword) {
				// Add Basic Authorization header
				options.headers = options.headers || {}
				options.headers.Authorization = buildAuthorization()
			}
		},
	})

	// Expose to useNuxtApp().$apiFetch
	return {
		provide: {
			apiFetch: $apiFetch
		}
	}
})
