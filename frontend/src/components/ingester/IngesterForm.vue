<template>
  <v-card>
    <v-card-title>
      {{ selectedIngester?.name || 'Dispatch Workflow' }}
    </v-card-title>

    <v-card-text>
      <v-alert v-if="!selectedIngester" type="info" variant="tonal" class="mb-4">
        Select a target workflow from the list below to configure dispatch settings.
      </v-alert>

      <v-select
        v-if="availableIngesters.length > 0"
        v-model="selectedIngesterKey"
        :items="availableIngesters"
        item-title="name"
        item-value="key"
        label="Select Workflow *"
        hint="Choose the target ingestion workflow"
        persistent-hint
        prepend-icon="mdi-send"
        class="mb-4"
      />

      <v-form v-if="selectedIngester" ref="formRef" v-model="formValid">
        <v-text-field
          v-model="form.source"
          :label="isSeadChangeRequest ? 'Normalized Workbook Path *' : 'Source File Path *'"
          :hint="isSeadChangeRequest ? 'Path to the normalized workbook that will be turned into a change package' : 'Path to the Excel file to ingest'"
          persistent-hint
          :rules="[rules.required]"
          prepend-icon="mdi-file-excel"
        />

        <template v-if="isSeadChangeRequest">
          <v-alert type="info" variant="tonal" class="mt-4" data-test="sead-change-request-workflow">
            This workflow collects the operator context needed to validate identities, wait for Binding Set confirmation when required, and emit a Delivery 1 deploy package.
          </v-alert>

          <v-text-field
            v-model="form.submission_name"
            label="Submission Name *"
            hint="Used in pending confirmation guidance and deploy package metadata"
            persistent-hint
            :rules="[rules.required]"
            prepend-icon="mdi-tag"
            class="mt-4"
          />
          <div class="text-caption text-medium-emphasis mb-2">
            {{ isSubmissionNameProjectDerived
              ? 'Auto-derived from the active project and selected datatype until you override it.'
              : 'Operator override for this run.' }}
          </div>

          <v-text-field
            v-model="seadChangeRequest.project_name"
            label="Project Name *"
            hint="Used in deploy package metadata and bundle naming"
            persistent-hint
            :rules="[rules.required]"
            prepend-icon="mdi-folder-outline"
          />
          <div class="text-caption text-medium-emphasis mb-2">
            {{ isProjectNameProjectDerived
              ? 'Auto-derived from the active project.'
              : 'Operator override for this run.' }}
          </div>

          <v-text-field
            v-model="seadChangeRequest.timestamp"
            label="Dispatch Timestamp *"
            hint="Keep this stable when rerunning after Binding Set confirmation"
            persistent-hint
            :rules="[rules.required, rules.submissionTimestamp]"
            prepend-icon="mdi-calendar-clock"
            type="datetime-local"
          />
          <div class="text-caption text-medium-emphasis mb-2">
            Operator-entered for this run.
          </div>

          <v-select
            v-model="seadChangeRequest.datatype"
            :items="approvedDatatypes"
            label="Approved Datatype *"
            hint="The datatype must match the approved SEAD change-control values"
            persistent-hint
            :rules="[rules.required]"
            prepend-icon="mdi-shape"
          />
          <div class="text-caption text-medium-emphasis mb-2">
            Operator-selected for this run.
          </div>

          <v-text-field
            v-model="seadChangeRequest.identifier"
            label="Submission Identifier *"
            hint="A short stable identifier used in bundle naming. Use only A-Z, 0-9, and _."
            persistent-hint
            :rules="[rules.required, rules.submissionIdentifier]"
            prepend-icon="mdi-identifier"
          />
          <div class="text-caption text-medium-emphasis mb-2">
            {{ isIdentifierProjectDerived
              ? 'Auto-derived from the active project name until you override it.'
              : 'Operator override for this run.' }}
          </div>

          <v-textarea
            v-model="seadChangeRequest.description"
            label="Description"
            hint="Optional package description shown in deploy metadata"
            persistent-hint
            :rules="[rules.singleLineDescription]"
            rows="2"
            auto-grow
          />
          <div class="text-caption text-medium-emphasis mb-2">
            {{ isDescriptionProjectDerived
              ? 'Auto-derived from project metadata until you override it.'
              : 'Operator-entered for this run.' }}
          </div>

          <v-text-field
            v-model="seadChangeRequest.issue_number"
            label="Issue Number"
            hint="Optional change-control issue number used in SQL headers and metadata"
            persistent-hint
            prepend-icon="mdi-pound"
          />

          <v-text-field
            v-model="seadChangeRequest.author"
            label="Author"
            hint="Optional author name written into generated package headers"
            persistent-hint
            prepend-icon="mdi-account"
          />

          <v-select
            v-model="deployStrategy"
            :items="deployStrategyOptions"
            item-title="title"
            item-value="value"
            label="Deploy Output *"
            hint="Choose which deploy artifact shape to emit after a successful run"
            persistent-hint
            prepend-icon="mdi-package-variant-closed"
          />
          <div class="text-caption text-medium-emphasis mb-2">
            Operator-selected for this run.
          </div>

          <v-alert type="info" variant="tonal" density="compact" class="mt-2" data-test="deploy-strategy-guidance">
            {{ currentDeployStrategyGuidance }}
          </v-alert>
        </template>

        <template v-else>
          <v-text-field
            v-model="form.submission_name"
            label="Submission Name *"
            hint="Unique name for this submission"
            persistent-hint
            :rules="[rules.required]"
            prepend-icon="mdi-tag"
            class="mt-4"
          />

          <v-text-field
            v-model="form.data_types"
            label="Data Types *"
            hint="Type of data (for example 'dendro', 'ceramics', 'adna')"
            persistent-hint
            :rules="[rules.required]"
            prepend-icon="mdi-shape"
          />
        </template>

        <v-alert
          v-if="targetDataSourceName"
          type="info"
          variant="tonal"
          density="compact"
          class="mt-4"
        >
          <div class="text-caption">
            <strong>Target Database:</strong> {{ targetDataSourceName }}
            <span v-if="targetDataSourceInfo">
              <span v-if="targetDataSourceInfo.host">
                • {{ targetDataSourceInfo.host }}{{ targetDataSourceInfo.port ? ':' + targetDataSourceInfo.port : '' }}
              </span>
              <span v-if="targetDataSourceInfo.database || targetDataSourceInfo.dbname">
                • {{ targetDataSourceInfo.database || targetDataSourceInfo.dbname }}
              </span>
            </span>
          </div>
          <div v-if="!targetDataSourceInfo" class="text-caption error--text mt-1">
            ⚠️ Data source "{{ targetDataSourceName }}" not found in project configuration
          </div>
        </v-alert>

        <v-alert
          v-else
          type="warning"
          variant="tonal"
          density="compact"
          class="mt-4"
        >
          No target database configured for this ingester in the project file.
          Please configure the "ingesters.{{ selectedIngester?.key }}.data_source" option.
        </v-alert>

        <v-expansion-panels class="mt-4">
          <v-expansion-panel :title="isSeadChangeRequest ? 'Input Options' : 'Advanced Options'">
            <v-expansion-panel-text>
              <v-textarea
                v-model="ignoreColumnsText"
                label="Ignore Columns"
                hint="One pattern per line (e.g., 'date_updated', '*_uuid')"
                persistent-hint
                rows="3"
              />

              <v-switch
                v-if="!isSeadChangeRequest"
                v-model="form.do_register"
                label="Register in Database"
                color="primary"
                hide-details
              />

              <v-switch
                v-if="!isSeadChangeRequest"
                v-model="form.explode"
                label="Explode to Public Tables"
                color="primary"
                hide-details
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <v-alert
          v-if="validationPendingConfirmationReport"
          type="warning"
          variant="tonal"
          class="mt-4"
          data-test="validation-pending-confirmation"
        >
          <div class="text-subtitle-2">Binding Set Confirmation Required</div>
          <div class="text-body-2 mt-2">{{ validationPendingConfirmationReport.outstanding_step }}</div>
          <div class="text-caption mt-2"><strong>Binding Set:</strong> {{ validationPendingConfirmationReport.binding_set_uuid || 'Not yet assigned' }}</div>
          <div class="text-caption"><strong>State:</strong> {{ validationPendingConfirmationReport.binding_set_state || 'unknown' }}</div>
          <div class="text-caption"><strong>Blocked entities:</strong> {{ formatList(validationPendingConfirmationReport.blocked_entities) }}</div>
          <div class="text-caption"><strong>Blocked rows:</strong> {{ validationPendingConfirmationReport.blocked_rows }}</div>
          <div class="text-caption mt-2"><strong>Operator action:</strong> {{ validationPendingConfirmationReport.operator_action }}</div>
          <div class="text-caption"><strong>Rerun:</strong> {{ validationPendingConfirmationReport.rerun_instruction }}</div>
        </v-alert>

        <v-alert
          v-else-if="validationResult"
          :type="validationResult.is_valid ? 'success' : 'error'"
          variant="tonal"
          class="mt-4"
        >
          <div class="text-subtitle-2">
            {{ validationResult.is_valid ? 'Validation Passed' : 'Validation Failed' }}
          </div>
          <div v-if="validationResult.errors.length > 0" class="mt-2">
            <div class="text-caption">Errors:</div>
            <ul>
              <li v-for="(error, i) in validationResult.errors" :key="i">{{ error }}</li>
            </ul>
          </div>
          <div v-if="validationResult.warnings.length > 0" class="mt-2">
            <div class="text-caption">Warnings:</div>
            <ul>
              <li v-for="(warning, i) in validationResult.warnings" :key="i">{{ warning }}</li>
            </ul>
          </div>
          <div v-if="validationResult.infos.length > 0" class="mt-2">
            <div class="text-caption">Info:</div>
            <ul>
              <li v-for="(info, i) in validationResult.infos" :key="i">{{ info }}</li>
            </ul>
          </div>
        </v-alert>

        <v-alert
          v-if="ingestionPendingConfirmationReport"
          type="warning"
          variant="tonal"
          class="mt-4"
          data-test="ingestion-pending-confirmation"
        >
          <div class="text-subtitle-2">Binding Set Confirmation Incomplete</div>
          <div class="text-body-2 mt-2">{{ ingestionResult?.message }}</div>
          <div class="text-caption mt-2"><strong>Binding Set:</strong> {{ ingestionPendingConfirmationReport.binding_set_uuid || 'Not yet assigned' }}</div>
          <div class="text-caption"><strong>State:</strong> {{ ingestionPendingConfirmationReport.binding_set_state || 'unknown' }}</div>
          <div class="text-caption"><strong>Blocked entities:</strong> {{ formatList(ingestionPendingConfirmationReport.blocked_entities) }}</div>
          <div class="text-caption"><strong>Blocked rows:</strong> {{ ingestionPendingConfirmationReport.blocked_rows }}</div>
          <div class="text-caption mt-2"><strong>Operator action:</strong> {{ ingestionPendingConfirmationReport.operator_action }}</div>
          <div class="text-caption"><strong>Rerun:</strong> {{ ingestionPendingConfirmationReport.rerun_instruction }}</div>
        </v-alert>

        <v-alert
          v-else-if="ingestionResult"
          :type="ingestionResult.success ? 'success' : 'error'"
          variant="tonal"
          class="mt-4"
        >
          <div class="text-subtitle-2">{{ ingestionResult.message }}</div>
          <div v-if="ingestionResult.success" class="mt-2">
            <div>Records Processed: {{ ingestionResult.records_processed }}</div>
            <div v-if="ingestionResult.submission_id">
              Submission ID: {{ ingestionResult.submission_id }}
            </div>
            <div v-if="ingestionResult.output_path">
              Output: {{ ingestionResult.output_path }}
            </div>
            <template v-if="deployArtifactMetadata">
              <div class="text-caption mt-2"><strong>Deploy strategy:</strong> {{ deployArtifactMetadata.deploy_strategy || deployStrategy }}</div>
              <div v-if="deployArtifactMetadata.binding_set_uuid" class="text-caption"><strong>Binding Set:</strong> {{ deployArtifactMetadata.binding_set_uuid }}</div>
              <div v-if="deployArtifactMetadata.change_request_name" class="text-caption"><strong>Change request:</strong> {{ deployArtifactMetadata.change_request_name }}</div>
              <div class="text-caption"><strong>Revert support:</strong> {{ deployArtifactMetadata.non_revertible ? 'Not implemented in this delivery' : 'Available' }}</div>
            </template>
            <template v-if="deployArtifactManifest">
              <div v-if="deployArtifactManifest.cr_name" class="text-caption"><strong>Bundle name:</strong> {{ deployArtifactManifest.cr_name }}</div>
              <div v-if="deployArtifactManifest.issue_number" class="text-caption"><strong>Issue number:</strong> {{ deployArtifactManifest.issue_number }}</div>
              <div v-if="deployArtifactBundleFiles.length > 0" class="text-caption"><strong>Bundle files:</strong> {{ deployArtifactBundleFiles.join(', ') }}</div>
            </template>
            <div v-if="isSeadChangeRequest" class="text-caption mt-2" data-test="deploy-artifact-guidance">
              <strong>Handoff:</strong> {{ activeDeployArtifactGuidance }}
            </div>
          </div>
          <div v-else-if="ingestionResult.error_details" class="text-caption mt-2">
            {{ ingestionResult.error_details }}
          </div>
        </v-alert>

        <v-alert v-if="error" type="error" variant="tonal" class="mt-4" closable @click:close="clearError">
          {{ error }}
        </v-alert>
      </v-form>
    </v-card-text>

    <v-card-actions>
      <v-btn
        color="primary"
        variant="outlined"
        :loading="isValidating"
        :disabled="!formValid || !selectedIngester"
        @click="handleValidate"
      >
        <v-icon start>mdi-check-circle</v-icon>
        Validate
      </v-btn>

      <v-btn
        color="success"
        :loading="isIngesting"
        :disabled="!formValid || !selectedIngester"
        @click="handleIngest"
      >
        <v-icon start>mdi-send</v-icon>
        Dispatch
      </v-btn>

      <v-spacer />

      <v-btn variant="text" @click="resetForm">
        Reset
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useIngesterStore } from '@/stores/ingester'
import { useDataSourceStore } from '@/stores/data-source'
import { useProjectStore } from '@/stores/project'
import type { DeployArtifact, IngestRequest, PendingConfirmationReport, SubmissionContextInput, ValidateRequest } from '@/types/ingester'

const ingesterStore = useIngesterStore()
const dataSourceStore = useDataSourceStore()
const projectStore = useProjectStore()

const {
  selectedIngester,
  validationResult,
  ingestionResult,
  error,
  isValidating,
  isIngesting
} = storeToRefs(ingesterStore)
const { validate, ingest, clearError, clearValidation, clearIngestion } = ingesterStore
const { selectedProject } = storeToRefs(projectStore)

const formRef = ref()
const formValid = ref(false)
const selectedIngesterKey = ref<string | null>(null)

const approvedDatatypes = [
  'adna',
  'archaeobotany',
  'bugs',
  'ceramics',
  'dendrochronology',
  'isotope',
  'mal',
  'radiocarbon'
]

const deployStrategyOptions = [
  { title: 'Inline SQL Insert Package', value: 'inline_insert' },
  { title: 'COPY CSV Bundle', value: 'copy_csv' }
]

interface SeadChangeRequestFormState {
  project_name: string
  timestamp: string
  datatype: string
  identifier: string
  description: string
  issue_number: string
  author: string
}

function createBaseForm(): IngestRequest {
  return {
    source: '',
    submission_name: '',
    data_types: '',
    do_register: false,
    explode: false,
    config: {
      data_source_name: '',
      ignore_columns: []
    }
  }
}

function createLocalTimestamp(): string {
  const now = new Date()
  now.setSeconds(0, 0)
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

function createSeadChangeRequestState(projectName = ''): SeadChangeRequestFormState {
  return {
    project_name: projectName,
    timestamp: createLocalTimestamp(),
    datatype: 'bugs',
    identifier: '',
    description: '',
    issue_number: '',
    author: ''
  }
}

const form = ref<IngestRequest>(createBaseForm())
const seadChangeRequest = ref<SeadChangeRequestFormState>(createSeadChangeRequestState())
const deployStrategy = ref('inline_insert')

const ignoreColumnsText = ref('date_updated\n*_uuid\n(*')

const availableIngesters = computed(() => ingesterStore.ingesters)
const isSeadChangeRequest = computed(() => selectedIngester.value?.key === 'sead_change_request')
const ingesterConfig = computed(() => {
  if (!selectedProject.value || !selectedIngester.value) return null
  const ingesters = selectedProject.value.options?.ingesters || {}
  return ingesters[selectedIngester.value.key] || null
})
const defaultProjectName = computed(() => selectedProject.value?.metadata?.name?.trim() || '')

const targetDataSourceName = computed(() => {
  return ingesterConfig.value?.data_source || null
})

const targetDataSourceInfo = computed(() => {
  if (!targetDataSourceName.value) return null
  return dataSourceStore.dataSourceByName(targetDataSourceName.value)
})

const validationPendingConfirmationReport = computed<PendingConfirmationReport | null>(() => {
  return validationResult.value?.pending_confirmation_report ?? null
})

const ingestionPendingConfirmationReport = computed<PendingConfirmationReport | null>(() => {
  return ingestionResult.value?.pending_confirmation_report ?? null
})

const deployArtifact = computed<DeployArtifact | null>(() => {
  return ingestionResult.value?.deploy_artifact ?? null
})

const deployArtifactMetadata = computed<Record<string, any> | null>(() => {
  return deployArtifact.value?.metadata ?? null
})

const deployArtifactManifest = computed<Record<string, any> | null>(() => {
  return deployArtifact.value?.metadata_artifact ?? null
})

const deployArtifactBundleFiles = computed(() => {
  return Object.keys(deployArtifact.value?.bundle_files ?? {})
})

const currentDeployStrategyGuidance = computed(() => deployStrategyGuidance(deployStrategy.value))
const activeDeployArtifactGuidance = computed(() => {
  const resolvedStrategy = String(deployArtifactMetadata.value?.deploy_strategy || deployStrategy.value)
  return deployStrategyGuidance(resolvedStrategy)
})

const lastAutoIdentifier = ref('')
const lastAutoSubmissionName = ref('')
const lastAutoDescription = ref('')
const defaultProjectDescription = computed(() => selectedProject.value?.metadata?.description?.trim() || '')
const projectDerivedSubmissionName = computed(() => createSubmissionNameDefault(defaultProjectName.value, seadChangeRequest.value.datatype))
const projectDerivedIdentifier = computed(() => createProjectIdentifierDefault(defaultProjectName.value))
const isProjectNameProjectDerived = computed(() => {
  return !!defaultProjectName.value && seadChangeRequest.value.project_name.trim() === defaultProjectName.value
})
const isSubmissionNameProjectDerived = computed(() => {
  return !!projectDerivedSubmissionName.value && normalizeSubmissionName(form.value.submission_name) === projectDerivedSubmissionName.value
})
const isIdentifierProjectDerived = computed(() => {
  return !!projectDerivedIdentifier.value && normalizeSubmissionIdentifier(seadChangeRequest.value.identifier) === projectDerivedIdentifier.value
})
const isDescriptionProjectDerived = computed(() => {
  return !!defaultProjectDescription.value && seadChangeRequest.value.description.trim() === defaultProjectDescription.value
})

watch(ignoreColumnsText, (newValue) => {
  form.value.config!.ignore_columns = newValue
    .split('\n')
    .map(s => s.trim())
    .filter(s => s.length > 0)
})

watch(selectedIngesterKey, (key) => {
  if (key) {
    ingesterStore.selectIngester(key)
  }
})

watch(selectedIngester, (ingester) => {
  if (ingester?.key && selectedIngesterKey.value !== ingester.key) {
    selectedIngesterKey.value = ingester.key
  }
}, { immediate: true })

watch(defaultProjectName, (projectName) => {
  if (projectName && !seadChangeRequest.value.project_name) {
    seadChangeRequest.value.project_name = projectName
  }
}, { immediate: true })

watch(defaultProjectDescription, (description) => {
  if (!description) {
    return
  }

  const currentDescription = seadChangeRequest.value.description.trim()
  if (!currentDescription || currentDescription === lastAutoDescription.value) {
    seadChangeRequest.value.description = description
    lastAutoDescription.value = description
  }
}, { immediate: true })

watch(() => seadChangeRequest.value.project_name, (projectName, previousProjectName) => {
  const nextAutoIdentifier = createProjectIdentifierDefault(projectName)
  const previousAutoIdentifier = createProjectIdentifierDefault(previousProjectName || '')
  const currentIdentifier = normalizeSubmissionIdentifier(seadChangeRequest.value.identifier)

  if (nextAutoIdentifier && (!currentIdentifier || currentIdentifier === lastAutoIdentifier.value || currentIdentifier === previousAutoIdentifier)) {
    seadChangeRequest.value.identifier = nextAutoIdentifier
    lastAutoIdentifier.value = nextAutoIdentifier
  }
}, { immediate: true })

watch(
  [() => seadChangeRequest.value.project_name, () => seadChangeRequest.value.datatype],
  ([projectName, datatype], [previousProjectName, previousDatatype]) => {
    const nextAutoSubmissionName = createSubmissionNameDefault(projectName, datatype)
    const previousAutoSubmissionName = createSubmissionNameDefault(previousProjectName || '', previousDatatype || '')
    const currentSubmissionName = normalizeSubmissionName(form.value.submission_name)

    if (
      nextAutoSubmissionName
      && (!currentSubmissionName || currentSubmissionName === lastAutoSubmissionName.value || currentSubmissionName === previousAutoSubmissionName)
    ) {
      form.value.submission_name = nextAutoSubmissionName
      lastAutoSubmissionName.value = nextAutoSubmissionName
    }
  },
  { immediate: true },
)

watch(() => seadChangeRequest.value.identifier, (identifier) => {
  const normalizedIdentifier = normalizeSubmissionIdentifier(identifier)

  if (identifier !== normalizedIdentifier) {
    seadChangeRequest.value.identifier = normalizedIdentifier
  }
})

watch(() => form.value.submission_name, (submissionName) => {
  const normalizedSubmissionName = normalizeSubmissionName(submissionName)

  if (submissionName !== normalizedSubmissionName) {
    form.value.submission_name = normalizedSubmissionName
  }
})

watch(ingesterConfig, () => {
  applyIngesterDefaults()
}, { immediate: true })

const rules = {
  required: (v: string) => !!v || 'Required field',
  submissionTimestamp: (value: string) => {
    if (!isSeadChangeRequest.value) {
      return true
    }

    return isValidSubmissionTimestamp(value) || 'Enter a valid ISO-8601 local datetime'
  },
  submissionIdentifier: (value: string) => {
    if (!isSeadChangeRequest.value) {
      return true
    }

    return isValidSubmissionIdentifier(value) || 'Use only A-Z, 0-9, and _; max 39 characters'
  },
  singleLineDescription: (value: string) => {
    return isValidDescription(value) || 'Use a single line shorter than 80 characters'
  }
}

function normalizeSubmissionIdentifier(identifier: string): string {
  return identifier.trim().toUpperCase()
}

function normalizeSubmissionName(submissionName: string): string {
  return submissionName
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

function createProjectIdentifierDefault(projectName: string): string {
  return normalizeSubmissionIdentifier(projectName)
    .replace(/[^A-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 39)
}

function createSubmissionNameDefault(projectName: string, datatype: string): string {
  const nameParts = [projectName, datatype]
    .map(value => normalizeSubmissionName(value))
    .filter(Boolean)

  return nameParts.join('_')
}

function isValidSubmissionTimestamp(value: string): boolean {
  if (!value.trim()) {
    return false
  }

  return !Number.isNaN(new Date(value).getTime())
}

function isValidSubmissionIdentifier(value: string): boolean {
  const normalizedIdentifier = normalizeSubmissionIdentifier(value)
  return /^[A-Z0-9_]+$/.test(normalizedIdentifier) && normalizedIdentifier.length < 40
}

function isValidDescription(value: string): boolean {
  const normalizedDescription = value.trim()

  if (!normalizedDescription) {
    return true
  }

  return !/[\r\n]/.test(normalizedDescription) && normalizedDescription.length < 80
}

function deployStrategyGuidance(strategy: string): string {
  if (strategy === 'copy_csv') {
    return 'Review the emitted SQL, manifest, and compressed table payload files before handing the bundle to the controlled SCCS runtime.'
  }

  return 'Review the generated deploy, revert, and verify SQL files plus the manifest before handing the package to the operator who will execute it.'
}

function formatList(values: string[]): string {
  return values.length > 0 ? values.join(', ') : 'None'
}

function applyIngesterDefaults() {
  const config = ingesterConfig.value

  if (form.value.config) {
    form.value.config.data_source_name = config?.data_source || ''
  }

  ignoreColumnsText.value = config?.options?.ignore_columns?.join('\n') || 'date_updated\n*_uuid\n(*'

  form.value.do_register = config?.options?.do_register ?? false
  form.value.explode = config?.options?.explode ?? false

  if (!seadChangeRequest.value.project_name && defaultProjectName.value) {
    seadChangeRequest.value.project_name = defaultProjectName.value
  }

  if (!seadChangeRequest.value.identifier && seadChangeRequest.value.project_name) {
    const autoIdentifier = createProjectIdentifierDefault(seadChangeRequest.value.project_name)
    seadChangeRequest.value.identifier = autoIdentifier
    lastAutoIdentifier.value = autoIdentifier
  }

  if (!form.value.submission_name && seadChangeRequest.value.project_name) {
    const autoSubmissionName = createSubmissionNameDefault(seadChangeRequest.value.project_name, seadChangeRequest.value.datatype)
    form.value.submission_name = autoSubmissionName
    lastAutoSubmissionName.value = autoSubmissionName
  }

  if (!seadChangeRequest.value.description && defaultProjectDescription.value) {
    seadChangeRequest.value.description = defaultProjectDescription.value
    lastAutoDescription.value = defaultProjectDescription.value
  }
}

function buildSubmissionContext(): SubmissionContextInput | undefined {
  if (!isSeadChangeRequest.value) {
    return undefined
  }

  return {
    submission_name: normalizeSubmissionName(form.value.submission_name),
    project_name: seadChangeRequest.value.project_name.trim(),
    timestamp: seadChangeRequest.value.timestamp,
    datatype: seadChangeRequest.value.datatype,
    identifier: normalizeSubmissionIdentifier(seadChangeRequest.value.identifier),
    description: seadChangeRequest.value.description.trim() || undefined,
    issue_number: seadChangeRequest.value.issue_number.trim() || undefined,
    author: seadChangeRequest.value.author.trim() || undefined
  }
}

function buildValidateRequest(): ValidateRequest {
  return {
    source: form.value.source,
    config: form.value.config,
    submission_context: buildSubmissionContext(),
    deploy_strategy: isSeadChangeRequest.value ? deployStrategy.value : undefined
  }
}

function buildIngestRequest(): IngestRequest {
  return {
    ...form.value,
    submission_name: normalizeSubmissionName(form.value.submission_name),
    data_types: isSeadChangeRequest.value ? seadChangeRequest.value.datatype : form.value.data_types.trim(),
    config: form.value.config,
    submission_context: buildSubmissionContext(),
    deploy_strategy: isSeadChangeRequest.value ? deployStrategy.value : undefined
  }
}

async function handleValidate() {
  const validationState = await formRef.value?.validate?.()
  if (validationState && validationState.valid === false) return
  if (!formValid.value) return

  clearValidation()
  clearError()

  await validate(buildValidateRequest())
}

async function handleIngest() {
  const validationState = await formRef.value?.validate?.()
  if (validationState && validationState.valid === false) return
  if (!formValid.value) return

  clearValidation()
  clearIngestion()
  clearError()

  await ingest(buildIngestRequest())
}

function resetForm() {
  formRef.value?.resetValidation?.()
  form.value = createBaseForm()
  seadChangeRequest.value = createSeadChangeRequestState(defaultProjectName.value)
  lastAutoIdentifier.value = ''
  lastAutoSubmissionName.value = ''
  lastAutoDescription.value = ''
  deployStrategy.value = 'inline_insert'
  applyIngesterDefaults()
  clearValidation()
  clearIngestion()
  clearError()
}

onMounted(async () => {
  if (ingesterStore.ingesters.length === 0) {
    await ingesterStore.fetchIngesters()
  }

  if (availableIngesters.value.length === 1) {
    const firstIngester = availableIngesters.value[0]
    if (firstIngester) {
      selectedIngesterKey.value = firstIngester.key
    }
  }

  if (dataSourceStore.dataSources.length === 0) {
    try {
      await dataSourceStore.fetchDataSources()
    } catch (err) {
      console.error('Failed to load data sources:', err)
    }
  }
})
</script>
