// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
	devtools: { enabled: true },
	modules: ['@nuxt/ui', '@pinia/nuxt', '@nuxt/image'],
	runtimeConfig: {
		app: {
			backendApiUrl: process.env.BACKEND_API_URL || '',
			authUser: process.env.AUTH_USER || '',
			authPassword: process.env.AUTH_PASSWORD || '',
		}
	},
	ssr: false, // we use only client side rendering,
})
