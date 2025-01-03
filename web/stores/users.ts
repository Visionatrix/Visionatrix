export const useUserStore = defineStore('userStore', {
	state: () => ({
		loading: false,
		user: <UserInfo>{},
	}),

	getters: {
		isAdmin(): boolean {
			return this.user.is_admin || false
		},
		isLoaded(): boolean {
			return !!this.user.user_id
		},
	},

	actions: {
		async fetchUserInfo() {
			if (this.isLoaded) {
				return
			}
			const { $apiFetch } = useNuxtApp()
			this.loading = true
			return await $apiFetch('/other/whoami')
				.then((res: any) => {
					this.user = <UserInfo>res
				}).finally(() => {
					this.loading = false
				})
		},
	},
})

export interface UserInfo {
	user_id: string
	full_name: string
	email: string
	is_admin: boolean
}
