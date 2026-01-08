<template>
  <v-container fluid class="fill-height">
    <v-row>
      <v-col cols="12">
        <v-card elevation="0">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon class="mr-3" size="large" color="primary">mdi-book-open-variant</v-icon>
            <span class="text-h5">User Guide</span>
            <v-spacer />
            <!-- Quick navigation -->
            <v-chip-group v-model="selectedSection" mandatory class="mr-2">
              <v-chip
                v-for="section in sections"
                :key="section.id"
                :value="section.id"
                variant="outlined"
                size="small"
                @click="scrollToSection(section.id)"
              >
                {{ section.title }}
              </v-chip>
            </v-chip-group>
            <!-- External link -->
            <v-btn
              href="https://github.com/humlab-sead/sead_shape_shifter/blob/main/docs/USER_GUIDE.md"
              target="_blank"
              rel="noopener noreferrer"
              variant="outlined"
              size="small"
            >
              <v-icon start size="small">mdi-open-in-new</v-icon>
              View on GitHub
            </v-btn>
          </v-card-title>

          <v-divider />

          <v-card-text class="pa-6">
            <!-- Loading state -->
            <v-skeleton-loader v-if="loading" type="article, article, article" />

            <!-- Error state -->
            <v-alert v-else-if="error" type="error" variant="tonal" class="mb-4">
              <div class="d-flex align-center">
                <v-icon class="mr-2">mdi-alert-circle</v-icon>
                <div>
                  <div class="font-weight-bold">Failed to load user guide</div>
                  <div class="text-caption mt-1">{{ error }}</div>
                </div>
              </div>
            </v-alert>

            <!-- Rendered markdown content -->
            <div
              v-else
              ref="contentRef"
              class="markdown-content"
              v-html="renderedContent"
            ></div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useHelp } from '@/composables/useHelp'

// Quick navigation sections
const sections = [
  { id: '1-introduction', title: 'Introduction' },
  { id: '2-getting-started', title: 'Getting Started' },
  { id: '3-working-with-configurations', title: 'Projects' },
  { id: '4-managing-entities', title: 'Entities' },
  { id: '5-validation', title: 'Validation' },
  { id: '6-auto-fix-features', title: 'Auto-Fix' },
  { id: '7-execute-workflow', title: 'Execute' },
  { id: '8-tips--best-practices', title: 'Best Practices' },
  { id: '9-troubleshooting', title: 'Troubleshooting' },
  { id: '10-faq', title: 'FAQ' },
]

const selectedSection = ref('1-introduction')
const contentRef = ref<HTMLElement | null>(null)

const { renderedContent, loading, error, loadHelp } = useHelp()

onMounted(async () => {
  await loadHelp('USER_GUIDE')
})

function scrollToSection(sectionId: string) {
  if (!contentRef.value) return

  const heading = contentRef.value.querySelector(`#${sectionId}`)
  if (heading) {
    heading.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}
</script>

<style scoped>
.markdown-content {
  max-width: 900px;
  margin: 0 auto;
  line-height: 1.7;
  font-size: 15px;
}

.markdown-content :deep(h1) {
  font-size: 2.5em;
  font-weight: 600;
  margin-top: 1.5em;
  margin-bottom: 0.75em;
  padding-bottom: 0.3em;
  border-bottom: 2px solid rgba(var(--v-theme-primary), 0.2);
}

.markdown-content :deep(h2) {
  font-size: 2em;
  font-weight: 600;
  margin-top: 1.5em;
  margin-bottom: 0.75em;
  padding-bottom: 0.25em;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.markdown-content :deep(h3) {
  font-size: 1.5em;
  font-weight: 600;
  margin-top: 1.25em;
  margin-bottom: 0.5em;
}

.markdown-content :deep(h4) {
  font-size: 1.25em;
  font-weight: 600;
  margin-top: 1em;
  margin-bottom: 0.5em;
}

.markdown-content :deep(p) {
  margin-bottom: 1em;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 1em;
  padding-left: 2em;
}

.markdown-content :deep(li) {
  margin-bottom: 0.5em;
}

.markdown-content :deep(code) {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
  font-size: 0.9em;
}

.markdown-content :deep(pre) {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 1.25em;
  border-radius: 6px;
  overflow-x: auto;
  margin-bottom: 1em;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.markdown-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
  border-radius: 0;
  font-size: 0.875em;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid rgba(var(--v-theme-primary), 0.5);
  padding-left: 1em;
  margin-left: 0;
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-style: italic;
}

.markdown-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  padding: 8px 12px;
  text-align: left;
}

.markdown-content :deep(th) {
  background-color: rgba(var(--v-theme-primary), 0.08);
  font-weight: 600;
}

.markdown-content :deep(a) {
  color: rgb(var(--v-theme-primary));
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

.markdown-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 1em 0;
}

.markdown-content :deep(hr) {
  border: 0;
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  margin: 2em 0;
}

/* Checkbox list styling */
.markdown-content :deep(input[type='checkbox']) {
  margin-right: 0.5em;
}

/* Emoji support */
.markdown-content :deep(.emoji) {
  height: 1.2em;
  vertical-align: text-bottom;
}
</style>
