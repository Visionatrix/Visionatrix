<script setup lang="ts">
const links = [
	{
		label: 'Settings',
		icon: 'i-heroicons-cog-6-tooth-20-solid',
		to: '/settings',
	},
	{
		label: 'Workers information',
		icon: 'i-heroicons-chart-bar-16-solid',
		to: '/settings/workers',
	},
]
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<div class="flex flex-col md:flex-row">
			<UVerticalNavigation :links="links" />
			<div class="content px-5">
				<h2 class="my-3 text-xl">Settings</h2>
				<p class="text-slate-500">TODO</p>
			</div>
		</div>
	</AppContainer>
</template>