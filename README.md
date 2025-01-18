<img src="images/city-update-logo.svg" width="100" alt="CityUpdate Boston Logo" align="right"/>

# CityUpdate Boston

CityUpdate Boston provides AI-generated summaries of Boston's performance metrics from its [CityScore dashboard](https://www.boston.gov/departments/analytics-team/cityscore). This is an independent project and not an official City of Boston website.

## Overview

This project automatically generates daily analyses of Boston's municipal performance metrics using:

- Python scripts to fetch and process data from Boston's open data portal
- Claude (Anthropic's LLM) to generate natural language analysis
- HTML templates to create a static website

## Components

- `generate_metrics.py`: Fetches latest CityScore data from Boston's API
- `generate_analysis.py`: Uses Claude to analyze metrics and generate insights
- `template.html`: Base template for the static site
- `metric_definitions.csv`: Metadata about each metric being tracked
- `system_prompt.txt`: Prompt provided with the data to the LLM

## Getting Started

1. Install dependencies:
```bash
pip install anthropic httpx jinja2
```

2. Set up environment variables:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

3. Run the scripts:
```bash
python generate_metrics.py    # Fetches latest data
python generate_analysis.py   # Generates analysis
```

The generated site will be available in the `docs` directory.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

The content has not been evaluated for accuracy. This is not an official City of Boston website.