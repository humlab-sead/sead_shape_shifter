<template>
  <v-container fluid class="pa-6 whats-new-view">
    <v-row>
      <v-col cols="12">
        <v-card elevation="0" class="mb-6">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon class="mr-3" size="large" color="primary">mdi-new-box</v-icon>
            <div>
              <div class="text-h5">What's New</div>
              <div class="text-body-2 text-medium-emphasis">Recent user-visible updates and workflow improvements.</div>
            </div>
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-6">
            <v-skeleton-loader v-if="loading" type="article, article, article" />

            <v-alert v-else-if="error" type="error" variant="tonal" class="mb-4">
              <div class="font-weight-bold">Failed to load release notes</div>
              <div class="text-caption mt-1">{{ error }}</div>
            </v-alert>

            <template v-else-if="latestNote">
              <section class="hero-shell mb-6">
                <v-card class="latest-note-card" variant="flat">
                  <v-card-text class="pa-6 pa-md-8">
                    <div class="d-flex flex-wrap align-center ga-2 mb-4">
                      <v-chip size="small" color="primary" variant="flat">Latest Release</v-chip>
                      <v-chip size="small" variant="outlined">v{{ latestNote.version }}</v-chip>
                      <v-chip v-if="latestNote.date" size="small" variant="outlined">{{ latestNote.date }}</v-chip>
                    </div>
                    <div class="text-h4 mb-3 hero-title">{{ latestNote.title }}</div>
                    <div class="text-body-1 hero-copy mb-6">
                      User-visible improvements, workflow refinements, and fixes collected into a readable release archive.
                    </div>

                    <v-row>
                      <v-col cols="12" md="7">
                        <div class="text-overline mb-2 text-medium-emphasis">Highlights</div>
                        <v-list bg-color="transparent" density="comfortable" class="pa-0">
                          <v-list-item v-for="highlight in latestNote.highlights.slice(0, 5)" :key="highlight" class="px-0">
                            <template #prepend>
                              <v-icon size="small" color="primary">mdi-sparkles</v-icon>
                            </template>
                            <v-list-item-title class="text-body-2 whitespace-normal">{{ highlight }}</v-list-item-title>
                          </v-list-item>
                        </v-list>
                      </v-col>
                      <v-col cols="12" md="5">
                        <div class="stats-grid">
                          <div class="stat-card">
                            <div class="stat-value">{{ notes.length }}</div>
                            <div class="stat-label">Tracked releases</div>
                          </div>
                          <div class="stat-card">
                            <div class="stat-value">{{ latestNote.sections.length }}</div>
                            <div class="stat-label">Sections in latest note</div>
                          </div>
                        </div>
                      </v-col>
                    </v-row>
                  </v-card-text>
                </v-card>
              </section>

              <div class="d-flex align-center justify-space-between mb-3 flex-wrap ga-2">
                <div>
                  <div class="text-h6">Release Archive</div>
                  <div class="text-body-2 text-medium-emphasis">Browse the generated notes for each published version.</div>
                </div>
              </div>

              <v-expansion-panels v-model="expandedPanels" multiple variant="accordion">
                <v-expansion-panel v-for="(note, index) in notes" :key="note.version" :value="index">
                  <v-expansion-panel-title>
                    <div class="d-flex flex-column archive-header">
                      <div class="d-flex align-center flex-wrap ga-2">
                        <span class="font-weight-medium">v{{ note.version }}</span>
                        <v-chip v-if="note.date" size="x-small" variant="outlined">{{ note.date }}</v-chip>
                        <v-chip size="x-small" variant="tonal">{{ note.highlights.length }} highlights</v-chip>
                      </div>
                      <div v-if="note.highlights[0]" class="text-caption text-medium-emphasis mt-1">
                        {{ note.highlights[0] }}
                      </div>
                    </div>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <div class="d-flex flex-wrap ga-2 mb-4" v-if="note.sections.length > 0">
                      <v-chip v-for="section in note.sections" :key="section.title" size="small" variant="outlined">
                        {{ section.title }} · {{ section.items.length }}
                      </v-chip>
                    </div>
                    <div class="markdown-content" v-html="note.html"></div>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </template>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useWhatsNew } from '@/composables/useWhatsNew'

const expandedPanels = ref<number[]>([0])
const { latestNote, notes, loading, error, loadAllNotes } = useWhatsNew()

onMounted(async () => {
  try {
    await loadAllNotes()
  } catch (loadError) {
    console.error('Failed to load release notes archive:', loadError)
  }
})
</script>

<style scoped>
.whats-new-view {
  min-height: calc(100vh - 64px);
}

.hero-shell {
  position: relative;
}

.latest-note-card {
  border: 1px solid rgba(var(--v-theme-primary), 0.16);
  background:
    radial-gradient(circle at top right, rgba(var(--v-theme-primary), 0.16), transparent 28%),
    linear-gradient(135deg, rgba(var(--v-theme-primary), 0.08), rgba(var(--v-theme-surface), 1));
}

.hero-title {
  line-height: 1.1;
}

.hero-copy {
  max-width: 56rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.stat-card {
  border: 1px solid rgba(var(--v-theme-primary), 0.14);
  border-radius: 16px;
  padding: 1rem;
  background: rgba(var(--v-theme-surface), 0.72);
  backdrop-filter: blur(8px);
}

.stat-value {
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1;
}

.stat-label {
  margin-top: 0.4rem;
  font-size: 0.85rem;
  color: rgba(var(--v-theme-on-surface), 0.72);
}

.archive-header {
  width: 100%;
}

.markdown-content {
  max-width: 900px;
  line-height: 1.7;
  font-size: 15px;
}

.whitespace-normal {
  white-space: normal;
}

.markdown-content :deep(h1) {
  font-size: 2rem;
  font-weight: 600;
  margin-top: 0;
  margin-bottom: 0.75em;
}

.markdown-content :deep(h2) {
  font-size: 1.35rem;
  font-weight: 600;
  margin-top: 1.25em;
  margin-bottom: 0.5em;
}

.markdown-content :deep(p) {
  margin-bottom: 1em;
}

.markdown-content :deep(ul) {
  margin-bottom: 1em;
  padding-left: 1.5em;
}

.markdown-content :deep(li) {
  margin-bottom: 0.5em;
}

.markdown-content :deep(a) {
  color: rgb(var(--v-theme-primary));
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

@media (max-width: 959px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>