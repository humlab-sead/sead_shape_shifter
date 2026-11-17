export interface ReconciliationHelpItem {
  label: string
  description: string
  icon?: string
}

export const RECONCILIATION_ACTION_ICONS = {
  search: 'mdi-magnify',
  reject: 'mdi-close-circle-outline',
  new: 'mdi-plus-circle-outline',
  manualLink: 'mdi-link-variant',
} as const

export const RECONCILIATION_STATUS_PRESENTATION = {
  proposed: { icon: 'mdi-lightbulb-outline', color: 'blue', backgroundClass: 'bg-blue-lighten-5' },
  accepted: { icon: 'mdi-check-circle-outline', color: 'green', backgroundClass: 'bg-green-lighten-5' },
  rejected: { icon: 'mdi-close-circle-outline', color: 'grey', backgroundClass: 'bg-grey-lighten-5' },
  local: { icon: 'mdi-home-outline', color: 'purple', backgroundClass: 'bg-purple-lighten-5' },
  unresolved: { icon: 'mdi-help-circle-outline', color: 'amber', backgroundClass: 'bg-amber-lighten-5' },
  errors: { icon: 'mdi-alert-circle-outline', color: 'red', backgroundClass: 'bg-red-lighten-5' },
} as const

const RECONCILIATION_STATUS_KEYS: Partial<Record<string, keyof typeof RECONCILIATION_STATUS_PRESENTATION>> = {
  Proposed: 'proposed',
  Accepted: 'accepted',
  'Accepted · re-accept candidate': 'accepted',
  Rejected: 'rejected',
  New: 'local',
  Unresolved: 'unresolved',
  Unreviewable: 'unresolved',
  'Needs attention': 'errors',
}

export function getReconciliationStatusPresentation(label: string) {
  const key = RECONCILIATION_STATUS_KEYS[label]
  return key ? RECONCILIATION_STATUS_PRESENTATION[key] : undefined
}

interface ReconciliationHelpContent {
  title: string
  description: string
  quickTips: string[]
  workflow: ReconciliationHelpItem[]
  columns: ReconciliationHelpItem[]
  controls: ReconciliationHelpItem[]
  rowActions: ReconciliationHelpItem[]
}

export const reconciliationHelp: ReconciliationHelpContent = {
  title: 'Reconcile & Review',
  description: 'Find candidate target records for normalized rows, review the matches, and export selected results.',
  quickTips: [
    'Find Candidates proposes matches; it does not accept a candidate for you.',
    'The search label finds candidates. The encoded business key identifies the row and stores your review choice.',
    'Accepting a candidate does not change the current ID until you use Export to Mapping. Manual links are saved directly and are not checked against SEAD.',
    'New means the row has no mapping to an existing target. The ingester handles it as a new record; ID allocation depends on its mode.',
  ],
  workflow: [
    {
      label: '1. Find Candidates',
      description:
        'Search normalized rows for possible target records. Results are proposals until you choose an action.',
    },
    {
      label: '2. Review and choose',
      description:
        'Accept the correct candidate, search for another one, reject the suggestion, mark the row New, or add a manual link.',
    },
    {
      label: '3. Export to Mapping',
      description:
        'Export accepted candidates and New decisions. Accepted candidates are checked against SEAD during export.',
    },
  ],
  columns: [
    {
      label: 'Search label',
      description: 'The configured field value sent to candidate search. It is not the row identity.',
    },
    {
      label: 'Business key',
      description: 'The encoded key built from the entity keys. It identifies the row and stores its decision.',
    },
    {
      label: 'Other mapped columns',
      description: 'Additional normalized values used by the reconciliation specification; these vary by entity.',
    },
    {
      label: 'Selected target ID',
      description: 'The ID of the candidate selected for this row. It does not become the current ID until exported.',
    },
    {
      label: 'Score',
      description:
        'The candidate score as a percentage, or Unknown when no score is available. It does not approve a match.',
    },
    {
      label: 'Review status',
      description:
        'Proposed, Accepted, Rejected, or New. New means the row has no mapping to an existing target. Unresolved, Needs attention, and Unreviewable indicate missing candidates or review choices, row errors, or a missing business key.',
    },
    {
      label: 'Current ID',
      description:
        'The ID currently used by normalization. Its badge shows whether it comes from the normalized row or a committed mapping, and whether a reconciliation mapping was verified.',
    },
    {
      label: 'Row errors',
      description: 'Problems reported for this row. Resolve them before accepting a candidate or exporting a mapping.',
    },
    {
      label: 'Actions',
      description: 'Row-specific review buttons. Review appears only when candidates are available.',
    },
  ],
  controls: [
    {
      label: 'Find Candidates',
      description:
        'Search all normalized rows and create or refresh proposed candidates. Existing review choices are preserved.',
    },
    {
      label: 'Add Manual Link',
      description:
        'Enter an encoded business key and positive target ID. This saves a trusted manual link directly, without checking the ID against SEAD.',
    },
    {
      label: 'Export to Mapping',
      description:
        'Check and export accepted candidates; export New approvals separately. Manual and unowned links are protected.',
    },
    {
      label: 'Preview',
      description:
        'Temporarily unavailable while the preview is updated to show the source values used to find candidates.',
    },
    {
      label: 'Status filters and row search',
      description: 'Filter by review status or errors, or search the grid to find specific rows.',
    },
  ],
  rowActions: [
    {
      label: 'Review (n)',
      description:
        'Open the n suggested candidates. Select one and choose Accept selected candidate to save it as accepted.',
    },
    {
      label: 'Search',
      icon: RECONCILIATION_ACTION_ICONS.search,
      description: 'Search for an alternative using at least two characters. Select a result and choose Accept Match.',
    },
    {
      label: 'Reject',
      icon: RECONCILIATION_ACTION_ICONS.reject,
      description: 'Save a rejection for this row.',
    },
    {
      label: 'New',
      icon: RECONCILIATION_ACTION_ICONS.new,
      description:
        'Record that this row has no mapping to an existing target. The ingester treats it as a new record; an optional reason can be saved.',
    },
    {
      label: 'Manual link',
      icon: RECONCILIATION_ACTION_ICONS.manualLink,
      description:
        'Open the manual-link form with this row’s key filled in. The saved ID is trusted and is not checked against SEAD.',
    },
  ],
}
