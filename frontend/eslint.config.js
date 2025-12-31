import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import vueTsEslintConfig from '@vue/eslint-config-typescript'
import prettierConfig from '@vue/eslint-config-prettier'

export default [
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue,js,jsx}'],
  },
  {
    name: 'app/files-to-ignore',
    ignores: ['**/dist/**', '**/dist-ssr/**', '**/coverage/**', 'node_modules/**'],
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  ...vueTsEslintConfig(),
  prettierConfig,
  {
    name: 'app/custom-rules',
    rules: {
      'vue/multi-word-component-names': 'off',
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
]
