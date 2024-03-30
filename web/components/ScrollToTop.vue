<script setup lang="ts">
const props = defineProps({
	show: {
		type: Boolean,
		required: true,
	},
	target: {
		type: String,
		required: true,
	},
})

function scrollToTop() {
	const target = document.getElementById(props.target)
	if (target) {
		target.scrollIntoView({ behavior: 'smooth' })
	}
}
</script>

<template>
	<UButton v-show="show"
		icon="i-heroicons-arrow-small-up"
		color="black"
		variant="outline"
		@click="scrollToTop"/>
</template>