export function paginate(items: any[], page: number, items_per_page: number): any[] {
	const paginated = []
	const pages = Math.ceil(items.length / items_per_page)
	for (let i = 0; i < pages; i++) {
		paginated.push(items.slice(i * items_per_page, (i + 1) * items_per_page))
	}
	return paginated[page - 1]
}
