import type { UseFetchOptions } from 'nuxt/app'

export function useApiFetch<T>(
	url: string | (() => string),
	options: UseFetchOptions<T> = {}
) {
	return useFetch(url, {
		...options,
		$fetch: useNuxtApp().$apiFetch,
	})
}
