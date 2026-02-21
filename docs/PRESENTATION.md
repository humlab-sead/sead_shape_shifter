---
marp: true
theme: default
paginate: true
backgroundColor: #fff
backgroundImage: url('https://marp.app/assets/hero-background.svg')
header: 'Shape Shifter - SEAD Workshop'
footer: 'SEAD Development Team | January 2026'
---

<!--
This presentation uses Marp (Markdown Presentation Ecosystem)

To view/export:
1. Install Marp CLI: npm install -g @marp-team/marp-cli
2. Export to PDF: marp PRESENTATION_SEAD_WORKSHOP.md --pdf
3. Export to HTML: marp PRESENTATION_SEAD_WORKSHOP.md --html
4. Export to PPTX: marp PRESENTATION_SEAD_WORKSHOP.md --pptx
5. Watch mode: marp -w PRESENTATION_SEAD_WORKSHOP.md

Or use the Makefile:
  make presentation-pdf
  make presentation-html
  make presentation-pptx

Images:
- Place images in: docs/images/
- Screenshots in: docs/images/screenshots/
- Uncomment ![bg ...] lines and add your images
- Supported formats: PNG, JPG, SVG, GIF
- Use relative paths from this file
-->

<!-- _class: lead -->
<!-- _paginate: false -->

# Shape Shifter
## Data Harmonization for SEAD

*Simplifying Archaeological Data Integration*

**SEAD Development Team**
January 18, 2026

---

## Today's Agenda

1. **The Challenge** - Data integration pain points
2. **The Solution** - Shape Shifter overview
3. **Key Features** - What makes it work
4. **Identity Reconciliation** - Assigning SEAD identities
5. **Data Dispatch** - Sending data to target systems
6. **Live Walkthrough** - See it in action
7. **Your Benefits** - Why this matters to you
8. **Getting Started** - Next steps
9. **Q&A** - Your questions

*~30 minutes*

---

# Part 1: The Challenge

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Data Integration Today

<!-- ![bg right:40%](docs/images/data-chaos.png) -->

**The Current Reality:**

- 🗂️ Multiple data formats (Excel, Access, CSV, databases)
- 🔀 Inconsistent column names and structures
- 📊 Different naming conventions across providers
- ⚠️ Manual data transformation = errors
- ⏱️ Hours/days of preparation per dataset
- 🔁 Repeat for every new data delivery

**Sound familiar?**

<!-- 
Image suggestion: Screenshot showing messy Excel files, 
Access databases, CSV files scattered on desktop
-->

---

## Example: Sample Data Chaos

**Your Data:**
```
Sample_ID | SampleType | Latitude | Longitude
```

**Another Provider:**
```
sample_id | sample_type_name | (lat, lon)
```

**SEAD Expects:**
```
sample_id | sample_type_id | latitude_dd | longitude_dd
```

**Problem:** Someone has to manually map and transform this... every time.

---

## The Cost of Manual Integration

**For Data Providers:**
- ❌ Significant time investment
- ❌ Risk of transformation errors
- ❌ Difficult to validate correctness
- ❌ Hard to reproduce transformations
- ❌ Knowledge locked in individual workflows

**For SEAD:**
- ❌ Inconsistent data quality
- ❌ Manual QA required
- ❌ Delayed data availability
- ❌ Difficult to track provenance

---

# Part 2: The Solution

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Introducing Shape Shifter

<!-- ![bg right:35%](docs/images/shape-shifter-logo.svg) -->

**Declarative Data Transformation Framework**

✨ **Define once, run forever**
- Write transformation rules in simple YAML
- Visual editor for non-programmers
- Automatic validation and error detection
- Reproducible, auditable transformations

🎯 **Built for SEAD's needs**
- Archaeological data patterns
- Complex entity relationships
- Data quality requirements
- Integration workflows

<!-- 
Image suggestion: Shape Shifter logo or screenshot of the main interface
-->

---

## How It Works

```
┌─────────────────┐
│  Your Data      │  Excel, Access, 
│  Sources        │  PostgreSQL, CSV
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Shape Shifter  │  ← You configure transformations
│  Project        │     using visual editor
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SEAD-Ready     │  Validated, harmonized,
│  Data           │  ready for import
└─────────────────┘
```

---

## Key Concept: Declarative Configuration

**Traditional Approach (Python/SQL):**
```python
def transform_samples():
    df = pd.read_csv('samples.csv')
    df['sample_type_id'] = lookup_sample_type(df['SampleType'])
    df.rename({'Latitude': 'latitude_dd'}, inplace=True)
    # ... 50 more lines ...
```

**Shape Shifter (YAML):**
```yaml
sample:
  type: csv
  data_source: my_samples
  columns: [sample_id, sample_type, latitude_dd, longitude_dd]
  foreign_keys:
    - entity: sample_type
      local_keys: [sample_type]
      remote_keys: [sample_type_name]
```

**Which would you prefer to maintain?**

---

# Part 3: Key Features

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## 1. Visual Project Editor

![bg right:50% fit](docs/images/screenshots/project-editor.png)

**Web-Based Interface:**
- 🖥️ No installation required (browser-based)
- 📑 Tabbed interface: Entities, Dependencies, Validation, Reconciliation, Dispatch
- 📝 Monaco editor with YAML syntax highlighting
- 🔍 Real-time validation with auto-fix suggestions
- 💾 Automatic timestamped backups
- 📱 Works on any device

**For Archaeologists:**
- No programming required for basic tasks
- Form-based editors alongside YAML view
- Copy-paste from examples
- Immediate feedback on errors

---

## 2. Entity Management

**Define Your Data Entities:**

```yaml
sample:
  keys: [sample_name, site_id]
  surrogate_id: sample_id
  columns: [sample_name, sample_type, depth, notes]
  source: site
  foreign_keys:
    - entity: site
      local_keys: [site_id]
      remote_keys: [site_id]
```

**Visual Form Editor:**
- Fill in forms instead of writing YAML
- Add foreign keys with dropdowns
- Test relationships with sample data

---

## 3. Data Source Flexibility

**Connect to Multiple Sources:**

- 📊 **Excel/Access** - Your existing spreadsheets
- 🗄️ **Databases** - PostgreSQL, SQLite, SQL Server
- 📄 **CSV Files** - Simple text files
- 🔌 **MS Access** - Legacy database support

**Example Use Case:**
- Lookup tables from SEAD PostgreSQL
- Your samples from Excel
- Site data from Access database
- Combine seamlessly!

---

## 4. Intelligent Validation

**Multi-Level Quality Checks:**

✅ **Structural Validation**
- YAML syntax correct?
- All entities defined?
- References valid?
- No circular dependencies?

✅ **Data Validation**
- Columns exist in sources?
- Foreign keys match?
- Unique constraints satisfied?
- Data types compatible?

**Result:** Catch errors *before* data reaches SEAD

---

## 5. Auto-Fix Capabilities

**Smart Error Resolution:**

```
❌ Error: Column 'SampleType' not found in source

💡 Auto-fix available:
   Did you mean 'sample_type'?
   [Apply Fix]
```

**Features:**
- Automatic backup before fixes
- Preview changes before applying
- One-click error resolution
- Learn from corrections

---

## 6. Foreign Key Testing

**Verify Relationships Before Processing:**

```yaml
foreign_keys:
  - entity: sample_type
    local_keys: [sample_type_name]
    remote_keys: [type_name]
    constraints:
      cardinality: many_to_one
      require_unique_left: false
```

**Test Shows:**
- ✅ 98.5% match rate
- ⚠️ 15 unmatched values
- 📊 Sample data preview
- 💡 Recommendations

---

## 7. Data Preview

**See Results Before Committing:**

- 🔬 Preview individual entities from Entities tab
- 📊 Interactive data table with pagination
- 🔍 Filter and search capabilities
- 📈 Row counts and statistics
- ⚡ 3-tier intelligent caching (TTL, version, hash)

**Smart Caching:**
- Cached results with 5-minute TTL
- Version-based invalidation on project changes
- Hash-based detection of entity modifications
- Instant preview for unchanged entities

---

## 8. Data Dispatch System

**Integrated Project Workflow:**

🎯 **Dispatch Tab** (within each project)
- Configure target systems once in project settings
- Select dispatcher (SEAD Clearinghouse, etc.)
- Set ingester-specific policies
- Validate before dispatching

📤 **Supported Dispatchers:**
- **SEAD Clearinghouse** - Direct integration with submission policies
- **File Export** - Excel, CSV, JSON formats
- **Database** - PostgreSQL, SQLite direct writes
- **Extensible** - Plugin architecture for custom dispatchers

**Configuration-Based:**
- Dispatcher settings in project YAML under `options.ingesters`
- Reference existing data sources by name
- Reusable across project versions

---

## 9. Dispatch Workflow Integration

**Complete Data Pipeline:**

```
1. Define Entities (Entities tab)
   ↓
2. Configure Relationships (Dependencies graph)
   ↓
3. Validate Configuration (Validation tab)
   ↓
4. Reconcile Identities (Reconciliation tab)
   ↓
5. Dispatch Data (Dispatch tab)
```

**Dispatch Tab Features:**
- 🎯 Select ingester from project configuration
- 🔍 View target data source details
- ✅ Validate before dispatch
- 📊 Track dispatch status and results
- 💾 All settings saved in project file

---

## 10. Identity Reconciliation

**The Critical Integration Step**

🎯 **Assigning SEAD Identities**
- Map your taxonomy names to SEAD taxon IDs
- Link your sites to existing SEAD site records
- Connect samples to SEAD controlled vocabularies
- Resolve ambiguous names and variants

🤖 **Automated Matching**
- OpenRefine reconciliation service integration
- Fuzzy matching with confidence scores
- Geographic distance matching (for sites)
- Automatic suggestions for review

---

### Why Reconciliation Matters

**The Identity Problem:**

**Your Data:**
```
Site: "Ångermanälven Delta"
Taxon: "Pinus sylvestris L."
Sample Type: "Wood charcoal"
```

**SEAD Has:**
```
Site ID 1523: "Ångermanälven, delta area"
Taxon ID 4892: "Pinus sylvestris"
Sample Type ID 12: "Charcoal, wood"
```

**Question:** Are these the same? How do you know?

**Manual Approach:** Hours of lookups, spreadsheets, guesswork

**Shape Shifter:** Automated matching with confidence scores and review

---

### How Reconciliation Works

**1. Configure Specification**

```yaml
reconciliation:
  entities:
    sample_taxon:
      taxon_id:
        remote:
          service_type: "Taxon"  # SEAD entity type
        property_mappings:
          taxon_name: "taxon_name"
          author: "taxon_author"
        auto_accept_threshold: 0.95
        review_threshold: 0.70
```

**Define:**
- Which entity field needs SEAD IDs
- What SEAD entity type to match against
- Which properties to use for matching
- Confidence thresholds for auto-accept

---

### 2. Run Auto-Reconciliation

**Process:**

1. Fetch your unique values (e.g., all unique taxon names)
2. Send to OpenRefine reconciliation service
3. Service searches SEAD database
4. Returns ranked candidates with scores
5. Apply thresholds:
   - **≥95%** → Auto-accept
   - **70-95%** → Flag for review
   - **<70%** → No match, needs manual work

**Example Match:**
```
Your Value: "Pinus sylvestris L."
Candidates:
  1. Pinus sylvestris (ID: 4892) - Score: 98% ✅ AUTO-MATCH
  2. Pinus sylvestris var. lapponica (ID: 4893) - Score: 78%
  3. Pinus cembra (ID: 4891) - Score: 45%
```

---

### 3. Review and Refine

**Interactive Grid:**

| Your Value | Auto-Match | Score | Status | SEAD ID |
|------------|------------|-------|--------|---------|
| Pinus sylvestris L. | Pinus sylvestris | 98% | ✅ Matched | 4892 |
| Betula sp. | Betula pubescens | 82% | ⚠️ Review | 3214 |
| Corylus | *No match* | - | ❌ Manual | - |

**Actions:**
- ✅ Accept auto-matches (already done!)
- 🔍 Review moderate-confidence matches
- 🖊️ Manually select correct candidate
- 🚫 Mark as "local-only" (won't match)
- 💬 Add notes for documentation

---

### 4. Save and Apply

**Saved Mappings:**

```yaml
mapping:
  - source_value: "Pinus sylvestris L."
    sead_id: 4892
    confidence: 0.98
    notes: "Auto-matched"
  
  - source_value: "Betula sp."
    sead_id: 3214
    confidence: 0.82
    notes: "Reviewed and accepted by user"
  
  - source_value: "Local sample X"
    sead_id: null
    will_not_match: true
    notes: "Project-specific code, not in SEAD"
```

**Benefits:**
- 💾 Saved in project configuration
- 🔁 Reused for future data deliveries
- 📝 Fully documented and traceable
- 🤝 Shareable with colleagues

---

### Real-World Example: Taxon Reconciliation

**Scenario: 500 Unique Taxon Names**

**Without Reconciliation:**
- ⏱️ Lookup each in SEAD manually
- 🔍 Deal with spelling variants
- 📊 Maintain separate mapping spreadsheet
- ❌ Prone to errors and inconsistencies
- **Time:** ~2-3 days

**With Shape Shifter Reconciliation:**
- ⏱️ Configure specification: 15 minutes
- 🤖 Run auto-reconciliation: 2 minutes
- 🔍 Review flagged items (~50): 30 minutes
- ✅ High-quality, documented mappings
- **Time:** ~1 hour, **reusable forever**

---

### Geographic Reconciliation

**Special Feature for Sites:**

**Your Data:**
```
Site: "Lake Storsjön"
Latitude: 63.1234
Longitude: 14.5678
```

**Reconciliation Includes:**
- 📛 Name matching (fuzzy)
- 📍 Geographic distance calculation
- 🗺️ Proximity threshold checking
- 🎯 Combined confidence score

**Result:**
```
Candidate: "Storsjön, Jämtland" (ID: 1523)
  Name Match: 92%
  Distance: 0.3 km
  Combined Score: 97% ✅ AUTO-MATCH
```

---

### Best Practices

**Setup:**
- ✅ Start with lookup tables (controlled vocabularies)
- ✅ Configure high auto-accept threshold (95%+)
- ✅ Set moderate review threshold (70-80%)
- ✅ Test on small sample first

**Review Process:**
- 🔍 Always review flagged items
- 📝 Add notes for future reference
- ✅ Accept only when confident
- 🚫 Mark unmatchable items clearly

**Maintenance:**
- 🔄 Rerun when new SEAD entities added
- 📊 Review statistics for quality
- 💬 Share mappings across projects
- 📚 Document special cases

---

### Integration with Workflow

**Complete Pipeline:**

```
1. Define Entities
   ↓
2. Configure Foreign Keys
   ↓
3. Validate Structure
   ↓
4. **Run Reconciliation** ← Maps to SEAD IDs
   ↓
5. Preview with SEAD IDs
   ↓
6. Execute & Export
```

**Result:** Data ready for SEAD with proper identity resolution!

---

# Part 4: Live Walkthrough

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Scenario: Arbodat Integration

**Your Situation:**
- Arbodat database (MS Access)
- Contains: samples, sites, taxonomic data
- Need to: Load into SEAD for regional analysis

**Traditional Approach:** 
- Export to Excel, manual mapping, SQL scripts = *days of work*

**Shape Shifter Approach:**
- Configure once = *hours*, reuse = *minutes*

---

## Step 1: Create Project

**Action:**
1. Open Shape Shifter web interface
2. Click "Projects" in sidebar navigation
3. Click "New Project" button
4. Name: `arbodat_integration`
5. Select template or start blank
6. Click "Create"

**Result:**
- New YAML configuration created
- Automatic timestamped backup system enabled
- Project opens in tabbed interface
- Ready to configure entities and data sources

---

## Step 2: Configure Data Source

**Add MS Access Connection:**

```yaml
data_sources:
  arbodat:
    driver: ucanaccess
    database: ./projects/Arbodat_2024.mdb
```

**Visual Form:**
- Select "MS Access (UCanAccess)"
- Browse to database file
- Test connection
- See available tables

---

## Step 3: Define First Entity

**Sample Type Lookup:**

```yaml
entities:
  sample_type:
    type: sql
    data_source: arbodat
    query: "SELECT type_id, type_name FROM SampleTypes"
    keys: [type_name]
    surrogate_id: sample_type_id
```

**Form Editor:**
- Entity name: `sample_type`
- Type: SQL
- Select data source: `arbodat`
- Write simple SELECT query
- Define keys

---

## Step 4: Add Related Entity

**Samples with Foreign Key:**

```yaml
  sample:
    type: sql
    data_source: arbodat
    query: "SELECT * FROM Samples"
    keys: [sample_name, site_code]
    surrogate_id: sample_id
    foreign_keys:
      - entity: sample_type
        local_keys: [sample_type_name]
        remote_keys: [type_name]
        how: left
        constraints:
          cardinality: many_to_one
```

---

## Step 5: Validate Configuration

**Navigate to Validation Tab:**

**Click "Validate All" button:**

**Multi-Level Results:**
```
✅ Structural validation passed
  - YAML syntax valid
  - All entities defined
  - No circular dependencies

✅ Data validation passed
  - All columns exist in sources
  - Foreign keys valid
  
⚠️ Entity-specific warnings:
  - Column 'site_code' has 3 null values in 'sample'
  
ℹ️ Summary: 1,247 samples will be processed
```

**Actions:**
- Review warnings by entity
- View auto-fix suggestions
- Preview and apply fixes
- Re-validate after changes

---

## Step 6: Test Foreign Key

**Click "Test Join" on sample_type relationship:**

**Statistics:**
```
Total Rows: 1,247
Matched: 1,235 (99.0%)
Unmatched: 12 (1.0%)

Cardinality: ✅ Many-to-one satisfied
Unique Left: ✅ No duplicates
```

**Sample Preview:**
- See matched data
- Identify unmatched values
- Fix source data or configuration

---

## Step 7: Preview Results

**Entity Preview for 'sample':**

| sample_id | sample_name | sample_type_id | site_id | depth_cm |
|-----------|-------------|----------------|---------|----------|
| 1 | ABO-001 | 3 | 45 | 15.5 |
| 2 | ABO-002 | 3 | 45 | 22.0 |
| 3 | ABO-003 | 5 | 46 | 8.3 |

**Verify:**
- ✅ IDs generated correctly
- ✅ Foreign keys resolved
- ✅ Data looks clean
- ✅ Ready for export

---

## Step 8: Reconcile Taxon Names

**Navigate to Reconciliation Tab:**

**Dual-Mode Editor:**
- 📝 **Form View**: Visual configuration with dropdowns
- 🖊️ **YAML View**: Direct YAML editing with Monaco
- 🔄 Switch seamlessly between modes

**Configure in Form View:**
1. Select entity: `sample_taxon`
2. Select field: `taxon_id`
3. Service type: `Taxon`
4. Property mappings: `taxon_name` → `taxon_name`
5. Auto-accept threshold: `0.95`
6. Review threshold: `0.70`

**Click "Run Auto-Reconcile":**
- 🔍 Found 45 unique taxon names
- ✅ Auto-matched: 42 (93%)
- ⚠️ Need review: 2 (4%)
- ❌ No match: 1 (2%)

**Interactive Review Grid:**
- ✅ Auto-matches already applied
- 🔍 Review "Betula sp." → Select "Betula pubescens" from candidates
- 🚫 Mark "Local code X" as "will not match"
- 💾 Save mappings to project configuration

**Result:** All taxon names resolved to SEAD IDs!

---

## Step 9: Configure Dispatch

**Navigate to Dispatch Tab:**

**Configure Target System:**

In project YAML (or use form editor later):
```yaml
options:
  ingesters:
    sead:
      target_data_source: sead_staging_db
      submission_name: arbodat_2026_01
      data_types: [dendro]
      policies:
        ignore_columns: ["temp_*"]
        register: true
        explode: false
```

**Dispatch Form:**
1. Ingester auto-selected (if only one configured)
2. View target data source details
3. Verify submission settings
4. Click "Validate Data" (optional pre-check)
5. Click "Dispatch"

**Result:**
- 🔄 Validating... (5 seconds)
- ✅ Validation passed
- 📤 Dispatching to SEAD Clearinghouse... (30 seconds)
- ✅ Success! 1,247 samples dispatched
- 📊 View dispatch report

---

# Part 5: Your Benefits

---

## For Data Providers

**Time Savings:**
- ⏱️ Initial setup: Few hours
- ⏱️ Updates: Minutes
- ⏱️ No more manual transformations

**Quality Improvements:**
- ✅ Validation catches errors early
- ✅ Consistent transformations
- ✅ Reproducible results
- ✅ Documentation included

**Flexibility:**
- 🔄 Reuse for similar datasets
- 📋 Share configurations with colleagues
- 🔧 Modify without programming

---

## For SEAD Team

**Data Quality:**
- ✅ Standardized format
- ✅ Pre-validated data
- ✅ Traceable transformations
- ✅ Error reports included

**Efficiency:**
- 🚀 Faster data ingestion
- 📉 Less manual QA needed
- 🤝 Self-service for providers
- 📊 Better data documentation

**Sustainability:**
- 📚 Knowledge preserved in configs
- 👥 Transferable between team members
- 🔁 Repeatable processes
- 🔬 Auditable workflows

---

## Real Impact

**Before Shape Shifter:**
```
New dataset arrives
  ↓
3 days: Manual transformation
  ↓
1 day: Manual ID lookups in SEAD
  ↓
1 day: Error correction
  ↓
1 day: QA and validation
  ↓
Finally: Import to SEAD
───────────────────
Total: ~6 days per dataset
```

**With Shape Shifter:**
```
New dataset arrives
  ↓
2 hours: Configure entities & data sources (first time)
  ↓
1 hour: Configure reconciliation & review matches
  ↓
30 minutes: Configure dispatch settings
  ↓
5 minutes: Validate → Dispatch to SEAD
───────────────────
Total: ~3.5 hours first time
       ~15 minutes for repeat deliveries (just re-dispatch!)
```

---

# Part 6: Getting Started

---

## System Access

**Web Application:**
- 🌐 URL: `http://sead-server:5173`
- 🔐 Login with SEAD credentials
- 💻 Works in any modern browser
- 📱 Responsive interface

**Backend API:**
- 🔌 `http://sead-server:8012`
- 📚 Full API documentation
- 🤖 Automation support

---

## Learning Resources

**Documentation:**
1. 📖 **User Guide** - Complete feature documentation
2. 🎓 **Tutorial** - Step-by-step walkthrough
3. 🔧 **Configuration Guide** - YAML syntax reference
4. ❓ **FAQ** - Common questions

**Access:**
- In-app: Click "Help" in navigation
- GitHub: `docs/` directory
- Examples: `configurations/` directory

---

## Example Projects

**Available Templates:**

1. **Arbodat Integration** - Tree-ring database
2. **Ceramic Analysis** - Pottery classification
3. **Site Survey** - Archaeological site data
4. **Radiocarbon** - Dating sample processing
5. **Dendro Samples** - Tree-ring samples

**Location:** `projects/` directory

**Use:**
- Open and study structure
- Copy and modify for your data
- Learn best practices

---

## Support & Help

**Get Assistance:**

💬 **In-App Help**
- Tooltips on all buttons
- Context-sensitive help
- Validation error suggestions

📧 **SEAD Team**
- Email: sead-support@example.com
- Response: 1-2 business days

🐛 **Report Issues**
- GitHub Issues
- Include error details
- Attach configuration (if possible)

👥 **Community**
- Monthly user meetings
- Share configurations
- Best practices discussions

---

## Next Steps

**This Week:**
1. 🔐 Request access credentials
2. 📚 Read User Guide introduction
3. 🎮 Explore example projects
4. 💭 Identify one dataset to try

**This Month:**
1. 🛠️ Create your first project
2. ✅ Validate and test
3. 📤 Execute and export
4. 💬 Share feedback with SEAD team

**This Year:**
1. 🔄 Migrate regular data deliveries
2. 📋 Build project library
3. 👥 Train colleagues
4. 🎯 Improve data quality

---

# Part 7: Q&A

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Common Questions

**Q: Do I need programming skills?**
A: No! Basic tasks use visual forms. YAML is simple to learn. Examples provided.

**Q: What if my data structure is complex?**
A: Shape Shifter handles complex relationships, nested data, and multi-source integration.

**Q: Can I test without affecting SEAD?**
A: Yes! Preview and validate locally. Export to files first. Full control.

**Q: What about sensitive data?**
A: Data never leaves your infrastructure. You control all access.

**Q: Is it stable for production use?**
A: v0.1.0 released. Active development. Production-ready for validated workflows.

**Q: How does reconciliation handle ambiguous names?**
A: Reconciliation service returns multiple candidates ranked by confidence. You review and choose the correct match, or mark as unmatchable. Geographic coordinates help for sites.

**Q: What if SEAD doesn't have my taxon/site?**
A: Mark as "will not match" to use your local identifier. Or request SEAD team to add the entity, then rerun reconciliation.

**Q: Are reconciliation mappings reusable?**
A: Yes! Saved in your project config. Rerun on new data to apply existing mappings + reconcile new values.

---

## Technical Questions Welcome!

**Topics We Can Discuss:**

- 🔧 Specific data integration challenges
- 📊 Complex transformation requirements  
- 🗄️ Database connection setup
- 🔗 Foreign key relationship configuration
- 🎯 Identity reconciliation strategies
- ✅ Validation customization
- 🚀 Performance optimization
- 🤝 Integration with existing workflows

**Your Questions?**

---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

# Thank You!

## Let's Transform Data Integration Together

**Contact Information:**
- 📧 Email: sead-team@example.com
- 🌐 Web: https://sead.se
- 💻 GitHub: humlab-sead/sead_shape_shifter
- 📚 Docs: https://github.com/humlab-sead/sead_shape_shifter/docs

**Remember:**
- Start small, iterate quickly
- Validation is your friend
- Community support available
- Your feedback shapes development

---

## Appendix: Quick Reference

**Essential YAML Structure:**

```yaml
# Project metadata
name: my_project
version: 1.0

# Data source connections
data_sources:
  my_db:
    driver: postgresql
    host: localhost
    database: mydata

# Entity definitions
entities:
  my_entity:
    type: sql
    data_source: my_db
    query: "SELECT * FROM table"
    keys: [id]
    surrogate_id: entity_id
    foreign_keys:
      - entity: other_entity
        local_keys: [fk_col]
        remote_keys: [pk_col]
```

---

## Appendix: Keyboard Shortcuts

**Editor:**
- `Ctrl+S` - Save configuration
- `Ctrl+F` - Find in file
- `Ctrl+/` - Toggle comment
- `Alt+Up/Down` - Move line

**Navigation:**
- Click entity in tree → Jump to definition
- `Ctrl+Click` link → Open reference
- `F12` - Browser DevTools

**Validation:**
- Click "Validate All" for full check
- Right-click entity → Validate Entity

---

## Appendix: Architecture

```
┌────────────────────────────────────────────────┐
│         Web Browser (Vue 3 + Vuetify)          │
│  ┌──────────────────────────────────────────┐  │
│  │  Project Detail (Tabbed Interface)       │  │
│  │  - Entities  - Dependencies  - Dispatch  │  │
│  │  - Validation  - Reconciliation  - YAML  │  │
│  └────────────┬─────────────────────────────┘  │
│  ┌────────────┴─────────────────────────────┐  │
│  │  Monaco Editor | Cytoscape.js | Pinia    │  │
│  └────────────┬─────────────────────────────┘  │
└───────────────┼────────────────────────────────┘
                │ REST API
                ▼
┌────────────────────────────────────────────────┐
│         FastAPI Backend (Python)               │
│  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Validation  │  │  ShapeShift Service    │ │
│  │   Service    │  │  (3-tier cache)        │ │
│  └──────────────┘  └────────────────────────┘ │
│  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Reconciliation│ │  Ingester Registry     │ │
│  │   Service    │  │  (Dispatchers)         │ │
│  └──────────────┘  └────────────────────────┘ │
└────────────────────┬───────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│         Data Sources & Targets                 │
│  PostgreSQL | SQLite | MS Access | CSV | Excel │
│  SEAD Clearinghouse | Reconciliation Services  │
└────────────────────────────────────────────────┘
```

---

## Appendix: Docker Deployment

**Containerized Deployment:**

Shape Shifter can be deployed as a Docker container for production use:

```bash
# Build and start container
make docker-build
make docker-start

# Access at http://localhost:8012
```

**Hot-Patching Frontend:**

During development or for quick fixes, you can rebuild and patch the frontend without container rebuild:

```bash
# Rebuild frontend and patch running container
make docker-patch-frontend
```

**What It Does:**
1. 🔨 Rebuilds Vue 3 frontend (production mode, skip type checks)
2. 📦 Bundles assets with Vite
3. 🚀 Copies `dist/` to running container
4. ⚡ No container restart needed - instant update

**Use Cases:**
- Fix UI bugs in production
- Update logos or branding
- Quick CSS/styling adjustments
- Test frontend changes before full rebuild

**Container Architecture:**
- Multi-stage Docker build
- Frontend served by FastAPI backend
- UCanAccess for MS Access support
- Non-root user for security
- Health checks and auto-restart

---
