/**
 * Unit tests for schema type utilities
 */
import { describe, it, expect } from 'vitest'
import {
  formatDataType,
  getColumnIcon,
  getColumnColor,
  formatRowCount,
  getTableIcon,
  isValidTableName,
  escapeSqlIdentifier,
  type ColumnMetadata,
} from '../schema'

describe('schema utilities', () => {
  const createMockColumn = (overrides: Partial<ColumnMetadata> = {}): ColumnMetadata => ({
    name: 'test_column',
    data_type: 'VARCHAR',
    nullable: true,
    is_primary_key: false,
    max_length: null,
    default: null,
    ...overrides,
  })

  describe('formatDataType', () => {
    it('should format basic data type', () => {
      const column = createMockColumn({ data_type: 'INTEGER' })
      expect(formatDataType(column)).toBe('INTEGER')
    })

    it('should include max_length when present', () => {
      const column = createMockColumn({ data_type: 'VARCHAR', max_length: 255 })
      expect(formatDataType(column)).toBe('VARCHAR(255)')
    })

    it('should append NOT NULL when nullable is false', () => {
      const column = createMockColumn({ data_type: 'INTEGER', nullable: false })
      expect(formatDataType(column)).toBe('INTEGER NOT NULL')
    })

    it('should combine max_length and NOT NULL', () => {
      const column = createMockColumn({
        data_type: 'VARCHAR',
        max_length: 100,
        nullable: false,
      })
      expect(formatDataType(column)).toBe('VARCHAR(100) NOT NULL')
    })

    it('should not include max_length when null', () => {
      const column = createMockColumn({ data_type: 'TEXT', max_length: null })
      expect(formatDataType(column)).toBe('TEXT')
    })

    it('should not include max_length when undefined', () => {
      const column = createMockColumn({ data_type: 'TEXT', max_length: undefined })
      expect(formatDataType(column)).toBe('TEXT')
    })

    it('should handle zero max_length', () => {
      const column = createMockColumn({ data_type: 'VARCHAR', max_length: 0 })
      expect(formatDataType(column)).toBe('VARCHAR(0)')
    })
  })

  describe('getColumnIcon', () => {
    it('should return key icon for primary key', () => {
      const column = createMockColumn({ is_primary_key: true, data_type: 'INTEGER' })
      expect(getColumnIcon(column)).toBe('mdi-key')
    })

    it('should return numeric icon for integer types', () => {
      expect(getColumnIcon(createMockColumn({ data_type: 'INT' }))).toBe('mdi-numeric')
      expect(getColumnIcon(createMockColumn({ data_type: 'INTEGER' }))).toBe('mdi-numeric')
      expect(getColumnIcon(createMockColumn({ data_type: 'BIGINT' }))).toBe('mdi-numeric')
      expect(getColumnIcon(createMockColumn({ data_type: 'SMALLINT' }))).toBe('mdi-numeric')
    })

    it('should return numeric icon for decimal types', () => {
      expect(getColumnIcon(createMockColumn({ data_type: 'NUMERIC' }))).toBe('mdi-numeric')
      expect(getColumnIcon(createMockColumn({ data_type: 'DECIMAL' }))).toBe('mdi-numeric')
      expect(getColumnIcon(createMockColumn({ data_type: 'FLOAT' }))).toBe('mdi-numeric')
      expect(getColumnIcon(createMockColumn({ data_type: 'DOUBLE' }))).toBe('mdi-numeric')
      expect(getColumnIcon(createMockColumn({ data_type: 'REAL' }))).toBe('mdi-numeric')
    })

    it('should return text icon for character types', () => {
      expect(getColumnIcon(createMockColumn({ data_type: 'CHAR' }))).toBe('mdi-format-text')
      expect(getColumnIcon(createMockColumn({ data_type: 'VARCHAR' }))).toBe('mdi-format-text')
      expect(getColumnIcon(createMockColumn({ data_type: 'TEXT' }))).toBe('mdi-format-text')
      expect(getColumnIcon(createMockColumn({ data_type: 'STRING' }))).toBe('mdi-format-text')
    })

    it('should return calendar icon for date/time types', () => {
      expect(getColumnIcon(createMockColumn({ data_type: 'DATE' }))).toBe('mdi-calendar-clock')
      expect(getColumnIcon(createMockColumn({ data_type: 'TIME' }))).toBe('mdi-calendar-clock')
      expect(getColumnIcon(createMockColumn({ data_type: 'DATETIME' }))).toBe('mdi-calendar-clock')
      expect(getColumnIcon(createMockColumn({ data_type: 'TIMESTAMP' }))).toBe('mdi-calendar-clock')
    })

    it('should return checkbox icon for boolean type', () => {
      expect(getColumnIcon(createMockColumn({ data_type: 'BOOL' }))).toBe('mdi-checkbox-marked-outline')
      expect(getColumnIcon(createMockColumn({ data_type: 'BOOLEAN' }))).toBe('mdi-checkbox-marked-outline')
    })

    it('should return json icon for JSON types', () => {
      expect(getColumnIcon(createMockColumn({ data_type: 'JSON' }))).toBe('mdi-code-json')
      expect(getColumnIcon(createMockColumn({ data_type: 'JSONB' }))).toBe('mdi-code-json')
    })

    it('should return identifier icon for UUID type', () => {
      expect(getColumnIcon(createMockColumn({ data_type: 'UUID' }))).toBe('mdi-identifier')
    })

    it('should return brackets icon for array types', () => {
      expect(getColumnIcon(createMockColumn({ data_type: 'ARRAY' }))).toBe('mdi-code-brackets')
      // Note: Type-specific arrays (INT[], TEXT[]) match their base type first
    })

    it('should return database icon for unknown types', () => {
      expect(getColumnIcon(createMockColumn({ data_type: 'CUSTOM_TYPE' }))).toBe('mdi-database-outline')
      expect(getColumnIcon(createMockColumn({ data_type: 'BLOB' }))).toBe('mdi-database-outline')
    })

    it('should be case-insensitive', () => {
      expect(getColumnIcon(createMockColumn({ data_type: 'varchar' }))).toBe('mdi-format-text')
      expect(getColumnIcon(createMockColumn({ data_type: 'INTEGER' }))).toBe('mdi-numeric')
      expect(getColumnIcon(createMockColumn({ data_type: 'Boolean' }))).toBe('mdi-checkbox-marked-outline')
    })
  })

  describe('getColumnColor', () => {
    it('should return amber for primary key', () => {
      const column = createMockColumn({ is_primary_key: true })
      expect(getColumnColor(column)).toBe('amber')
    })

    it('should return blue for NOT NULL columns (non-primary)', () => {
      const column = createMockColumn({ is_primary_key: false, nullable: false })
      expect(getColumnColor(column)).toBe('blue')
    })

    it('should return grey for nullable columns', () => {
      const column = createMockColumn({ is_primary_key: false, nullable: true })
      expect(getColumnColor(column)).toBe('grey')
    })

    it('should prioritize primary key color over NOT NULL', () => {
      const column = createMockColumn({ is_primary_key: true, nullable: false })
      expect(getColumnColor(column)).toBe('amber')
    })
  })

  describe('formatRowCount', () => {
    it('should return "Unknown" for null', () => {
      expect(formatRowCount(null)).toBe('Unknown')
    })

    it('should return "Unknown" for undefined', () => {
      expect(formatRowCount(undefined)).toBe('Unknown')
    })

    it('should return plain number for counts < 1000', () => {
      expect(formatRowCount(0)).toBe('0')
      expect(formatRowCount(1)).toBe('1')
      expect(formatRowCount(999)).toBe('999')
    })

    it('should format thousands with K suffix', () => {
      expect(formatRowCount(1000)).toBe('1.0K')
      expect(formatRowCount(1500)).toBe('1.5K')
      expect(formatRowCount(10000)).toBe('10.0K')
      expect(formatRowCount(999999)).toBe('1000.0K')
    })

    it('should format millions with M suffix', () => {
      expect(formatRowCount(1000000)).toBe('1.0M')
      expect(formatRowCount(1500000)).toBe('1.5M')
      expect(formatRowCount(10000000)).toBe('10.0M')
    })

    it('should round to one decimal place', () => {
      expect(formatRowCount(1234)).toBe('1.2K')
      expect(formatRowCount(5678)).toBe('5.7K')
      expect(formatRowCount(1234567)).toBe('1.2M')
    })
  })

  describe('getTableIcon', () => {
    it('should return table icon', () => {
      expect(getTableIcon()).toBe('mdi-table')
    })
  })

  describe('isValidTableName', () => {
    it('should accept valid table names starting with letter', () => {
      expect(isValidTableName('users')).toBe(true)
      expect(isValidTableName('Users')).toBe(true)
      expect(isValidTableName('user_accounts')).toBe(true)
      expect(isValidTableName('user123')).toBe(true)
    })

    it('should accept valid table names starting with underscore', () => {
      expect(isValidTableName('_users')).toBe(true)
      expect(isValidTableName('_internal_table')).toBe(true)
    })

    it('should reject names starting with number', () => {
      expect(isValidTableName('1users')).toBe(false)
      expect(isValidTableName('123table')).toBe(false)
    })

    it('should reject names with special characters', () => {
      expect(isValidTableName('user-accounts')).toBe(false)
      expect(isValidTableName('user.accounts')).toBe(false)
      expect(isValidTableName('user@accounts')).toBe(false)
      expect(isValidTableName('user accounts')).toBe(false)
      expect(isValidTableName('user!accounts')).toBe(false)
    })

    it('should reject empty string', () => {
      expect(isValidTableName('')).toBe(false)
    })

    it('should accept names with consecutive underscores', () => {
      expect(isValidTableName('user__accounts')).toBe(true)
    })

    it('should accept names ending with underscore', () => {
      expect(isValidTableName('users_')).toBe(true)
    })

    it('should accept single letter names', () => {
      expect(isValidTableName('a')).toBe(true)
      expect(isValidTableName('Z')).toBe(true)
    })

    it('should accept single underscore', () => {
      expect(isValidTableName('_')).toBe(true)
    })
  })

  describe('escapeSqlIdentifier', () => {
    it('should wrap identifier in double quotes', () => {
      expect(escapeSqlIdentifier('users')).toBe('"users"')
      expect(escapeSqlIdentifier('table_name')).toBe('"table_name"')
    })

    it('should escape internal double quotes', () => {
      expect(escapeSqlIdentifier('user"name')).toBe('"user""name"')
      expect(escapeSqlIdentifier('weird""table')).toBe('"weird""""table"')
    })

    it('should handle identifiers with spaces', () => {
      expect(escapeSqlIdentifier('user accounts')).toBe('"user accounts"')
    })

    it('should handle identifiers with special characters', () => {
      expect(escapeSqlIdentifier('user-accounts')).toBe('"user-accounts"')
      expect(escapeSqlIdentifier('user.table')).toBe('"user.table"')
      expect(escapeSqlIdentifier('user@domain')).toBe('"user@domain"')
    })

    it('should handle empty string', () => {
      expect(escapeSqlIdentifier('')).toBe('""')
    })

    it('should handle identifiers starting with numbers', () => {
      expect(escapeSqlIdentifier('123table')).toBe('"123table"')
    })

    it('should handle multiple consecutive quotes', () => {
      expect(escapeSqlIdentifier('a""b')).toBe('"a""""b"')
    })

    it('should handle identifiers with only quotes', () => {
      expect(escapeSqlIdentifier('""')).toBe('""""""')
    })

    it('should be idempotent when properly used', () => {
      const identifier = 'user"table'
      const escaped1 = escapeSqlIdentifier(identifier)
      // Note: Should not escape already escaped identifiers
      expect(escaped1).toBe('"user""table"')
    })

    it('should handle SQL keywords', () => {
      expect(escapeSqlIdentifier('SELECT')).toBe('"SELECT"')
      expect(escapeSqlIdentifier('FROM')).toBe('"FROM"')
      expect(escapeSqlIdentifier('WHERE')).toBe('"WHERE"')
    })

    it('should handle case-sensitive identifiers', () => {
      expect(escapeSqlIdentifier('Users')).toBe('"Users"')
      expect(escapeSqlIdentifier('USERS')).toBe('"USERS"')
    })
  })
})
