import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import yamlWorker from 'monaco-yaml/yaml.worker?worker'

export function configureMonacoWorkers() {
  self.MonacoEnvironment = {
    getWorker(_: string, label: string) {
      if (label === 'yaml') {
        return new yamlWorker()
      }
      return new editorWorker()
    },
  }
}
