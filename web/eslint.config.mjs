import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt(
	{
		rules: {
			semi: ['error', 'never'],
			quotes: ['error', 'single'],
			indent: ['error', 'tab'],
			'no-unused-expressions': ['warn', { allowShortCircuit: true }],
			'@typescript-eslint/no-unused-expressions': ['warn', { allowShortCircuit: true }],
			'@typescript-eslint/no-explicit-any': 'off', // TODO: Remove later with fixes in code
			'@typescript-eslint/ban-ts-comment': 'off',
			'@typescript-eslint/no-empty-object-type': 'off',
			'quote-props': ['error', 'as-needed'],
			'vue/multi-word-component-names': 0,
			'vue/max-attributes-per-line': 'off',
			'vue/no-v-html': 0,
			'vue/html-indent': ['error', 'tab'],
			'vue/first-attribute-linebreak': 0,
			'vue/html-closing-bracket-newline': 0,
			'vue/singleline-html-element-content-newline': 0,
			'vue/no-mutating-props': 0,
			'vue/no-deprecated-v-bind-sync': 0,
			'vue/no-deprecated-slot-attribute': 0,
		}
	},
	{
		ignores: [
			'node_modules',
			'.output',
			'dist',
			'.nuxt',
			'public',
		]
	}
)
