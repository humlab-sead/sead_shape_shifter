<template>
  <v-dialog v-model="dialogModel" :max-width="viewMode !== 'form' ? '95vw' : '900'"
    :height="viewMode !== 'form' ? '90vh' : '800'" persistent scrollable>
    <v-card style="height: 100%">
      <v-toolbar color="primary" density="compact">
        <v-toolbar-title>
          <v-icon :icon="mode === 'create' ? 'mdi-plus-circle' : 'mdi-pencil'" class="mr-2" />
          {{ mode === 'create' ? 'Create Entity' : `Edit ${entity?.name}` }}
        </v-toolbar-title>
        <v-spacer />

        <!-- Three-state view toggle -->
        <v-btn-toggle v-model="viewMode" mandatory density="compact" :disabled="mode === 'create'" class="mr-2">
          <v-btn value="form" size="small">
            <v-icon size="small">mdi-form-select</v-icon>
            <v-tooltip activator="parent" location="bottom">Form Only</v-tooltip>
          </v-btn>
          <v-btn value="both" size="small">
            <v-icon size="small">mdi-view-split-vertical</v-icon>
            <v-tooltip activator="parent" location="bottom">Split View (Ctrl+Shift+P)</v-tooltip>
          </v-btn>
          <v-btn value="preview" size="small">
            <v-icon size="small">mdi-table</v-icon>
            <v-tooltip activator="parent" location="bottom">Preview Only</v-tooltip>
          </v-btn>
        </v-btn-toggle>
      </v-toolbar>

      <v-tabs v-model="activeTab" bg-color="primary">
        <v-tab value="basic">Basic</v-tab>
        <v-tab value="relationships" :disabled="mode === 'create'">Foreign Keys</v-tab>
        <v-tab value="filters" :disabled="mode === 'create'">Filters</v-tab>
        <v-tab value="unnest" :disabled="mode === 'create'">Unnest</v-tab>
        <v-tab value="append" :disabled="mode === 'create'">Append</v-tab>
        <v-tab value="extra_columns" :disabled="mode === 'create'">Extra Columns</v-tab>
        <v-tab value="replacements" :disabled="mode === 'create'">Replace</v-tab>
        <v-tab value="yaml" :disabled="mode === 'create'">
          <v-icon icon="mdi-code-braces" class="mr-1" size="small" />
          YAML
        </v-tab>
      </v-tabs>

      <v-card-text class="pa-0 dialog-content" :class="{ 'split-container': viewMode !== 'form' }">
        <!-- Loading overlay while fetching entity data -->
        <v-overlay v-model="loading" contained persistent class="align-center justify-center">
          <v-progress-circular indeterminate size="64" color="primary" />
          <div class="mt-4 text-h6">Loading entity data...</div>
        </v-overlay>

        <div :class="viewMode !== 'form' ? 'split-layout' : ''" :data-view-mode="viewMode">
          <!-- Left: Entity Form -->
          <div v-show="viewMode === 'form' || viewMode === 'both'"
            :class="viewMode === 'both' ? 'form-panel' : 'pt-6 px-4 form-content'">
            <v-window v-model="activeTab">
              <v-window-item value="basic">
                <v-defaults-provider :defaults="{
                  VTextField: { density: 'compact', variant: 'outlined', },
                  VSelect: { density: 'compact', variant: 'outlined', },
                  VAutocomplete: { density: 'compact', variant: 'outlined', },
                  VCombobox: { density: 'compact', variant: 'outlined', },
                  VCheckbox: { density: 'compact', hideDetails: true },
                }">
                  <v-form ref="formRef" v-model="formValid" class="compact-form">
                    <!-- Entity Name, Type, and Source/Data Source on same row -->
                    <div class="form-row">
                      <v-row no-gutters>
                        <v-col cols="4" class="pr-2">
                          <v-text-field v-model="formData.name" label="Entity Name *" :rules="nameRules"
                            variant="outlined" :disabled="mode === 'edit'" required>
                            <template #message>
                              <span class="text-caption">Unique identifier for this entity</span>
                            </template>
                          </v-text-field>
                        </v-col>

                        <v-col cols="4" class="px-1">
                          <!-- Entity Type -->
                          <v-select v-model="formData.type" :items="entityTypeOptions" label="Type *"
                            :rules="requiredRule" variant="outlined" required hide-details="auto">
                            <template #append-inner>
                              <v-tooltip location="top" text="How this entity gets its data">
                                <template #activator="{ props }">
                                  <v-icon v-bind="props" icon="mdi-help-circle-outline" size="small"
                                    class="text-medium-emphasis" tabindex="0" />
                                </template>
                              </v-tooltip>
                            </template>
                          </v-select>
                        </v-col>

                        <v-col cols="4" class="pl-2">
                          <!-- Source Entity (only for 'entity' type) -->
                          <v-autocomplete v-if="formData.type === 'entity'" v-model="formData.source"
                            :items="availableSourceEntities" label="Source Entity" variant="outlined"
                            :disabled="mode === 'edit'" clearable persistent-placeholder>
                            <template #message>
                              <span class="text-caption">Parent entity to derive this entity from</span>
                            </template>
                          </v-autocomplete>

                          <!-- Data Source (only for 'sql' type) -->
                          <v-autocomplete v-if="formData.type === 'sql'" v-model="formData.data_source"
                            :items="availableDataSources" label="Data Source *"
                            :rules="formData.type === 'sql' ? requiredRule : []" variant="outlined" clearable>
                            <template #message>
                              <span class="text-caption">Name of the data source connection</span>
                            </template>
                          </v-autocomplete>
                        </v-col>
                      </v-row>
                    </div>

                    <!-- File Options Row (for CSV, Excel types) -->
                    <div class="form-row" v-if="isFileType">
                      <v-row no-gutters>
                        <!-- Filename -->
                        <v-col :cols="formData.type === 'csv' ? 8 : 12" :class="formData.type === 'csv' ? 'pr-2' : ''">
                          <v-autocomplete 
                            v-model="formData.options.filename" 
                            :items="availableProjectFiles"
                            item-title="name"
                            item-value="name"
                            label="File *" 
                            :rules="requiredRule" 
                            variant="outlined" 
                            clearable 
                            :loading="filesLoading">
                            <template v-slot:item="{ props, item }">
                              <v-list-item v-bind="props">
                                <template v-slot:append>
                                  <v-chip 
                                    :color="item.raw.location === 'global' ? 'primary' : 'secondary'" 
                                    size="x-small" 
                                    variant="flat">
                                    {{ item.raw.location === 'global' ? 'Global' : 'Project' }}
                                  </v-chip>
                                </template>
                              </v-list-item>
                            </template>
                          </v-autocomplete>
                        </v-col>

                        <!-- CSV Delimiter -->
                        <v-col v-if="formData.type === 'csv'" cols="4" class="pl-2">
                          <v-select v-model="formData.options.sep" :items="delimiterOptions" label="Delimiter *"
                            :rules="requiredRule" variant="outlined" />
                        </v-col>
                      </v-row>

                      <!-- Excel Options (sheet name and range) -->
                      <v-row no-gutters v-if="isExcelType" class="mt-2">
                        <!-- Sheet Name -->
                        <v-col :cols="formData.type === 'openpyxl' ? 6 : 12"
                          :class="formData.type === 'openpyxl' ? 'pr-2' : ''">
                          <v-autocomplete v-model="formData.options.sheet_name" :items="sheetOptions" label="Sheet Name"
                            variant="outlined" placeholder="Sheet1" clearable :loading="sheetOptionsLoading"
                            @update:model-value="handleSheetSelection" />
                        </v-col>

                        <!-- Range (OpenPyxl only) -->
                        <v-col v-if="formData.type === 'openpyxl'" cols="6" class="pl-2">
                          <v-text-field v-model="formData.options.range" label="Cell Range" variant="outlined"
                            placeholder="A1:G99" />
                        </v-col>
                      </v-row>
                    </div>

                    <!-- Identity Section: system_id (info), public_id (required), keys (required) -->
                    <div class="form-row">
                      <v-row no-gutters>
                        <!-- System ID (info only - always "system_id") -->
                        <v-col cols="4" class="pr-2">
                          <v-text-field model-value="system_id" label="System ID" variant="outlined" readonly
                            class="system-id-field">
                            <template #append-inner>
                              <v-tooltip location="top" max-width="400">
                                <template #activator="{ props }">
                                  <v-icon v-bind="props" icon="mdi-information-outline" size="small"
                                    class="text-medium-emphasis" />
                                </template>
                                <div class="text-body-2">
                                  <strong>System ID (Local Scope)</strong><br />
                                  Auto-incrementing local identifier (1, 2, 3...).<br />
                                  Always named 'system_id' - not configurable.
                                </div>
                              </v-tooltip>
                            </template>
                            <template #message>
                              <span class="text-caption">Local auto-incrementing ID (always "system_id")</span>
                            </template>
                          </v-text-field>
                        </v-col>

                        <!-- Public ID (target system PK, defines FK columns) -->
                        <v-col cols="4" class="px-1">
                          <v-text-field v-model="formData.public_id" label="Public ID *" variant="outlined"
                            placeholder="e.g., sample_type_id" :rules="publicIdRules" required>
                            <template #append-inner>
                              <v-tooltip location="top" max-width="400">
                                <template #activator="{ props }">
                                  <v-icon v-bind="props" icon="mdi-information-outline" size="small"
                                    class="text-medium-emphasis" />
                                </template>
                                <div class="text-body-2">
                                  <strong>Public ID (Global Scope)</strong><br />
                                  1. Target system primary key name<br />
                                  2. Defines FK column names in child entities<br />
                                  Must end with '_id' (e.g., 'sample_type_id').
                                </div>
                              </v-tooltip>
                            </template>
                            <!-- <template #message>
                              <span class="text-caption">Target PK name + FK column name pattern</span>
                            </template> -->
                          </v-text-field>
                        </v-col>

                        <v-col cols="4" class="pl-2">
                          <!-- Keys (business keys) -->
                          <v-combobox v-model="formData.keys" label="Business Keys *" variant="outlined" multiple chips
                            closable-chips persistent-placeholder>
                            <template #message>
                              <span class="text-caption">Natural key columns that uniquely identify records</span>
                            </template>
                          </v-combobox>
                        </v-col>
                      </v-row>
                    </div>

                    <!-- Columns (for entity/fixed types) -->
                    <div class="form-row" v-if="formData.type === 'entity' || formData.type === 'fixed' || isFileType">
                      <v-combobox v-model="formData.columns" :items="availableColumns" label="Columns"
                        variant="outlined" multiple chips closable-chips persistent-placeholder>
                        <template #message>
                          <span class="text-caption">Column names to extract or create</span>
                        </template>
                      </v-combobox>
                    </div>
                    <!-- Fixed Values Grid (only for fixed type) -->
                    <div class="form-row" v-if="formData.type === 'fixed'">
                      <FixedValuesGrid v-if="fixedValuesColumns.length > 0" v-model="formData.values" :columns="fixedValuesColumns"
                        :public-id="formData.public_id" height="400px" />
                      <v-alert v-else type="info" variant="tonal" density="compact" class="mb-2">
                        <v-alert-title>No Columns Defined</v-alert-title>
                        Add keys and/or columns above to define the grid structure for fixed values.
                      </v-alert>
                    </div>

                    <!-- Depends On -->
                    <div class="form-row">
                      <v-combobox v-model="formData.depends_on" label="Depends On" :items="availableSourceEntities"
                        variant="outlined" multiple chips closable-chips persistent-placeholder>
                        <template #message>
                          <span class="text-caption">Entities that must be processed before this entity</span>
                        </template>
                      </v-combobox>
                    </div>

                    <!-- Drop Duplicates and Drop Empty Rows on same row -->
                    <div class="form-row">
                      <v-row no-gutters>
                        <!-- Drop Duplicates -->
                        <v-col cols="6" class="pr-2">
                          <v-row no-gutters class="mb-2">
                            <v-col cols="4">
                              <v-checkbox v-model="formData.drop_duplicates.enabled" label="Drop Duplicates"
                                hide-details />
                            </v-col>
                            <v-col cols="8" class="pl-1">
                              <v-checkbox v-model="formData.check_functional_dependency"
                                label="Check Functional Dependency" hide-details
                                :disabled="!formData.drop_duplicates.enabled" />
                            </v-col> </v-row>

                          <v-combobox v-model="formData.drop_duplicates.columns" label="Deduplication Columns"
                            variant="outlined" multiple chips closable-chips persistent-placeholder
                            :disabled="!formData.drop_duplicates.enabled">
                            <template #message>
                              <span class="text-caption">Columns to use for deduplication (empty = all columns)</span>
                            </template>
                          </v-combobox>
                        </v-col>

                        <!-- Drop Empty Rows -->
                        <v-col cols="6" class="pl-2">
                          <v-row no-gutters class="mb-2">
                            <v-col cols="12" class="pr-1">
                              <v-checkbox v-model="formData.drop_empty_rows.enabled" label="Drop Empty Rows"
                                hide-details />
                            </v-col>
                          </v-row>
                          <v-combobox v-model="formData.drop_empty_rows.columns"
                            label="Columns to Check for Empty Values" variant="outlined" multiple chips closable-chips
                            persistent-placeholder :disabled="!formData.drop_empty_rows.enabled">
                            <template #message>
                              <span class="text-caption">Columns to check for empty values (empty = all columns)</span>
                            </template>
                          </v-combobox>
                        </v-col>
                      </v-row>
                    </div>

                    <!-- Smart Suggestions Panel -->
                    <div class="form-row" v-if="(showSuggestions || suggestionsLoading) && fkSuggestionsEnabled">
                      <v-progress-linear v-if="suggestionsLoading" indeterminate color="primary" class="mb-2" />

                      <SuggestionsPanel v-if="suggestions && !suggestionsLoading" :suggestions="suggestions"
                        @accept-foreign-key="handleAcceptForeignKey" @reject-foreign-key="handleRejectForeignKey"
                        @accept-dependency="handleAcceptDependency" @reject-dependency="handleRejectDependency" />
                    </div>

                    <!-- SQL Query (for sql type) -->
                    <div class="form-row" v-if="formData.type === 'sql'">
                      <SqlEditor v-model="formData.query" height="250px"
                        help-text="SQL query to execute against the selected data source"
                        :error="formValid === false && !formData.query ? 'SQL query is required' : ''" />
                    </div>

                    <v-alert v-if="error" type="error" variant="tonal" class="mt-4">
                      {{ error }}
                    </v-alert>
                  </v-form>
                </v-defaults-provider>
              </v-window-item>

              <v-window-item value="relationships">
                <foreign-key-editor v-model="formData.foreign_keys" :available-entities="availableSourceEntities"
                  :project-name="projectName" :entity-name="formData.name" :is-entity-saved="mode === 'edit'" />
              </v-window-item>

              <v-window-item value="filters">
                <filters-editor v-model="formData.advanced.filters" :available-entities="availableSourceEntities" />
              </v-window-item>

              <v-window-item value="unnest">
                <unnest-editor v-model="formData.advanced.unnest" :available-columns="availableColumnsForUnnest" />
              </v-window-item>

              <v-window-item value="append">
                <append-editor v-model="formData.advanced.append" />
              </v-window-item>

              <v-window-item value="extra_columns">
                <extra-columns-editor v-model="formData.advanced.extra_columns" />
              </v-window-item>

              <v-window-item value="replacements">
                <replacements-editor v-model="formData.advanced.replacements" :available-columns="formData.columns" />
              </v-window-item>

              <v-window-item value="yaml">
                <v-alert type="info" variant="tonal" density="compact" class="mb-4">
                  <div class="text-caption">
                    <v-icon icon="mdi-information" size="small" class="mr-1" />
                    Edit the entity in YAML format. Changes will be synced with the form editor.
                  </div>
                </v-alert>

                <yaml-editor v-model="yamlContent" height="500px" mode="entity" :validation-context="validationContext"
                  :validate-on-change="true" @validate="handleYamlValidation" @change="handleYamlChange" />

                <v-alert v-if="yamlError" type="error" density="compact" variant="tonal" class="mt-2">
                  {{ yamlError }}
                </v-alert>
              </v-window-item>
            </v-window>
          </div>

          <!-- Right: Live Preview Panel -->
          <div v-show="viewMode === 'both' || viewMode === 'preview'" class="preview-panel">
            <div class="preview-header">
              <div class="d-flex align-center justify-space-between pa-2">
                <div class="d-flex align-center gap-2">
                  <v-select v-model="previewLimit" :items="previewLimitOptions" item-title="title" item-value="value"
                    label="Rows" density="compact" variant="outlined" style="max-width: 150px" hide-details
                    @update:model-value="refreshPreview" />

                  <v-btn size="small" variant="tonal" @click="refreshPreview" :loading="previewLoading"
                    :disabled="!canPreview">
                    <v-icon start size="small">mdi-refresh</v-icon>
                    Refresh
                  </v-btn>

                  <v-chip v-if="livePreviewData" size="small" color="primary" variant="tonal">
                    {{ livePreviewData.total_rows_in_preview || 0 }} rows
                  </v-chip>

                  <v-chip v-if="livePreviewLastRefresh" size="small" variant="text">
                    <v-icon start size="x-small">mdi-clock-outline</v-icon>
                    {{ formatRefreshTime(livePreviewLastRefresh) }}
                  </v-chip>
                </div>

                <v-checkbox v-model="autoRefreshEnabled" label="Auto-refresh" density="compact" hide-details
                  class="mt-0" />
              </div>

              <v-alert v-if="previewError" type="error" density="compact" closable class="ma-2"
                @click:close="previewError = null">
                <div v-if="typeof previewError === 'string'">{{ previewError }}</div>
                <div v-else-if="previewError?.detail?.message">
                  <div class="font-weight-bold mb-1">{{ previewError.detail.error_type || 'Error' }}</div>
                  <div class="text-caption" style="white-space: pre-wrap">{{ previewError.detail.message }}</div>
                  <div v-if="previewError.detail.tips?.length" class="mt-2">
                    <div class="text-caption font-weight-bold">Suggestions:</div>
                    <ul class="text-caption mt-1">
                      <li v-for="(tip, idx) in previewError.detail.tips" :key="idx">{{ tip }}</li>
                    </ul>
                  </div>
                </div>
                <div v-else-if="previewError?.message">
                  {{ previewError.message }}
                </div>
                <div v-else>{{ previewError }}</div>
              </v-alert>

              <v-alert v-if="!canPreview" type="info" density="compact" class="ma-2">
                Entity must be saved before preview is available
              </v-alert>
            </div>

            <div class="preview-content">
              <v-progress-linear v-if="previewLoading" indeterminate color="primary" />

              <div v-if="livePreviewData && !previewLoading" class="preview-table-container">
                <div class="preview-grid-wrapper">
                  <ag-grid-vue class="ag-theme-alpine preview-ag-grid" :style="{ height: '100%', width: '100%' }"
                    :columnDefs="previewColumnDefs" :rowData="previewRowData" :defaultColDef="previewDefaultColDef"
                    :animateRows="true" :suppressCellFocus="true" :headerHeight="32" :rowHeight="28" />
                </div>
              </div>

              <div v-else-if="!previewLoading && !livePreviewData"
                class="d-flex align-center justify-center pa-8 text-disabled">
                <div class="text-center">
                  <v-icon size="64" color="disabled">mdi-table-off</v-icon>
                  <div class="mt-2">No preview data</div>
                  <div class="text-caption">Click Refresh to load preview</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </v-card-text>

      <v-card-actions>
        <!-- Materialization buttons (edit mode only, not create) -->
        <!-- DEBUG: mode={{ mode }}, currentEntity={{ !!currentEntity }}, materialized={{ currentEntity?.materialized?.enabled }} -->
        <template v-if="mode === 'edit' && currentEntity">
          <v-btn v-if="currentEntity.materialized?.enabled" color="warning" variant="text"
            prepend-icon="mdi-database-arrow-up" @click="showUnmaterializeDialog = true" :disabled="loading">
            Unmaterialize
          </v-btn>
          <v-btn v-else-if="currentEntity.entity_data.type !== 'fixed'" color="primary" variant="text"
            prepend-icon="mdi-database-arrow-down" @click="showMaterializeDialog = true" :disabled="loading">
            Materialize
          </v-btn>
        </template>

        <!-- Save success indicator -->
        <v-fade-transition>
          <v-chip v-if="showSaveSuccess" color="success" size="small" prepend-icon="mdi-check-circle" class="ml-2">
            Saved successfully
          </v-chip>
        </v-fade-transition>

        <v-spacer />
        <v-btn variant="text" @click="handleCancel" :disabled="loading"> Cancel </v-btn>
        <v-btn color="primary" variant="flat" :loading="loading" :disabled="!formValid" @click="handleSubmit">
          <v-icon start>mdi-content-save</v-icon>
          Save
        </v-btn>
        <v-btn color="primary" variant="outlined" :loading="loading" :disabled="!formValid" @click="handleSubmitAndClose">
          Save & Close
        </v-btn>
      </v-card-actions>

      <!-- Materialization Dialogs -->
      <MaterializeDialog v-model="showMaterializeDialog" :project-name="projectName" :entity-name="entity?.name || ''"
        @materialized="handleMaterialized" />
      <UnmaterializeDialog v-model="showUnmaterializeDialog" :project-name="projectName"
        :entity-name="entity?.name || ''" @unmaterialized="handleUnmaterialized" />
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
/**
 * EntityFormDialog - Create and edit entities
 *
 * Supports dual-mode editing: visual form and raw YAML
 * Includes live preview panel for saved entities
 * 
 * STATE MANAGEMENT STRATEGY:
 * - On dialog open, ALWAYS fetches fresh entity data from API (edit mode)
 * - This ensures we display the latest data from the YAML file (source of truth)
 * - Avoids issues with stale state in Pinia store or reactive prop chains
 * - Adds minimal overhead (~10-50ms API call) for guaranteed data consistency
 */
import { ref, computed, watch, watchEffect, onMounted, onUnmounted } from 'vue'
import { useEntities, useSuggestions, useEntityPreview, useSettings } from '@/composables'
import { useNotification } from '@/composables/useNotification'
import { useProjectStore, useEntityStore } from '@/stores'
import type { EntityResponse } from '@/api/entities'
import type { ForeignKeySuggestion, DependencySuggestion } from '@/composables'
import * as yaml from 'js-yaml'
import { AgGridVue } from 'ag-grid-vue3'
import type { ColDef } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'
import ForeignKeyEditor from './ForeignKeyEditor.vue'
import FiltersEditor from './FiltersEditor.vue'
import UnnestEditor from './UnnestEditor.vue'
import AppendEditor from './AppendEditor.vue'
import ExtraColumnsEditor from './ExtraColumnsEditor.vue'
import ReplacementsEditor from './ReplacementsEditor.vue'
import SuggestionsPanel from './SuggestionsPanel.vue'
// import EntityPreviewPanel from './EntityPreviewPanel.vue'
import YamlEditor from '../common/YamlEditor.vue'
import SqlEditor from '../common/SqlEditor.vue'
import MaterializeDialog from './MaterializeDialog.vue'
import UnmaterializeDialog from './UnmaterializeDialog.vue'
import type { ValidationContext } from '@/utils/projectYamlValidator'
import { defineAsyncComponent, nextTick } from 'vue'
import { api } from '@/api'

// Lazy load FixedValuesGrid to avoid ag-grid loading unless needed
const FixedValuesGrid = defineAsyncComponent(() => import('./FixedValuesGrid.vue'))

interface Props {
  modelValue: boolean
  projectName: string
  entity?: EntityResponse | null
  mode: 'create' | 'edit'
  initialTab?: 'form' | 'yaml'
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved', entityName: string): void
}

// Error type that can be a string, an API error response, or null
type PreviewError =
  | string
  | {
      detail?: {
        message: string
        error_type?: string
        tips?: string[]
      }
      message?: string
    }
  | null

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { entities, create, update } = useEntities({
  projectName: props.projectName,
  autoFetch: false,
})

const { getSuggestionsForEntity, loading: suggestionsLoading } = useSuggestions()

const appSettings = useSettings()
const fkSuggestionsEnabled = computed(() => appSettings.enableFkSuggestions.value)

const { error: showError } = useNotification()

const projectStore = useProjectStore()

// Split-pane and preview state
type ViewMode = 'form' | 'both' | 'preview'
const viewMode = ref<ViewMode>('form')
const autoRefreshEnabled = ref(false)
const previewLimit = ref<number | null>(100)

// Live preview composable (separate from the preview tab)
const {
  previewData: livePreviewData,
  loading: previewLoading,
  error: livePreviewError,
  lastRefresh: livePreviewLastRefresh,
  previewEntity,
  debouncedPreviewEntity,
  clearPreview,
} = useEntityPreview()

const previewLimitOptions = [
  { title: '10 rows', value: 10 },
  { title: '25 rows', value: 25 },
  { title: '50 rows', value: 50 },
  { title: '100 rows', value: 100 },
  { title: '200 rows', value: 200 },
  { title: '500 rows', value: 500 },
  { title: '1,000 rows', value: 1000 },
  { title: 'All rows', value: null },
]

const previewError = ref<PreviewError>(null)

// Form state
const formRef = ref()
const formValid = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const showSaveSuccess = ref(false)
let saveSuccessTimeout: ReturnType<typeof setTimeout> | null = null
const suggestions = ref<any>(null)
const showSuggestions = ref(false)
const yamlContent = ref('')
const yamlError = ref<string | null>(null)
const yamlValid = ref(true)

// Materialization dialogs
const showMaterializeDialog = ref(false)
const showUnmaterializeDialog = ref(false)

// Store complete entity data (including materialized metadata) for UI checks
const currentEntity = ref<EntityResponse | null>(null)

interface FormData {
  name: string
  type: string
  system_id: string  // Always "system_id"
  public_id: string  // Target system PK name and FK column pattern
  surrogate_id: string  // Deprecated - for backward compatibility
  keys: string[]
  columns: string[]
  values: any[][] // For fixed type entities
  source: string | null
  data_source: string
  query: string
  options: {
    filename: string
    sep: string
    encoding: string
    sheet_name: string
    range: string
  }
  foreign_keys: any[]
  depends_on: string[]
  drop_duplicates: {
    enabled: boolean
    columns: string[]
  }
  drop_empty_rows: {
    enabled: boolean
    columns: string[]
  }
  check_functional_dependency: boolean
  advanced: {
    filters?: any[]
    unnest?: any | null
    append?: any[]
    extra_columns?: Record<string, string | null>
    replacements?: Record<string, any>
  }
}

const formData = ref<FormData>({
  name: '',
  type: 'entity',
  system_id: 'system_id',  // Always "system_id"
  public_id: '',  // Required field
  surrogate_id: '',  // Deprecated - kept for backward compat
  keys: [],
  columns: [],
  values: [],
  source: null,
  data_source: '',
  query: '',
  options: {
    filename: '',
    sep: ',',
    encoding: 'utf-8',
    sheet_name: '',
    range: '',
  },
  foreign_keys: [],
  depends_on: [],
  drop_duplicates: {
    enabled: false,
    columns: [],
  },
  drop_empty_rows: {
    enabled: false,
    columns: [],
  },
  check_functional_dependency: false,
  advanced: {
    filters: [],
    unnest: null,
    append: [],
    extra_columns: undefined,
    replacements: undefined,
  },
})

const activeTab = ref('basic')

// Watch for initial tab from entity store overlay
const entityStore = useEntityStore()
watch(
  () => entityStore.overlayInitialTab,
  (tab) => {
    if (tab === 'yaml') {
      activeTab.value = 'yaml'
    } else {
      activeTab.value = 'basic'
    }
  },
  { immediate: true }
)

// Also watch props.initialTab for direct usage
watch(
  () => props.initialTab,
  (tab) => {
    if (tab === 'yaml') {
      activeTab.value = 'yaml'
    } else if (tab === 'form') {
      activeTab.value = 'basic'
    }
  },
  { immediate: true }
)

// File handling state
interface FileInfo {
  name: string
  path: string
  location: 'global' | 'local'
  size_bytes: number
  modified_at: string | number
}

const availableProjectFiles = ref<FileInfo[]>([])
const filesLoading = ref(false)
const sheetOptions = ref<string[]>([])
const sheetOptionsLoading = ref(false)
const columnsOptions = ref<string[]>([])
const columnsLoading = ref(false)

// Delimiter options for CSV
const delimiterOptions = [
  { title: 'Comma (,)', value: ',' },
  { title: 'Semicolon (;)', value: ';' },
  { title: 'Tab', value: '\t' },
  { title: 'Pipe (|)', value: '|' },
  { title: 'Space', value: ' ' },
]

// Important: `values` is a positional 2D array, so the grid column order must match the three-tier identity model.
// Fixed values grid must include: system_id, public_id (if defined), keys, and columns
const fixedValuesColumns = computed(() => {
  const result: string[] = []
  
  // Always include system_id first (required for three-tier identity)
  result.push('system_id')
  
  // Include public_id if defined (required for entities with FK children or mappings)
  if (formData.value.public_id && formData.value.public_id.trim().length > 0) {
    result.push(formData.value.public_id)
  }
  
  // Include keys (business keys)
  const keys = (formData.value.keys || []).filter((k: string) => typeof k === 'string' && k.trim().length > 0)
  result.push(...keys)
  
  // Include columns (data columns)
  const columns = (formData.value.columns || []).filter((c: string) => typeof c === 'string' && c.trim().length > 0)
  result.push(...columns)
  
  return result
})

// Can preview only in edit mode
const canPreview = computed(() => {
  return props.mode === 'edit' && formData.value.name
})

// Ag-grid project for preview
const previewColumnDefs = computed<ColDef[]>(() => {
  if (!livePreviewData.value?.columns) return []

  return livePreviewData.value.columns.map((col) => ({
    field: col.name,
    headerName: col.name,
    sortable: true,
    filter: true,
    resizable: true,
    minWidth: 40,
    flex: 1,
    cellClass: col.is_key ? 'key-column' : '',
    headerComponent: undefined,
    headerComponentParams: {
      columnInfo: col,
    },
  }))
})

const previewRowData = computed(() => {
  return livePreviewData.value?.rows || []
})

const previewDefaultColDef: ColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  minWidth: 40,
}

// Split-pane functions
function toggleSplitView() {
  // Cycle through: form -> both -> preview -> form
  if (viewMode.value === 'form') {
    viewMode.value = 'both'
  } else if (viewMode.value === 'both') {
    viewMode.value = 'preview'
  } else {
    viewMode.value = 'form'
  }

  if (viewMode.value !== 'form' && canPreview.value) {
    refreshPreview()
  }
}

function buildEntityConfigFromFormData(): Record<string, unknown> {
  /**
   * Convert form data to entity config format.
   * Shared by both handleSubmit and refreshPreview to ensure consistency.
   */
  const entityData: Record<string, unknown> = {
    type: formData.value.type,
    keys: formData.value.keys,
    // Always include columns so new entities default to an empty list instead of omitting the field
    columns: formData.value.columns,
  }

  // Always include public_id (even if null) to prevent field from being omitted
  entityData.public_id = formData.value.public_id || null

  if (formData.value.surrogate_id) {
    entityData.surrogate_id = formData.value.surrogate_id
  }

  // Always include values field for fixed type (required by backend validation)
  if (formData.value.type === 'fixed') {
    entityData.values = formData.value.values || []
  }

  if (formData.value.source) {
    entityData.source = formData.value.source
  }

  if (formData.value.type === 'sql') {
    entityData.data_source = formData.value.data_source
    entityData.query = formData.value.query
  }

  // Include file options for CSV and Excel types
  if (isFileType.value && formData.value.options.filename) {
    const options: Record<string, unknown> = {
      filename: formData.value.options.filename,
    }

    // Add location field to indicate where file is stored
    const selectedFile = availableProjectFiles.value.find(f => f.name === formData.value.options.filename)
    if (selectedFile) {
      options.location = selectedFile.location
    } else {
      // Default to global for backwards compatibility
      options.location = 'global'
    }

    if (formData.value.type === 'csv') {
      if (formData.value.options.sep) {
        options.sep = formData.value.options.sep
      }
      if (formData.value.options.encoding) {
        options.encoding = formData.value.options.encoding
      }
    } else if (isExcelType.value) {
      if (formData.value.options.sheet_name) {
        options.sheet_name = formData.value.options.sheet_name
      }
      if (formData.value.options.range) {
        options.range = formData.value.options.range
      }
    }

    entityData.options = options
  }

  // Include foreign keys if any
  if (formData.value.foreign_keys.length > 0) {
    // Transform foreign keys: extract just column values from column picker objects
    entityData.foreign_keys = formData.value.foreign_keys.map((fk: any) => ({
      entity: fk.entity,
      local_keys: Array.isArray(fk.local_keys)
        ? fk.local_keys.map((col: any) => typeof col === 'string' ? col : col.value)
        : [],
      remote_keys: Array.isArray(fk.remote_keys)
        ? fk.remote_keys.map((col: any) => typeof col === 'string' ? col : col.value)
        : [],
    }))
  }

  // Include depends_on if specified
  if (formData.value.depends_on.length > 0) {
    entityData.depends_on = formData.value.depends_on
  }

  // Include drop_duplicates if enabled
  if (formData.value.drop_duplicates.enabled) {
    if (formData.value.drop_duplicates.columns.length > 0) {
      entityData.drop_duplicates = formData.value.drop_duplicates.columns
    } else {
      entityData.drop_duplicates = true
    }
  }

  // Include drop_empty_rows if enabled
  if (formData.value.drop_empty_rows.enabled) {
    if (formData.value.drop_empty_rows.columns.length > 0) {
      entityData.drop_empty_rows = formData.value.drop_empty_rows.columns
    } else {
      entityData.drop_empty_rows = true
    }
  }

  // Include check_functional_dependency if enabled
  if (formData.value.check_functional_dependency) {
    entityData.check_functional_dependency = true
  }

  // Include advanced configuration
  if (formData.value.advanced.filters?.length) {
    entityData.filters = formData.value.advanced.filters
  }
  if (formData.value.advanced.unnest) {
    entityData.unnest = formData.value.advanced.unnest
  }
  if (formData.value.advanced.append?.length) {
    entityData.append = formData.value.advanced.append
  }
  if (formData.value.advanced.extra_columns) {
    entityData.extra_columns = formData.value.advanced.extra_columns
  }

  if (formData.value.advanced.replacements) {
    entityData.replacements = formData.value.advanced.replacements
  }

  return entityData
}

async function refreshPreview() {
  if (!canPreview.value) return

  previewError.value = null
  
  // Convert form data to entity config format (same as handleSubmit)
  const entityConfig = buildEntityConfigFromFormData()
  
  // Pass converted entity config to preview unsaved changes
  await previewEntity(props.projectName, formData.value.name, previewLimit.value, entityConfig)

  if (livePreviewError.value) {
    previewError.value = livePreviewError.value
  }
}

function formatRefreshTime(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  return date.toLocaleTimeString()
}

// Fetch project files based on entity type
async function fetchProjectFiles() {
  if (!isFileType.value) {
    availableProjectFiles.value = []
    return
  }

  filesLoading.value = true
  try {
    const extensions = getFileExtensions()
    // Build query params - backend expects 'ext' parameter for each extension
    const queryParams = extensions.map(ext => `ext=${ext}`).join('&')
    
    // Include project-specific files if we have a current project
    let url = `/api/v1/data-sources/files?${queryParams}`
    if (projectStore.currentProjectName) {
      url += `&project_name=${encodeURIComponent(projectStore.currentProjectName)}`
    }
    
    const response = await fetch(url)
    if (response.ok) {
      const files: FileInfo[] = await response.json()
      availableProjectFiles.value = files
    }
  } catch (err: any) {
    console.error('Failed to fetch project files:', err)
    const message = err.message || 'Unknown error'
    showError(`Failed to load available files: ${message}`)
  } finally {
    filesLoading.value = false
  }
}

async function fetchSheetOptions() {
  sheetOptionsLoading.value = true
  sheetOptions.value = []
  columnsOptions.value = []

  const filename = formData.value.options.filename
  if (!isExcelType.value || !filename) {
    sheetOptionsLoading.value = false
    return
  }

  try {
    // Find the file to get its location
    const fileInfo = availableProjectFiles.value.find(f => f.name === filename)
    const location = fileInfo?.location || 'global'
    
    const meta = await api.excelMetadata.fetch(filename, location)
    sheetOptions.value = meta.sheets || []

    if (!formData.value.options.sheet_name && sheetOptions.value.length > 0) {
      formData.value.options.sheet_name = sheetOptions.value[0] || ''
    }

    if (formData.value.options.sheet_name) {
      await fetchColumns()
    }
  } catch (err: any) {
    console.error('Failed to fetch sheet names', err)
    const message = err.response?.data?.detail || err.message || 'Unknown error'
    showError(`Failed to load Excel metadata: ${message}`)
  } finally {
    sheetOptionsLoading.value = false
  }
}

async function fetchColumns() {
  columnsLoading.value = true
  columnsOptions.value = []
  formData.value.columns = []

  const filename = formData.value.options.filename
  const sheet = formData.value.options.sheet_name
  const range = formData.value.options.range
  if (!isExcelType.value || !filename || !sheet) {
    columnsLoading.value = false
    return
  }

  try {
    // Find the file to get its location
    const fileInfo = availableProjectFiles.value.find(f => f.name === filename)
    const location = fileInfo?.location || 'global'
    
    const meta = await api.excelMetadata.fetch(filename, location, sheet, range)
    columnsOptions.value = meta.columns || []
    if (columnsOptions.value.length > 0) {
      formData.value.columns = [...columnsOptions.value]
    }
  } catch (err: any) {
    console.error('Failed to fetch columns', err)
    const message = err.response?.data?.detail || err.message || 'Unknown error'
    showError(`Failed to load Excel columns: ${message}`)
  } finally {
    columnsLoading.value = false
  }
}

async function handleSheetSelection() {
  columnsOptions.value = []
  formData.value.columns = []
  await fetchColumns()
}

function getColumnsFromEntity(entityName: string | null): string[] {
  if (!entityName) return []
  const sourceEntity = entities.value.find((e) => e.name === entityName)
  if (!sourceEntity) return []

  const sourceColumns = Array.isArray((sourceEntity as any)?.entity_data?.columns)
    ? (sourceEntity as any).entity_data.columns
    : []
  const sourceKeys = Array.isArray((sourceEntity as any)?.entity_data?.keys)
    ? (sourceEntity as any).entity_data.keys
    : []

  const combined = Array.from(new Set([...sourceKeys, ...sourceColumns]))
  return combined.filter((c) => c !== 'system_id')
}

function hydrateColumnsFromSource() {
  if (formData.value.type !== 'entity') return
  const colsFromSource = getColumnsFromEntity(formData.value.source)
  const existing = formData.value.columns || []
  // Ensure saved selections stay visible even if source metadata is not yet available
  columnsOptions.value = Array.from(new Set([...existing, ...colsFromSource]))
  console.debug('[EntityFormDialog] Hydrated columns from source:', {
    source: formData.value.source,
    colsFromSource,
    existing,
    columnsOptions: columnsOptions.value
  })
}

function getFileExtensions(): string[] {
  if (formData.value.type === 'csv') return ['csv']
  if (formData.value.type === 'xlsx') return ['xlsx', 'xls']
  if (formData.value.type === 'openpyxl') return ['xlsx']
  return []
}

// Watch for changes and auto-refresh if enabled
watch(
  formData,
  () => {
    if (autoRefreshEnabled.value && viewMode.value !== 'form' && canPreview.value) {
      // Convert form data to entity config before previewing
      const entityConfig = buildEntityConfigFromFormData()
      debouncedPreviewEntity(props.projectName, formData.value.name, 100, entityConfig)
    }
  },
  { deep: true }
)

// Watch for source entity changes (entity type) to hydrate columns
watch(
  () => formData.value.source,
  (newSource, oldSource) => {
    if (formData.value.type !== 'entity') return

    if (newSource && newSource !== oldSource) {
      // Only clear selections when the user actually changes the source
      if (oldSource !== undefined && oldSource !== null) {
        formData.value.columns = []
      }
      hydrateColumnsFromSource()
    }

    // Avoid clearing during initial hydration (oldSource undefined)
    if (!newSource && oldSource !== undefined) {
      columnsOptions.value = []
      formData.value.columns = []
    }
  },
  { immediate: true }
)

// Watch for Excel filename changes to refresh sheet list
watch(
  () => formData.value.options.filename,
  async (newFilename, oldFilename) => {
    if (!isExcelType.value) return

    if (newFilename && newFilename !== oldFilename) {
      // Only clear sheet_name if it's not already set (initial hydration case)
      // If sheet_name is already set, preserve it and just refresh metadata
      if (!formData.value.options.sheet_name) {
        columnsOptions.value = []
      }
      await fetchSheetOptions()
    }

    if (!newFilename) {
      sheetOptions.value = []
      columnsOptions.value = []
    }
  }
)

// Watch for sheet selection to load columns
watch(
  () => formData.value.options.sheet_name,
  async (newSheet, oldSheet) => {
    if (!isExcelType.value) return

    // Fetch columns on sheet change, but preserve columns list during initial hydration
    // (oldSheet === undefined means watcher fired for the first time during load)
    if (newSheet && newSheet !== oldSheet && oldSheet !== undefined) {
      columnsOptions.value = []
      await fetchColumns()
    } else if (newSheet && oldSheet === undefined) {
      // Initial hydration: fetch columns without clearing
      await fetchColumns()
    }

    if (!newSheet) {
      columnsOptions.value = []
    }
  }
)

// Watch for formData changes to trigger validation (handles FK editor changes)
watch(
  formData,
  () => {
    // Trigger form validation when any formData changes
    // This ensures the save button is enabled when FKs or other non-form fields change
    nextTick(async () => {
      const result = await formRef.value?.validate()
      // Explicitly update formValid to enable save button for changes outside v-form
      if (result?.valid) {
        formValid.value = true
      }
    })
  },
  { deep: true }
)

// Watch for entity type changes to fetch appropriate files
watch(() => formData.value.type, async (newType, oldType) => {
  // Clear data source and query when switching away from SQL
  if (newType !== 'sql') {
    formData.value.data_source = ''
    formData.value.query = ''
  }

  // Clear source when switching away from entity
  if (newType !== 'entity') {
    formData.value.source = null
  }

  // Clear or initialize options based on type
  if (!isFileType.value) {
    formData.value.options = {
      filename: '',
      sep: ',',
      encoding: 'utf-8',
      sheet_name: '',
      range: '',
    }
  }

  // Fetch files when switching to a file type
  const wasFileType = oldType && ['csv', 'xlsx', 'openpyxl'].includes(oldType)
  if (isFileType.value && !wasFileType) {
    await fetchProjectFiles()
  }

  // Hydrate columns from source entity when switching to entity type
  if (newType === 'entity') {
    hydrateColumnsFromSource()
  }

  if (isExcelType.value && formData.value.options.filename) {
    await fetchSheetOptions()
  } else {
    sheetOptions.value = []
    columnsOptions.value = []
  }
})

// Keyboard shortcut for split view toggle (Ctrl+Shift+P)
function handleKeyPress(e: KeyboardEvent) {
  if (e.ctrlKey && e.shiftKey && e.key === 'P' && dialogModel.value && props.mode === 'edit') {
    e.preventDefault()
    toggleSplitView()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyPress)

  // Fetch project files if editing a file type entity
  if (props.mode === 'edit' && isFileType.value) {
    fetchProjectFiles()
  }

  if (isExcelType.value && formData.value.options.filename) {
    fetchSheetOptions()
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyPress)
})

// Computed
const dialogModel = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const entityTypeOptions = [
  { title: 'Data (Derived)', value: 'entity', subtitle: 'Derive from another entity' },
  { title: 'SQL Query', value: 'sql', subtitle: 'Execute SQL against database' },
  { title: 'Fixed Values', value: 'fixed', subtitle: 'Hard-coded values' },
  { title: 'CSV File', value: 'csv', subtitle: 'Load from CSV file' },
  { title: 'Excel File (Pandas)', value: 'xlsx', subtitle: 'Load Excel with pandas' },
  { title: 'Excel File (OpenPyXL)', value: 'openpyxl', subtitle: 'Load Excel with OpenPyXL (supports ranges)' },
]

const availableSourceEntities = computed(() => {
  return entities.value.filter((e) => e.name !== formData.value.name).map((e) => e.name)
})

const availableDataSources = computed(() => {
  // Get entity source names from project's options.data_sources (e.g., "arbodat_data", "sead")
  const dataSources = projectStore.selectedProject?.options?.data_sources
  if (dataSources && typeof dataSources === 'object') {
    return Object.keys(dataSources)
  }
  return []
})

// File type computed properties
const isFileType = computed(() => {
  return ['csv', 'xlsx', 'openpyxl'].includes(formData.value.type)
})

const isExcelType = computed(() => {
  return ['xlsx', 'openpyxl'].includes(formData.value.type)
})

const availableColumns = computed(() => columnsOptions.value)

const availableColumnsForUnnest = computed(() => {
  const keys = formData.value.keys || []
  const columns = formData.value.columns || []
  const options = columnsOptions.value.length > 0 ? columnsOptions.value : columns
  const combined = Array.from(new Set([...keys, ...options]))
  return combined.filter((c) => c && c !== 'system_id')
})

// const getFileExtensionHint = computed(() => {
//   if (formData.value.type === 'csv') return 'Select a .csv file from the projects directory'
//   if (formData.value.type === 'xlsx') return 'Select a .xlsx or .xls file from the projects directory'
//   if (formData.value.type === 'openpyxl') return 'Select a .xlsx file from the projects directory'
//   return ''
// })

// Validation context for YAML intelligence
const validationContext = computed<ValidationContext>(() => ({
  entityNames: entities.value
    .filter((e) => e.name !== formData.value.name) // Exclude self
    .map((e) => e.name),
  dataSourceNames: availableDataSources.value,
  currentEntityName: formData.value.name,
}))

// Validation rules
const requiredRule = [
  (v: unknown) => {
    if (Array.isArray(v)) return v.length > 0 || 'This field is required'
    return !!v || 'This field is required'
  },
]

const nameRules = [
  (v: string) => !!v || 'Entity name is required',
  (v: string) => v.length >= 2 || 'Name must be at least 2 characters',
  (v: string) => /^[a-z][a-z0-9_]*$/.test(v) || 'Name must be lowercase snake_case',
  (v: string) => {
    if (props.mode === 'edit') return true
    return !entities.value.some((e) => e.name === v) || 'Entity name already exists'
  },
]

const publicIdRules = [
  (v: string) => !!v || 'Public ID is required',
  (v: string) => v.endsWith('_id') || 'Public ID must end with _id',
  (v: string) => /^[a-z][a-z0-9_]*_id$/.test(v) || 'Public ID must be lowercase snake_case ending with _id',
]

// YAML Editor Functions
function formDataToYaml(): string {
  // Reuse the shared conversion logic
  const entityData = buildEntityConfigFromFormData()
  
  // Add fields that are needed for YAML display but not API calls
  const yamlData: Record<string, any> = {
    name: formData.value.name,
    ...entityData,
  }
  
  // Always show system_id in YAML for user visibility (even though it's implicit in backend)
  yamlData.system_id = 'system_id'
  
  // Move name to the top for better YAML readability
  const orderedData: Record<string, any> = {
    name: yamlData.name,
    type: yamlData.type,
    system_id: yamlData.system_id,
  }
  
  // Copy remaining fields
  Object.keys(yamlData).forEach(key => {
    if (key !== 'name' && key !== 'type' && key !== 'system_id') {
      orderedData[key] = yamlData[key]
    }
  })

  return yaml.dump(orderedData, { indent: 2, lineWidth: -1 })
}

function yamlToFormData(yamlString: string): boolean {
  try {
    const data = yaml.load(yamlString) as Record<string, any>

    const dropDuplicates = data.drop_duplicates
    const dropDuplicatesData = {
      enabled: dropDuplicates !== undefined && dropDuplicates !== null,
      columns: Array.isArray(dropDuplicates) ? dropDuplicates : [],
    }

    const dropEmptyRows = data.drop_empty_rows
    const dropEmptyRowsData = {
      enabled: dropEmptyRows !== undefined && dropEmptyRows !== null,
      columns: Array.isArray(dropEmptyRows) ? dropEmptyRows : [],
    }

    formData.value = {
      name: data.name || formData.value.name,
      type: data.type || 'entity',
      system_id: 'system_id',  // Always standardized
      public_id: data.public_id || data.surrogate_id || '',  // Migrate surrogate_id → public_id
      surrogate_id: data.surrogate_id || '',  // Keep for backward compat
      keys: Array.isArray(data.keys) ? data.keys : [],
      columns: Array.isArray(data.columns) ? data.columns : [],
      values: Array.isArray(data.values) ? data.values : [],
      source: data.source || null,
      data_source: data.data_source || '',
      query: data.query || '',
      options: {
        filename: data.options?.filename || '',
        sep: data.options?.sep || ',',
        encoding: data.options?.encoding || 'utf-8',
        sheet_name: data.options?.sheet_name || '',
        range: data.options?.range || '',
      },
      foreign_keys: Array.isArray(data.foreign_keys) ? data.foreign_keys : [],
      depends_on: Array.isArray(data.depends_on) ? data.depends_on : [],
      drop_duplicates: dropDuplicatesData,
      drop_empty_rows: dropEmptyRowsData,
      check_functional_dependency: data.check_functional_dependency || false,
      advanced: {
        filters: Array.isArray(data.filters) ? data.filters : [],
        unnest: data.unnest || null,
        append: Array.isArray(data.append) ? data.append : [],
        extra_columns: data.extra_columns || undefined,
        replacements: data.replacements || undefined,
      },
    }

    yamlError.value = null
    return true
  } catch (err) {
    yamlError.value = err instanceof Error ? err.message : 'Invalid YAML'
    return false
  }
}

function handleYamlValidation(isValid: boolean, error?: string) {
  yamlValid.value = isValid
  if (!isValid && error) {
    yamlError.value = error
  }
}

async function handleYamlChange(value: string) {
  // Auto-sync YAML to form data when valid
  if (yamlValid.value) {
    const success = yamlToFormData(value)
    if (success) {
      // Explicitly trigger validation after YAML changes
      // This ensures Save button is enabled when editing via YAML tab
      await nextTick()
      const result = await formRef.value?.validate()
      if (result?.valid) {
        formValid.value = true
      }
    }
  }
}

// Methods
async function handleSubmit() {
  if (!formValid.value || loading.value) return  // Prevent double-submission

  const { valid } = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  error.value = null

  try {
    // Use shared function to build entity config
    const entityData = buildEntityConfigFromFormData()

    if (props.mode === 'create') {
      await create({
        name: formData.value.name,
        entity_data: entityData,
      })
      emit('saved', formData.value.name)
      // Keep dialog open after creating (user can choose "Save & Close" if they want to close)
      // Show success indicator
      showSaveSuccess.value = true
      if (saveSuccessTimeout) clearTimeout(saveSuccessTimeout)
      saveSuccessTimeout = setTimeout(() => {
        showSaveSuccess.value = false
      }, 3000)
    } else {
      await update(formData.value.name, {
        entity_data: entityData,
      })
      // Keep dialog open after saving in edit mode
      emit('saved', formData.value.name)
      
      // Show success indicator
      showSaveSuccess.value = true
      if (saveSuccessTimeout) clearTimeout(saveSuccessTimeout)
      saveSuccessTimeout = setTimeout(() => {
        showSaveSuccess.value = false
      }, 3000)
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to save entity'
  } finally {
    loading.value = false
  }
}

async function handleSubmitAndClose() {
  if (loading.value) return  // Prevent double-submission
  
  loading.value = true
  error.value = null

  try {
    const entityData = buildEntityConfigFromFormData()
    
    if (props.mode === 'create') {
      await create({
        name: formData.value.name,
        entity_data: entityData,
      })
    } else {
      await update(formData.value.name, {
        entity_data: entityData,
      })
    }
    
    emit('saved', formData.value.name)
    handleClose()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to save entity'
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  handleClose()
}

function handleClose() {
  error.value = null
  showSaveSuccess.value = false
  if (saveSuccessTimeout) {
    clearTimeout(saveSuccessTimeout)
    saveSuccessTimeout = null
  }
  formRef.value?.reset()
  dialogModel.value = false
}

function handleMaterialized() {
  // Entity was materialized - reload to get updated state
  showMaterializeDialog.value = false

  // Reload entity to update currentEntity with materialized flag
  if (props.entity?.name) {
    loading.value = true
    api.entities.get(props.projectName, props.entity.name)
      .then(freshEntity => {
        currentEntity.value = freshEntity
        formData.value = buildFormDataFromEntity(freshEntity)
        yamlContent.value = formDataToYaml()
      })
      .catch(err => {
        console.error('Failed to reload after materialization:', err)
        const message = err.response?.data?.detail || err.message || 'Unknown error'
        showError(`Failed to reload entity after materialization: ${message}`)
      })
      .finally(() => loading.value = false)
  }

  // Notify parent to refresh entity list
  if (props.entity?.name) {
    emit('saved', props.entity.name)
  }
}

function handleUnmaterialized(unmaterializedEntities: string[]) {
  // Entities were unmaterialized - reload to get updated state
  showUnmaterializeDialog.value = false

  // Reload entity to update currentEntity (remove materialized flag)
  if (props.entity?.name) {
    loading.value = true
    api.entities.get(props.projectName, props.entity.name)
      .then(freshEntity => {
        currentEntity.value = freshEntity
        formData.value = buildFormDataFromEntity(freshEntity)
        yamlContent.value = formDataToYaml()
      })
      .catch(err => {
        console.error('Failed to reload after unmaterialization:', err)
        const message = err.response?.data?.detail || err.message || 'Unknown error'
        showError(`Failed to reload entity after unmaterialization: ${message}`)
      })
      .finally(() => loading.value = false)
  }

  // Notify parent to refresh entity list
  if (props.entity?.name) {
    emit('saved', props.entity.name)
  }

  // Log unmaterialized entities
  if (unmaterializedEntities.length > 1) {
    console.log(`Unmaterialized ${unmaterializedEntities.length} entities:`, unmaterializedEntities)
  }
}

function buildFormDataFromEntity(entity: EntityResponse): FormData {
  const dropDuplicates = entity.entity_data.drop_duplicates
  const dropEmptyRows = entity.entity_data.drop_empty_rows

  return {
    name: entity.name,
    type: (entity.entity_data.type as string) || 'entity',
    system_id: 'system_id',  // Always standardized
    public_id: (entity.entity_data.public_id as string) || (entity.entity_data.surrogate_id as string) || '',  // Migrate
    surrogate_id: (entity.entity_data.surrogate_id as string) || '',  // Backward compat
    keys: (entity.entity_data.keys as string[]) || [],
    columns: (entity.entity_data.columns as string[]) || [],
    values: (entity.entity_data.values as any[][]) || [],
    source: (entity.entity_data.source as string) || null,
    data_source: (entity.entity_data.data_source as string) || '',
    query: (entity.entity_data.query as string) || '',
    options: {
      filename: (entity.entity_data.options as any)?.filename || '',
      sep: (entity.entity_data.options as any)?.sep || ',',
      encoding: (entity.entity_data.options as any)?.encoding || 'utf-8',
      sheet_name: (entity.entity_data.options as any)?.sheet_name || '',
      range: (entity.entity_data.options as any)?.range || '',
    },
    foreign_keys: (entity.entity_data.foreign_keys as any[]) || [],
    depends_on: (entity.entity_data.depends_on as string[]) || [],
    drop_duplicates: {
      enabled: dropDuplicates !== undefined && dropDuplicates !== null,
      columns: Array.isArray(dropDuplicates) ? dropDuplicates : [],
    },
    drop_empty_rows: {
      enabled: dropEmptyRows !== undefined && dropEmptyRows !== null,
      columns: Array.isArray(dropEmptyRows) ? dropEmptyRows : [],
    },
    check_functional_dependency: (entity.entity_data.check_functional_dependency as boolean) || false,
    advanced: {
      filters: (entity.entity_data.filters as any[]) || [],
      unnest: entity.entity_data.unnest || null,
      append: (entity.entity_data.append as any[]) || [],
      extra_columns: (entity.entity_data.extra_columns as Record<string, string | null>) || undefined,
    },
  }
}

function buildDefaultFormData(): FormData {
  return {
    name: '',
    type: 'entity',
    system_id: 'system_id',  // Always standardized
    public_id: '',
    surrogate_id: '',  // Backward compat
    keys: [],
    columns: [],
    values: [],
    source: null,
    data_source: '',
    query: '',
    options: {
      filename: '',
      sep: ',',
      encoding: 'utf-8',
      sheet_name: '',
      range: '',
    },
    foreign_keys: [],
    depends_on: [],
    drop_duplicates: {
      enabled: false,
      columns: [],
    },
    drop_empty_rows: {
      enabled: false,
      columns: [],
    },
    check_functional_dependency: false,
    advanced: {
      filters: [],
      unnest: null,
      append: [],
      extra_columns: undefined,
    },
  }
}

// Note: Entity loading now handled in modelValue watcher below
// This ensures we always fetch fresh data from the API when opening the dialog

// Reset form and fetch fresh entity data when dialog opens or entity changes
watch(
  [() => props.modelValue, () => props.entity?.name, () => props.mode],
  async ([isOpen, entityName, mode]) => {
    // Trigger reset when dialog opens in either mode:
    // - Create mode: always reset (no entity name required)
    // - Edit mode: reset when entity name is available
    if (isOpen && (mode === 'create' || entityName)) {
      console.log('[EntityFormDialog] Dialog opening/entity changed, props:', {
        mode: mode,
        entityName: entityName,
        hasEntity: !!props.entity,
        projectName: props.projectName
      })

      // Reset UI state
      error.value = null
      formRef.value?.resetValidation()
      suggestions.value = null
      showSuggestions.value = false
      yamlError.value = null
      clearPreview()
      previewError.value = null
      viewMode.value = 'form'  // Always reset to form view

      // Load entity data for edit mode
      if (mode === 'edit' && entityName) {
        // Use entity from props (already fresh from reactive store)
        // Only fetch from API if props.entity is missing (defensive coding)
        if (props.entity) {
          console.log('[EntityFormDialog] Using entity from props (reactive store):', entityName)
          currentEntity.value = props.entity
          formData.value = buildFormDataFromEntity(props.entity)
          yamlContent.value = formDataToYaml()

          // Hydrate columns for entity type after form data is loaded
          if (formData.value.type === 'entity') {
            hydrateColumnsFromSource()
          }
        } else {
          // Fallback: fetch from API if entity not provided (shouldn't happen in normal flow)
          loading.value = true
          console.warn('[EntityFormDialog] Entity not in props, fetching from API:', entityName)
          try {
            const freshEntity = await api.entities.get(props.projectName, entityName)
            console.log('[EntityFormDialog] API response received for:', freshEntity.name)
            currentEntity.value = freshEntity
            formData.value = buildFormDataFromEntity(freshEntity)
            yamlContent.value = formDataToYaml()

            // Hydrate columns for entity type after form data is loaded
            if (formData.value.type === 'entity') {
              hydrateColumnsFromSource()
            }
          } catch (err) {
            error.value = err instanceof Error ? err.message : 'Failed to load entity data'
            console.error('Failed to fetch entity data:', err)
          } finally {
            loading.value = false
          }
        }
      } else if (mode === 'create') {
        // Create mode: use default form data
        currentEntity.value = null
        formData.value = buildDefaultFormData()
        yamlContent.value = ''
      }
    }
  },
  { immediate: true }
)

// Sync form to YAML when switching to YAML tab
watch(activeTab, (newTab, oldTab) => {
  if (newTab === 'yaml' && oldTab !== 'yaml') {
    // Switching TO yaml tab - convert form data to YAML
    yamlContent.value = formDataToYaml()
    yamlError.value = null
  } else if (oldTab === 'yaml' && newTab !== 'yaml') {
    // Switching FROM yaml tab - validate and sync to form
    if (yamlValid.value) {
      yamlToFormData(yamlContent.value)
    }
  }
})

// Fetch suggestions when columns change (debounced)
let suggestionTimeout: NodeJS.Timeout | null = null
watchEffect(() => {
  if (!fkSuggestionsEnabled.value) {
    if (suggestions.value || showSuggestions.value) {
      suggestions.value = null
      showSuggestions.value = false
    }
    return
  }

  if (props.mode === 'create' && formData.value.name && formData.value.columns.length > 0) {
    // Clear existing timeout
    if (suggestionTimeout) {
      clearTimeout(suggestionTimeout)
    }

    // Debounce suggestions fetch
    suggestionTimeout = setTimeout(async () => {
      try {
        const allEntities = entities.value.map((e) => ({
          name: e.name,
          columns: (e.entity_data.columns as string[]) || [],
        }))

        // Add current entity being created
        allEntities.push({
          name: formData.value.name,
          columns: formData.value.columns,
        })

        const result = await getSuggestionsForEntity(
          {
            name: formData.value.name,
            columns: formData.value.columns,
          },
          allEntities
        )

        suggestions.value = result
        showSuggestions.value = true
      } catch (err) {
        console.error('Failed to fetch suggestions:', err)
      }
    }, 1000) // 1 second debounce
  }
})

// Handle suggestion acceptance
function handleAcceptForeignKey(fk: ForeignKeySuggestion) {
  // Add foreign key to form data
  const newFk = {
    entity: fk.remote_entity,
    local_keys: fk.local_keys,
    remote_keys: fk.remote_keys,
    how: 'left', // Default join type
  }

  // Check if FK already exists
  const exists = formData.value.foreign_keys.some(
    (existing) =>
      existing.entity === newFk.entity && JSON.stringify(existing.local_keys) === JSON.stringify(newFk.local_keys)
  )

  if (!exists) {
    formData.value.foreign_keys.push(newFk)
  }
}

function handleRejectForeignKey(fk: ForeignKeySuggestion) {
  // Just log for now - user rejected this suggestion
  console.log('Rejected FK suggestion:', fk)
}

function handleAcceptDependency(dep: DependencySuggestion) {
  // Dependencies would be handled by the backend during processing
  // For now, just log
  console.log('Accepted dependency suggestion:', dep)
}

function handleRejectDependency(dep: DependencySuggestion) {
  console.log('Rejected dependency suggestion:', dep)
}
</script>

<style scoped>
/* System ID field - read-only with dimmed text and subtle background */
.system-id-field :deep(input) {
  color: rgba(var(--v-theme-on-surface), 0.5) !important;
  cursor: not-allowed;
}

.system-id-field :deep(.v-field) {
  pointer-events: none;
  background-color: rgba(var(--v-theme-on-surface), 0.03) !important;
}

.system-id-field :deep(.v-field__outline) {
  opacity: 0.5;
}

/* Dialog content height management */
.dialog-content {
  min-height: 600px;
  max-height: calc(90vh - 120px);
  overflow-y: auto;
}

.form-content {
  min-height: 600px;
}

/* Split-pane layout */
.split-container {
  height: calc(100vh - 180px);
  overflow: hidden;
}

.split-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* When in preview-only mode, hide form panel and make preview 100% */
.split-layout[data-view-mode="preview"] .form-panel {
  display: none;
}

.split-layout[data-view-mode="preview"] .preview-panel {
  flex: 1 1 100%;
}

.form-panel {
  flex: 0 0 50%;
  overflow-y: auto;
  padding: 14px;
  border-right: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.preview-panel {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: rgba(var(--v-theme-surface-variant), 0.3);
}

.preview-header {
  flex: 0 0 auto;
  background: rgb(var(--v-theme-surface));
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.preview-content {
  flex: 1 1 auto;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.preview-table-container {
  flex: 1 1 auto;
  overflow: hidden;
  position: relative;
}

/* Ag-grid preview styles */
.preview-table-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  overflow: hidden;
}

.preview-grid-wrapper {
  flex: 1;
  overflow: auto;
  height: 100%;
  width: 100%;
}

.preview-ag-grid {
  font-size: 11px;
  --ag-background-color: rgb(var(--v-theme-background)) !important;
  --ag-foreground-color: rgb(var(--v-theme-on-background)) !important;
  --ag-header-foreground-color: rgb(var(--v-theme-on-surface)) !important;
  --ag-header-background-color: rgb(var(--v-theme-surface)) !important;
  --ag-odd-row-background-color: rgba(var(--v-theme-on-surface), 0.03) !important;
  --ag-row-hover-color: rgba(var(--v-theme-primary), 0.08) !important;
  --ag-border-color: rgba(var(--v-theme-on-surface), 0.12) !important;
  --ag-cell-horizontal-border: solid rgba(var(--v-theme-on-surface), 0.08) !important;
}

.preview-ag-grid :deep(.ag-root-wrapper) {
  border: none;
  background: rgb(var(--v-theme-background)) !important;
  color: rgb(var(--v-theme-on-background)) !important;
}

.preview-ag-grid :deep(.ag-header) {
  background: rgb(var(--v-theme-surface)) !important;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12) !important;
}

.preview-ag-grid :deep(.ag-header-cell) {
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface)) !important;
  background: rgb(var(--v-theme-surface)) !important;
}

.preview-ag-grid :deep(.ag-header-cell-label) {
  color: rgb(var(--v-theme-on-surface)) !important;
}

.preview-ag-grid :deep(.ag-cell) {
  padding: 4px 8px;
  font-size: 11px;
  line-height: 20px;
  color: rgb(var(--v-theme-on-background)) !important;
  border-color: rgba(var(--v-theme-on-surface), 0.08) !important;
  background: transparent;
}

.preview-ag-grid :deep(.ag-row) {
  color: rgb(var(--v-theme-on-background)) !important;
  background: transparent;
}

.preview-ag-grid :deep(.ag-row-odd) {
  background: rgba(var(--v-theme-on-surface), 0.03) !important;
}

.preview-ag-grid :deep(.ag-row-even) {
  background: transparent !important;
}

.preview-ag-grid :deep(.ag-row-hover) {
  background: rgba(var(--v-theme-primary), 0.08) !important;
}

.preview-ag-grid :deep(.key-column) {
  font-weight: 500;
  background: rgba(var(--v-theme-warning), 0.05) !important;
  color: rgb(var(--v-theme-on-background)) !important;
}

/* Dark mode support for ag-grid */

.striped-row {
  background: rgba(var(--v-theme-on-surface), 0.05);
}

/* Compact form styling with smaller font size */
.compact-form {
  margin-top: 8px;
}

/* Consistent spacing for all form rows */
.form-row {
  margin-bottom: 4px;
}

:deep(.v-field__input) {
  font-size: 12px;
  padding-top: 2px;
  padding-bottom: 2px;
}

:deep(.v-select__selection-text) {
  font-size: 12px;
}

:deep(.v-autocomplete .v-field__input) {
  font-size: 12px;
  padding-top: 2px;
  padding-bottom: 2px;
}

:deep(.v-chip) {
  min-height: 10px;
  height: 18px;
  font-size: 11px;
}

/* Reduce field padding */
:deep(.v-field) {
  --v-field-padding-top: 4px;
  --v-field-padding-bottom: 4px;
}

:deep(.v-field__field) {
  padding-top: 4px;
  padding-bottom: 4px;
}

:deep(.v-field--variant-outlined .v-field__outline) {
  --v-field-border-opacity: 0.3;
}

/* Remove all default Vuetify row/col margins and ensure left alignment */
.form-row :deep(.v-row) {
  margin: 0 !important;
}

.form-row :deep(.v-col) {
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}

/* Reduce checkbox font size */
:deep(.v-checkbox .v-label) {
  font-size: 12px;
}
</style>
