import { ImgComparisonSlider } from '@img-comparison-slider/vue'

export default defineNuxtPlugin({
	setup(nuxtApp) {
		nuxtApp.vueApp.component('ImgComparisonSlider', ImgComparisonSlider)
	}
})
