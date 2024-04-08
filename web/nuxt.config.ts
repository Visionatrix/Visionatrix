// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
	devtools: { enabled: true },
	modules: ['@nuxt/ui', '@pinia/nuxt', '@nuxt/image'],
	runtimeConfig: {
		app: {
			backendApiUrl: process.env.BACKEND_API_URL || '',
		}
	},
	app: {
		pageTransition: { name: 'page', mode: 'out-in' },
	},
	ssr: false, // we use only client side rendering,
})
