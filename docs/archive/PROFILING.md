# Performance Profiling Guide

Quick reference for profiling Shape Shifter tests to find performance bottlenecks.

## Quick Start

### Visual Profiling (Recommended)
```bash
# Profile any test and generate interactive flame graph
make profile TEST="tests/process/test_workflow.py::test_access_database_csv_workflow"

# View the results
xdg-open profile.svg
# Or upload profile.svg to https://www.speedscope.app/
```

### Statistical Profiling
```bash
# Get text-based statistics showing top 30 functions
make profile-stats TEST="tests/your_test.py::test_name"
```

## Reading Flame Graphs

- **Width** = Time spent in that function (wider = slower)
- **Height** = Call stack depth (how deep the function calls go)
- **Colors** = Different modules/files
- **Look for wide bars** = Performance bottlenecks

## Common Bottlenecks to Check

1. **Database queries** - `await loader.load()`
2. **Excel/CSV file I/O** - Reading and writing data files
3. **DataFrame operations** - Pandas transformations
4. **Foreign key validation** - Constraint checking
5. **Deep copying** - Configuration object mutations

## Example Results

From profiling `test_access_database_csv_workflow`:
- Total runtime: ~9-14 seconds
- Database operations: ~40-50% of time
- Excel writing: ~20-30% of time
- DataFrame transforms: ~10-20% of time

## More Details

See [Developer Guide - Performance Profiling](docs/DEVELOPER_GUIDE.md#performance-profiling) for:
- Additional profiling methods
- Line-by-line profiling
- Memory profiling
- Optimization workflow
- Interpreting detailed statistics
