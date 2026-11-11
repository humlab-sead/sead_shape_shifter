import { ref } from 'vue'
import MarkdownIt from 'markdown-it'
import { whatsNewApi, type WhatsNewManifestItem, type WhatsNewManifestResponse } from '@/api/whats-new'

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: false,
})

const pendingMd = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: false,
})

export interface WhatsNewSection {
  title: string
  items: string[]
}

export interface WhatsNewNote {
  version: string
  title: string
  date: string
  path: string
  markdown: string
  html: string
  highlights: string[]
  sections: WhatsNewSection[]
}

export interface PendingWhatsNewNote {
  markdown: string
  html: string
}

const noteCache = new Map<string, Promise<WhatsNewNote>>()
let manifestCache: Promise<WhatsNewManifestResponse> | null = null
let pendingNoteCache: Promise<PendingWhatsNewNote> | null = null

function parseSections(markdown: string): WhatsNewSection[] {
  const sections: WhatsNewSection[] = []
  let currentTitle: string | null = null
  let currentItems: string[] = []

  for (const rawLine of markdown.split('\n')) {
    const line = rawLine.trim()
    if (line.startsWith('## ')) {
      if (currentTitle) {
        sections.push({ title: currentTitle, items: currentItems })
      }
      currentTitle = line.slice(3).trim()
      currentItems = []
      continue
    }

    if (currentTitle && line.startsWith('- ')) {
      currentItems.push(line.slice(2).trim())
    }
  }

  if (currentTitle) {
    sections.push({ title: currentTitle, items: currentItems })
  }

  return sections
}

function parseNote(markdown: string, version: string): WhatsNewNote {
  const title = markdown.match(/^#\s+(.+)$/m)?.[1]?.trim() ?? `What's New in v${version}`
  const date = markdown.match(/^Date:\s+(.+)$/m)?.[1]?.trim() ?? ''
  const sections = parseSections(markdown)
  const highlights = sections.find((section) => section.title === 'Highlights')?.items ?? []

  return {
    version,
    title,
    date,
    path: `/docs/whats-new/v${version}.md`,
    markdown,
    html: md.render(markdown),
    highlights,
    sections,
  }
}

async function fetchManifest(): Promise<WhatsNewManifestResponse> {
  return whatsNewApi.getManifest()
}

function getOrLoadManifest(): Promise<WhatsNewManifestResponse> {
  if (!manifestCache) {
    manifestCache = fetchManifest()
  }

  return manifestCache
}

async function fetchNote(version: string): Promise<WhatsNewNote> {
  const markdown = await whatsNewApi.getNote(version)
  if (markdown.startsWith('<!DOCTYPE html>')) {
    throw new Error(`Received HTML instead of markdown for release note v${version}`)
  }

  return parseNote(markdown, version)
}

async function fetchPendingNote(): Promise<PendingWhatsNewNote> {
  const markdown = await whatsNewApi.getPendingContent()
  if (markdown.startsWith('<!DOCTYPE html>')) {
    throw new Error('Received HTML instead of markdown for pending release notes')
  }

  return { markdown, html: pendingMd.render(markdown) }
}

function getOrLoadNote(version: string): Promise<WhatsNewNote> {
  const cached = noteCache.get(version)
  if (cached) {
    return cached
  }

  const pending = fetchNote(version)
  noteCache.set(version, pending)
  return pending
}

function getOrLoadPendingNote(): Promise<PendingWhatsNewNote> {
  if (!pendingNoteCache) {
    pendingNoteCache = fetchPendingNote()
  }

  return pendingNoteCache
}

export function useWhatsNew() {
  const latestNote = ref<WhatsNewNote | null>(null)
  const pendingNote = ref<PendingWhatsNewNote | null>(null)
  const notes = ref<WhatsNewNote[]>([])
  const manifest = ref<WhatsNewManifestItem[]>([])
  const latestVersion = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function loadLatestNote() {
    loading.value = true
    error.value = null

    try {
      const manifestResponse = await getOrLoadManifest()
      manifest.value = manifestResponse.items
      latestVersion.value = manifestResponse.latest_version

      if (!manifestResponse.latest_version) {
        latestNote.value = null
        return null
      }

      latestNote.value = await getOrLoadNote(manifestResponse.latest_version)
      return latestNote.value
    } catch (err: any) {
      error.value = err.message || 'Failed to load latest release notes'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loadAllNotes() {
    loading.value = true
    error.value = null

    try {
      const manifestResponse = await getOrLoadManifest()
      manifest.value = manifestResponse.items
      latestVersion.value = manifestResponse.latest_version
      const notesPromise = Promise.all(manifestResponse.items.map((item) => getOrLoadNote(item.version)))
      const pendingNotePromise = manifestResponse.pending_available ? getOrLoadPendingNote() : Promise.resolve(null)
      const [loadedNotes, loadedPendingNote] = await Promise.all([notesPromise, pendingNotePromise])
      notes.value = loadedNotes
      pendingNote.value = loadedPendingNote
      latestNote.value = notes.value[0] ?? null
      return notes.value
    } catch (err: any) {
      error.value = err.message || 'Failed to load release notes archive'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    latestNote,
    pendingNote,
    notes,
    manifest,
    latestVersion,
    loading,
    error,
    loadLatestNote,
    loadAllNotes,
  }
}
