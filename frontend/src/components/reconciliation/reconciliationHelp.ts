export interface ReconciliationHelpItem {
  label: string
  description: string
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
  description: 'Find candidate target records for normalized rows, review each decision, and export the results.',
  quickTips: [
    'Find Candidates proposes matches; it does not accept a candidate for you.',
    'The search label finds candidates. The encoded business key identifies the row and its decision.',
    'Accepted decisions become effective after Export to Mapping. Manual links are saved directly and are not checked against SEAD.',
    'New means the row has no mapping to an existing target. The ingester handles it as a new record; ID allocation depends on its mode.',
  ],
  workflow: [
    {
      label: '1. Find Candidates',
      description:
        'Search normalized rows for possible target records. Results are proposals until you choose an action.',
    },
    {
      label: '2. Review and decide',
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
      label: 'Decision ID',
      description: 'The target ID selected in the reconciliation decision. It is not effective until exported.',
    },
    {
      label: 'Decision confidence',
      description:
        'The candidate score as a percentage, or Unknown when no score is available. It does not approve a match.',
    },
    {
      label: 'Decision status',
      description:
        'Proposed, Accepted, Rejected, or New. New means the row has no mapping to an existing target. Unresolved, Needs attention, and Unreviewable indicate missing candidates or decisions, row errors, or a missing business key.',
    },
    {
      label: 'Current ID',
      description:
        'The ID currently used by normalization. Its badge shows whether it comes from the normalized row or a committed mapping, and whether a reconciliation mapping was verified.',
    },
    {
      label: 'Row errors',
      description: 'Problems reported for this row. Resolve them before relying on its decision.',
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
        'Search all normalized rows and create or refresh proposed candidates. Existing operator decisions are preserved.',
    },
    {
      label: 'Add Manual Link',
      description:
        'Enter an encoded business key and positive target ID. This saves a trusted manual link directly, without checking the ID against SEAD.',
    },
    {
      label: 'Export to Mapping',
      description:
        'Check and export accepted candidates; export New decisions separately. Manual and unowned links are protected.',
    },
    {
      label: 'Preview',
      description: 'Inspect row decisions, filter the preview, or download the visible rows as CSV.',
    },
    {
      label: 'Status filters and row search',
      description: 'Filter by decision state or errors, or search the grid to find specific rows.',
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
      description: 'Search for an alternative using at least two characters. Select a result and choose Accept Match.',
    },
    {
      label: 'Reject',
      description: 'Save a rejection for this row.',
    },
    {
      label: 'New',
      description:
        'Record that this row has no mapping to an existing target. The ingester treats it as a new record; an optional reason can be saved.',
    },
    {
      label: 'Manual link',
      description:
        'Open the manual-link form with this row’s key filled in. The saved ID is trusted and is not checked against SEAD.',
    },
  ],
}
