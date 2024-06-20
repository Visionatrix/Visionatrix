// edit attention like in ComfyUI for Textarea inputs
// ref: https://github.com/comfyanonymous/ComfyUI/blob/master/web/extensions/core/editAttention.js

// TODO: extract into settings
const editAttentionDelta = '0.05'

function incrementWeight(weight: string, delta: number) {
	const floatWeight = parseFloat(weight)
	if (isNaN(floatWeight)) return weight
	const newWeight = floatWeight + delta
	if (newWeight < 0) return '0'
	return String(Number(newWeight.toFixed(10)))
}

function findNearestEnclosure(text: string, cursorPos: number) {
	let start = cursorPos, end = cursorPos
	let openCount = 0, closeCount = 0

	// Find opening parenthesis before cursor
	while (start >= 0) {
		start--
		if (text[start] === '(' && openCount === closeCount) break
		if (text[start] === '(') openCount++
		if (text[start] === ')') closeCount++
	}
	if (start < 0) return false

	openCount = 0
	closeCount = 0

	// Find closing parenthesis after cursor
	while (end < text.length) {
		if (text[end] === ')' && openCount === closeCount) break
		if (text[end] === '(') openCount++
		if (text[end] === ')') closeCount++
		end++
	}
	if (end === text.length) return false

	return { start: start + 1, end: end }
}

function addWeightToParentheses(text: string) {
	const parenRegex = /^\((.*)\)$/
	const parenMatch = text.match(parenRegex)

	const floatRegex = /:([+-]?(\d*\.)?\d+([eE][+-]?\d+)?)/
	const floatMatch = text.match(floatRegex)

	if (parenMatch && !floatMatch) {
		return `(${parenMatch[1]}:1.0)`
	} else {
		return text
	}
}

export function editAttention(event: any) {
	const inputField = event.composedPath()[0]
	const delta = parseFloat(editAttentionDelta)

	if (inputField.tagName !== 'TEXTAREA') return
	if (!(event.key === 'ArrowUp' || event.key === 'ArrowDown')) return
	if (!event.ctrlKey && !event.metaKey) return

	event.preventDefault()


	let start = inputField.selectionStart
	let end = inputField.selectionEnd
	let selectedText = inputField.value.substring(start, end)

	// If there is no selection, attempt to find the nearest enclosure, or select the current word
	if (!selectedText) {
		const nearestEnclosure = findNearestEnclosure(inputField.value, start)
		if (nearestEnclosure) {
			start = nearestEnclosure.start
			end = nearestEnclosure.end
			selectedText = inputField.value.substring(start, end)
		} else {
			// Select the current word, find the start and end of the word
			const delimiters = ' .,\\/!?%^*;:{}=-_`~()\r\n\t'
			
			while (!delimiters.includes(inputField.value[start - 1]) && start > 0) {
				start--
			}
			
			while (!delimiters.includes(inputField.value[end]) && end < inputField.value.length) {
				end++
			}

			selectedText = inputField.value.substring(start, end)
			if (!selectedText) return
		}
	}

	// If the selection ends with a space, remove it
	if (selectedText[selectedText.length - 1] === ' ') {
		selectedText = selectedText.substring(0, selectedText.length - 1)
		end -= 1
	}

	// If there are parentheses left and right of the selection, select them
	if (inputField.value[start - 1] === '(' && inputField.value[end] === ')') {
		start -= 1
		end += 1
		selectedText = inputField.value.substring(start, end)
	}

	// If the selection is not enclosed in parentheses, add them
	if (selectedText[0] !== '(' || selectedText[selectedText.length - 1] !== ')') {
		selectedText = `(${selectedText})`
	}

	// If the selection does not have a weight, add a weight of 1.0
	selectedText = addWeightToParentheses(selectedText)

	// Increment the weight
	const weightDelta = event.key === 'ArrowUp' ? delta : -delta
	const updatedText = selectedText.replace(/\((.*):(\d+(?:\.\d+)?)\)/, (match: any, text: string, weight: string) => {
		weight = incrementWeight(weight, weightDelta)
		if (Number(weight) == 1) {
			return text
		} else {
			return `(${text}:${weight})`
		}
	})

	inputField.setRangeText(updatedText, start, end, 'select')
	return inputField.value
}