export default defineNuxtRouteMiddleware((to, from) => {
	const config = useRuntimeConfig()
	if (config.app.isNextcloudIntegration) {
		const nextcloudStore = useNextcloudStore()
		nextcloudStore.handleRouteChange(to, from)
	}
})
