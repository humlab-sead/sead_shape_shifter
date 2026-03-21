import { ref } from 'vue'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: true,
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

export interface WhatsNewManifestItem {
  version: string
  title: string
  date: string | null
  path: string
}

interface WhatsNewManifestResponse {
  latest_version: string | null
  items: WhatsNewManifestItem[]
}

const noteCache = new Map<string, Promise<WhatsNewNote>>()
let manifestCache: Promise<WhatsNewManifestResponse> | null = null

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
  const response = await fetch('/api/v1/whats-new')
  if (!response.ok) {
    throw new Error(`Failed to load release notes manifest: ${response.statusText}`)
  }

  return response.json() as Promise<WhatsNewManifestResponse>
}

function getOrLoadManifest(): Promise<WhatsNewManifestResponse> {
  if (!manifestCache) {
    manifestCache = fetchManifest()
  }

  return manifestCache
}

async function fetchNote(version: string): Promise<WhatsNewNote> {
  const response = await fetch(`/api/v1/whats-new/${version}/content`)
  if (!response.ok) {
    throw new Error(`Failed to load release notes for v${version}: ${response.statusText}`)
  }

  const markdown = await response.text()
  if (markdown.startsWith('<!DOCTYPE html>')) {
    throw new Error(`Received HTML instead of markdown for release note v${version}`)
  }

  return parseNote(markdown, version)
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

export function useWhatsNew() {
  const latestNote = ref<WhatsNewNote | null>(null)
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
      notes.value = await Promise.all(manifestResponse.items.map((item) => getOrLoadNote(item.version)))
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
    notes,
    manifest,
    latestVersion,
    loading,
    error,
    loadLatestNote,
    loadAllNotes,
  }
}