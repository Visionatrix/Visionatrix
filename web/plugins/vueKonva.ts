import VueKonva from 'vue-konva'

export default defineNuxtPlugin({
	setup(nuxtApp) {
		nuxtApp.vueApp.use(VueKonva)
	}
})
