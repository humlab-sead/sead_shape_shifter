/**
 * Test Fixtures - Sample Project Configurations
 * 
 * These fixtures provide reusable test data for E2E tests.
 * They represent different project configurations for testing various scenarios.
 */

export const testProjects = {
  /**
   * Minimal valid project - simplest possible configuration
   */
  minimal: {
    name: 'minimal-test-project',
    version: '1.0',
    data_sources: {
      test_db: {
        driver: 'sqlite',
        database: ':memory:',
      },
    },
    entities: {
      simple_entity: {
        type: 'fixed',
        values: [
          { id: 1, name: 'Test Item 1' },
          { id: 2, name: 'Test Item 2' },
        ],
        keys: ['id'],
        surrogate_id: 'entity_id',
      },
    },
  },

  /**
   * Project with validation errors - for testing validation and auto-fix workflows
   */
  withErrors: {
    name: 'validation-test-project',
    version: '1.0',
    data_sources: {
      test_db: {
        driver: 'sqlite',
        database: ':memory:',
      },
    },
    entities: {
      parent_entity: {
        type: 'fixed',
        values: [{ id: 1, name: 'Parent' }],
        keys: ['id'],
        surrogate_id: 'parent_id',
      },
      child_entity: {
        type: 'fixed',
        values: [{ id: 1, parent_id: 1, name: 'Child' }],
        keys: ['id'],
        surrogate_id: 'child_id',
        foreign_keys: [
          {
            entity: 'nonexistent_entity', // Error: references non-existent entity
            local_keys: ['parent_id'],
            remote_keys: ['id'],
            how: 'left',
          },
        ],
      },
    },
  },

  /**
   * Project with foreign keys - for testing relationship validation
   */
  withForeignKeys: {
    name: 'foreign-key-test-project',
    version: '1.0',
    data_sources: {
      test_db: {
        driver: 'sqlite',
        database: ':memory:',
      },
    },
    entities: {
      sample_type: {
        type: 'fixed',
        values: [
          { type_id: 1, type_name: 'Wood' },
          { type_id: 2, type_name: 'Charcoal' },
          { type_id: 3, type_name: 'Bone' },
        ],
        keys: ['type_name'],
        surrogate_id: 'sample_type_id',
      },
      sample: {
        type: 'fixed',
        values: [
          { sample_id: 1, sample_name: 'S001', type_name: 'Wood' },
          { sample_id: 2, sample_name: 'S002', type_name: 'Charcoal' },
          { sample_id: 3, sample_name: 'S003', type_name: 'Bone' },
        ],
        keys: ['sample_name'],
        surrogate_id: 'sample_id',
        foreign_keys: [
          {
            entity: 'sample_type',
            local_keys: ['type_name'],
            remote_keys: ['type_name'],
            how: 'left',
            constraints: {
              cardinality: 'many_to_one',
            },
          },
        ],
      },
    },
  },

  /**
   * Project with reconciliation configured
   */
  withReconciliation: {
    name: 'reconciliation-test-project',
    version: '1.0',
    data_sources: {
      test_db: {
        driver: 'sqlite',
        database: ':memory:',
      },
    },
    entities: {
      taxon: {
        type: 'fixed',
        values: [
          { taxon_name: 'Pinus sylvestris', author: 'L.' },
          { taxon_name: 'Betula pubescens', author: 'Ehrh.' },
        ],
        keys: ['taxon_name'],
        surrogate_id: 'taxon_id',
      },
    },
    reconciliation: {
      entities: {
        taxon: {
          taxon_id: {
            remote: {
              service_type: 'Taxon',
            },
            property_mappings: {
              taxon_name: 'taxon_name',
              author: 'author',
            },
            auto_accept_threshold: 0.95,
            review_threshold: 0.7,
          },
        },
      },
    },
  },

  /**
   * Complex project with multiple entities and dependencies
   */
  complex: {
    name: 'complex-test-project',
    version: '1.0',
    data_sources: {
      test_db: {
        driver: 'sqlite',
        database: ':memory:',
      },
    },
    entities: {
      site: {
        type: 'fixed',
        values: [
          { site_id: 1, site_name: 'Site A', latitude: 63.1234, longitude: 14.5678 },
          { site_id: 2, site_name: 'Site B', latitude: 63.2345, longitude: 14.6789 },
        ],
        keys: ['site_name'],
        surrogate_id: 'site_id',
      },
      sample_type: {
        type: 'fixed',
        values: [
          { type_id: 1, type_name: 'Wood' },
          { type_id: 2, type_name: 'Charcoal' },
        ],
        keys: ['type_name'],
        surrogate_id: 'sample_type_id',
      },
      sample: {
        type: 'fixed',
        values: [
          { sample_id: 1, sample_name: 'S001', site_name: 'Site A', type_name: 'Wood', depth: 15.5 },
          { sample_id: 2, sample_name: 'S002', site_name: 'Site A', type_name: 'Charcoal', depth: 22.0 },
          { sample_id: 3, sample_name: 'S003', site_name: 'Site B', type_name: 'Wood', depth: 8.3 },
        ],
        keys: ['sample_name'],
        surrogate_id: 'sample_id',
        depends_on: ['site', 'sample_type'],
        foreign_keys: [
          {
            entity: 'site',
            local_keys: ['site_name'],
            remote_keys: ['site_name'],
            how: 'left',
          },
          {
            entity: 'sample_type',
            local_keys: ['type_name'],
            remote_keys: ['type_name'],
            how: 'left',
          },
        ],
      },
    },
    task_list: {
      tasks: ['site', 'sample_type', 'sample'],
    },
  },
}

/**
 * Helper to create a project YAML string from fixture
 */
export function projectToYaml(project: typeof testProjects.minimal): string {
  return `# Auto-generated test project
${JSON.stringify(project, null, 2)
  .replace(/"([^"]+)":/g, '$1:') // Remove quotes from keys
  .replace(/^/gm, '')}`
}
