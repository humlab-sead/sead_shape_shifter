# Presentation Images

This directory contains images for the SEAD Workshop presentation.

## Directory Structure

```
docs/images/
├── README.md                  # This file
├── diagrams/                 # System diagrams (SVG files)
│   ├── 1-the-problem-data-integration-chaos.svg
│   ├── 2-the-solution-shape-shifter-integration-platform.svg
│   ├── 4-system-architecture.svg
│   ├── 9-caching-strategy-shapeshift-service.svg
│   └── ... (15 total diagrams)
├── screenshots/              # Application screenshots
│   ├── project-editor.png   # Main project editor interface
│   ├── validation-tab.png   # Validation results view
│   ├── dependency-graph.png # Dependency visualization
│   └── reconciliation.png   # Reconciliation interface
├── data-chaos.png           # Example of messy data files
└── shape-shifter-logo.svg   # Application logo

```

## Diagram SVG Files

The diagrams in `diagrams/` are automatically generated from the Mermaid diagrams in `SYSTEM_DIAGRAMS.md`.

### Regenerating Diagrams

To extract and convert all diagrams:

```bash
# Extract Mermaid code from SYSTEM_DIAGRAMS.md
make diagrams-extract

# Convert to SVG using mermaid.ink API
make diagrams-to-svg

# List all created diagrams
make diagrams-list
```

**Note**: The conversion uses the mermaid.ink online API, which may rate-limit requests. If some diagrams fail to convert, wait a few minutes and run `make diagrams-to-svg` again - it will only convert missing files.

### Available Diagrams

1. **1-the-problem-data-integration-chaos.svg** - Current data integration challenges
2. **2-the-solution-shape-shifter-integration-platform.svg** - Shape Shifter solution overview
3. **3-complete-user-workflow.svg** - End-to-end user workflow
4. **4-system-architecture.svg** - Technical architecture
5. **5-tabbed-project-interface.svg** - UI component layout
6. **6-data-transformation-pipeline.svg** - Processing pipeline
7. **7-reconciliation-workflow.svg** - Identity reconciliation flow
8. **8-validation-system-architecture.svg** - Validation components
9. **9-caching-strategy-shapeshift-service.svg** - Caching implementation
10. **10-time-savings-comparison.svg** - Before/after comparison
11. **11-key-features-overview.svg** - Feature highlights
12. **12-user-personas-use-cases.svg** - User scenarios
13. **13-technology-stack.svg** - Technologies used
14. **14-deployment-architecture.svg** - Deployment options
15. **15-registry-pattern-extensibility.svg** - Extensibility architecture

## Adding Images to Presentation

### 1. Background Images (Right/Left Split)

```markdown
---

## Slide Title

![bg right:40%](docs/images/screenshot.png)

Content on the left side...
```

### 2. Inline Images with Size Control

```markdown
![w:600](docs/images/diagram.png)
![h:400](docs/images/chart.png)
![w:800 h:600](docs/images/screenshot.png)
```

### 3. Full Background Images

```markdown
---

![bg](docs/images/hero-background.jpg)

# Slide with background
```

### 4. Fit Background (Maintains Aspect Ratio)

```markdown
![bg fit](docs/images/diagram.png)
```

## Recommended Specifications

- **Screenshots**: 1920x1080 or 1280x720 (16:9 ratio)
- **Diagrams**: SVG (vector) or high-res PNG (300 DPI)
- **Logos**: SVG preferred for scaling
- **Photos**: JPG (compressed) or PNG (transparent backgrounds)
- **File size**: Keep under 1MB per image for faster loading

## Taking Screenshots

### Project Editor
1. Open Shape Shifter at http://localhost:8012
2. Load an example project (e.g., arbodat)
3. Maximize browser window (1920x1080)
4. Take screenshot showing:
   - Left sidebar with entity tree
   - Center editor with YAML code
   - Right panel with preview/validation

### Validation Tab
1. Navigate to Validation tab
2. Click "Validate All"
3. Show validation results with:
   - Green checkmarks for passed validations
   - Warning/error messages if any
   - Entity-level breakdown

### Reconciliation Tab
1. Open Reconciliation tab
2. Show the dual-mode editor (Form/YAML)
3. Display reconciliation results grid
4. Highlight matched vs. review-needed items

### Dependency Graph
1. Open Dependencies tab
2. Show Cytoscape.js graph visualization
3. Capture full graph with entity nodes and edges
4. Include legend/controls if visible

## Image Optimization

Before adding images:

```bash
# Optimize PNG files
pngquant --quality=65-80 screenshot.png

# Optimize JPG files
jpegoptim --max=85 photo.jpg

# Convert to WebP (modern format, smaller size)
cwebp -q 80 screenshot.png -o screenshot.webp
```

## Example References in Presentation

Current image placeholders in `PRESENTATION_SEAD_WORKSHOP.md`:

- Line ~60: Data chaos background (`data-chaos.png`)
- Line ~140: Shape Shifter logo (`shape-shifter-logo.svg`)
- Line ~220: Project editor screenshot (`screenshots/project-editor.png`)

Uncomment the `![bg ...]` lines and add your images to activate them.
