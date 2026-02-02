import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import yamlWorker from 'monaco-yaml/yaml.worker?worker'

export function configureMonacoWorkers() {
  self.MonacoEnvironment = {
    getWorker(_: string, label: string) {
      try {
        if (label === 'yaml') {
          return new yamlWorker()
        }
        return new editorWorker()
      } catch (error) {
        console.warn(`Failed to create ${label} worker:`, error)
        // Fallback to editor worker if YAML worker fails
        return new editorWorker()
      }
    },
  }
}
