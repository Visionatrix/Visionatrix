<script lang="ts" setup>
const props = defineProps({
	flow: {
		type: Object as () => Flow,
		required: true,
	}
})
const flowsStore = useFlowsStore()
const installed = ref(flowsStore.flows_installed.filter((f) => f.name === props?.flow?.name).length === 1)
</script>

<template>
	<div class="p-4 w-full md:w-6/12 lg:w-4/12">
		<UCard as="div" class="hover:shadow-md">
			<template #header>
				<div class="flex flex-grow justify-between">
					<h2 class="text-xl font-bold text-ellipsis" :title="flow?.display_name">{{ flow?.display_name }}</h2>
					<UTooltip v-if="flowsStore.isFlowInstalled(flow?.name)"
						text="Mark flow as favorite" :popper="{ placement: 'top' }" :open-delay="500">
						<UButton :icon="!flowsStore.isFlowFavorite(flow.name) ? 'i-heroicons-star' : 'i-heroicons-star-16-solid'"
							variant="outline"
							color="yellow"
							@click="flowsStore.markFlowFavorite(flow)" />
					</UTooltip>
				</div>
			</template>

			<div class="flex flex-col items-between">
				<p class="text-md text-slate-400 truncate text-ellipsis mb-2" :title="flow?.description">
					{{ flow?.description }}
				</p>
				<p class="flex flex-row flex-wrap items-center text-md mb-2">
					<span class="flex flex-row items-center">
						<UIcon name="i-heroicons-user-16-solid" class="mr-1" />
						<b>Author:</b>&nbsp;
					</span>
					<a class="hover:underline flex flex-row items-center" :href="flow?.homepage" rel="noopener" target="_blank">
						{{ flow?.author }}
					</a>
				</p>
				<p class="flex flex-row items-center text-md mb-2">
					<UIcon name="i-heroicons-document-text" class="mr-1" />
					<a v-if="flow?.documentation" class="hover:underline" :href="flow?.documentation" rel="noopener" target="_blank">Documentation</a>
					<span v-else>No documentation</span>
				</p>
				<p class="flex flex-row items-center text-md mb-2">
					<UIcon name="i-heroicons-arrow-down-on-square-stack" class="mr-1" />
					<b>Models:</b>&nbsp; {{ flow?.models?.length }}
				</p>
				<p class="flex flex-row items-center text-md">
					<b>Installed:</b>&nbsp;
					<UIcon :name="installed ? 'i-heroicons-check-badge' : 'i-heroicons-x-mark'" class="mx-1" />
					<span :class="{
						'text-green-500': installed,
						'text-red-500': !installed,
					}">
						{{ installed ? 'Yes' : 'No' }}
					</span>
				</p>
			</div>

			<template #footer>
				<UButton :to="`/workflows/${flow?.name}`"
					:icon="'i-heroicons-arrow-up-right-16-solid'"
					class="flex justify-center dark:bg-slate-500 bg-slate-500 dark:hover:bg-slate-700 hover:bg-slate-700 dark:text-white">
					Open
				</UButton>
			</template>
		</UCard>
	</div>
</template>
