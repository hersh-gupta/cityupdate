# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CityUpdate Boston is an AI-powered municipal analytics platform that automatically generates daily natural language analyses of Boston's performance metrics from the CityScore dashboard. The system:

1. Fetches real-time data from Boston's public API (data.boston.gov)
2. Uses Claude to generate human-readable insights from 23 municipal service metrics
3. Publishes static HTML pages with daily analyses to GitHub Pages

**Important:** This is an independent project, not an official City of Boston website.

## Development Commands

### Setup
```bash
# Install dependencies
pip install anthropic httpx jinja2

# Set environment variable (required for generate_analysis.py)
export ANTHROPIC_API_KEY="your-key-here"
```

### Running the Pipeline

```bash
# Step 1: Fetch latest metrics from Boston's API
python generate_metrics.py

# Step 2: Generate AI analysis and HTML output
python generate_analysis.py

# Historical backfill (for specific date ranges)
python backfill.py
```

### Testing Changes
There is no formal test suite. Validate changes by:
- Running the full pipeline and inspecting the generated HTML in `docs/`
- Checking that emoji-prefixed log messages show success (✅) not errors (❌)
- Verifying the generated `docs/index.html` renders correctly in a browser

## Architecture

### Data Flow
```
Boston CityScore API
  ↓
generate_metrics.py (fetch & process)
  ↓
data/cityscore_metrics.json
  ↓
generate_analysis.py (Claude LLM analysis)
  ↓
Jinja2 templating
  ↓
docs/ directory (HTML output)
  ↓
GitHub Pages (published)
```

### Key Files

**Python Scripts:**
- `generate_metrics.py` - Fetches and processes data from Boston's API
  - API endpoint: `https://data.boston.gov/api/3/action/datastore_search_sql`
  - Dataset ID: `dd657c02-3443-4c00-8b29-56a40cfe7ee4`
  - Filters for records where `latest_score_flag = 1`
  - Outputs to `data/cityscore_metrics.json`
  - Uses 10-second HTTP timeout via httpx

- `generate_analysis.py` - Generates AI analysis and renders HTML
  - Uses Claude model: `claude-3-5-sonnet-20241022`
  - Loads system prompt from `data/system_prompt.txt`
  - Renders Jinja2 templates from `templates/`
  - Creates three output files: `{date}.html`, `index.html`, `all-dates.html`
  - Implements navigation by finding previous analysis dates

- `backfill.py` - Historical data generation for date ranges
  - Similar to the main pipeline but accepts date parameters
  - Rate-limited with 1-second delays between API calls

**Data & Configuration:**
- `data/metric_definitions.csv` - Metadata for 23 metrics (titles, descriptions)
- `data/system_prompt.txt` - Comprehensive prompt for Claude defining:
  - How to interpret the 3 score calculation methods (current/historical, historical/current, target-based)
  - Analysis guidelines emphasizing concrete numbers over scores
  - Output format requirements (1-3 paragraphs, no speculation)

**Templates:**
- `templates/template.html` - Main page template with navigation, styling
- `templates/all_dates_template.html` - Archive listing template

**CI/CD:**
- `.github/workflows/run-analysis.yml` - Automated daily pipeline:
  - Runs at 20:00 UTC (3 PM EST, when metrics typically refresh)
  - Only generates new analysis if metrics date doesn't have existing HTML file
  - Auto-commits and pushes changes to trigger GitHub Pages deployment

### Metric Score Interpretation

The system tracks metrics using three calculation methods:

1. **Type A (current/historical):** `score = current / historical_average`
   - Example: Library Users at 1.74 = 74% above historical average

2. **Type B (historical/current):** `score = historical / current`
   - Example: BFD Incidents - lower is better, so higher score is better

3. **Type C (target-based):** `score = (numerator/denominator)/target` OR `target/median`
   - Example: 311 Call Center at 0.929 = achieving 92.9% of 95% target
   - Example: EMS Response with 7.5 min median vs 6 min target = 0.8

Each metric includes measurements across four time periods: day, week, month, quarter.

### Smart Update Detection

The pipeline includes a `needs_update()` function in `generate_metrics.py` that:
- Extracts the `calculated_at` timestamp from metrics
- Checks if `docs/{date}.html` already exists
- Returns `False` to skip analysis if file exists (saves API costs and time)
- This output is parsed by GitHub Actions to conditionally run `generate_analysis.py`

### Error Handling Pattern

Both main scripts follow this pattern:
- Emoji-prefixed console output (✅ success, ❌ error, ⚠️ warning, 🔄 processing)
- Try/except blocks with specific error types (FileNotFoundError, JSONDecodeError, HTTPStatusError, etc.)
- Always raise exceptions after logging to fail fast
- GitHub Actions uses `continue-on-error: false` to halt on failures

### Environment Variables

- `ANTHROPIC_API_KEY` - **Required** for `generate_analysis.py`, stored in GitHub Secrets
- No other environment configuration needed

## Code Patterns

### Date Handling
- Metrics API returns timestamps as: `YYYY-MM-DD HH:MM:SS.ffffff`
- Parse with: `datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')`
- File naming uses: `YYYY-MM-DD.html` format
- Jinja2 `strftime_filter` custom filter formats dates for display

### API Requests
- Always use `httpx.get()` with explicit `timeout=10.0` parameter
- URL-encode SQL queries with `urllib.parse.quote()`
- Check HTTP status with `resp.raise_for_status()`
- Expect JSON structure: `data['result']['records']`

### JSON Structure
The `cityscore_metrics.json` file structure:
```json
{
  "METRIC_NAME": {
    "title": "Human Readable Title",
    "definition": "Explanation of what the metric measures",
    "calculated_at": "2025-01-25 12:00:00.000000",
    "target": 95.0,  // or null
    "metric_logic": "target",
    "scores": {
      "day": {"score": 0.929, "numerator": 88.3, "denominator": 95.0},
      "week": {...},
      "month": {...},
      "quarter": {...}
    }
  }
}
```

### Template Rendering
- Use Jinja2 `Environment` with `FileSystemLoader('.')`
- Register custom filters with `env.filters['name'] = function`
- Pass `previous_date` for navigation links (or `None` for first analysis)
- Templates expect: `metrics_date`, `analysis`, `lm_model`, `generated_time`, `previous_date`

## Important Constraints

1. **No Test Framework:** Validate changes manually by running the full pipeline
2. **No Backwards Compatibility:** The project doesn't maintain compatibility with old data formats
3. **Single Source of Truth:** The `calculated_at` timestamp from the 311 metric determines the analysis date
4. **Static Site Only:** All output is pre-rendered HTML, no server-side logic
5. **Public Data Only:** All data comes from Boston's public open data portal
6. **Disclaimer Required:** Generated content has not been evaluated for accuracy

## Common Workflows

### Adding a New Metric
1. Add row to `data/metric_definitions.csv` with `metric_name`, `metric_title`, `definition`
2. No code changes needed - the system dynamically processes all metrics from the API
3. Warning will appear in logs if API returns a metric not in the CSV

### Modifying the Analysis Prompt
1. Edit `data/system_prompt.txt`
2. Changes apply to next `generate_analysis.py` run
3. Does not retroactively change historical analyses

### Changing the Claude Model
Update the `claude_model` variable in `generate_analysis.py`:
```python
claude_model = 'claude-3-5-sonnet-20241022'
```

### Manual Workflow Trigger
Visit GitHub Actions tab and use "Run workflow" button on `run-analysis.yml`
