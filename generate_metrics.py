import httpx
import csv
import json
from urllib.parse import quote
from typing import Dict, Any

metric_defs_file = 'metric_definitions.csv'
output_file = 'cityscore_metrics.json'

def load_metric_definitions(file_path: str) -> Dict[str, Dict[str, str]]:
    """Load metric definitions from CSV file"""
    definitions = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                definitions[row['metric_name']] = {
                    'metric_title': row['metric_title'],
                    'definition': row['definition']
                }
        return definitions
    except Exception as e:
        raise ValueError(f"Failed to load metric definitions: {str(e)}")

base_url: str = 'https://data.boston.gov/api/3/action/datastore_search_sql'
sql_query: str = 'SELECT * from "dd657c02-3443-4c00-8b29-56a40cfe7ee4" WHERE "latest_score_flag" LIKE \'1\''

def get_latest_score(url: str, sql: str) -> Dict[str, Any]:
    """Get the latest CityScore via API"""
    try:
        encoded_sql = quote(sql, safe='')
        full_url = f"{url}?sql={encoded_sql}"
        resp = httpx.get(full_url, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        raise httpx.HTTPError(f"HTTP request failed: {str(e)}")

def parse_metric_scores(data: Dict[str, Any], definitions: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    """Parse the raw CityScore data into a dictionary structure"""
    try:
        records = data['result']['records']
        metrics = {}
        
        for record in records:
            metric_name = record['metric_name']
            definition_data = definitions.get(metric_name, {
                'metric_title': metric_name,
                'definition': 'No definition available'
            })
            
            metrics[metric_name] = {
                'title': definition_data['metric_title'],
                'definition': definition_data['definition'],
                'calculated_at': record['score_calculated_ts'],
                'target': record['target'] if record['target'] else None,
                'metric_logic': record['metric_logic'],
                'scores': {
                    'day': {
                        'score': record['day_score'],
                        'numerator': record['day_numerator'],
                        'denominator': record['day_denominator']
                    },
                    'week': {
                        'score': record['week_score'],
                        'numerator': record['week_numerator'],
                        'denominator': record['week_denominator']
                    },
                    'month': {
                        'score': record['month_score'],
                        'numerator': record['month_numerator'],
                        'denominator': record['month_denominator']
                    },
                    'quarter': {
                        'score': record['quarter_score'],
                        'numerator': record['quarter_numerator'],
                        'denominator': record['quarter_denominator']
                    }
                }
            }
        
        return metrics
        
    except (KeyError, ValueError) as e:
        raise ValueError(f"Failed to parse metric data: {str(e)}")

def main() -> None:
    """Main function to fetch and process CityScore metrics"""
    try:
        # Load metric definitions first
        print(f"Reading defintions file {metric_defs_file}")
        definitions = load_metric_definitions(metric_defs_file)
        
        # Get and parse metric scores
        print("Getting CityScore data from https://data.boston.gov")
        raw_data = get_latest_score(base_url, sql_query)
        print("Formatting metrics")
        metrics = parse_metric_scores(raw_data, definitions)
        
        print("Saving file")
        # Write JSON to file with indentation for readability
        try: 
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2)
            print(f"Saved CityScore data as {output_file}")
        except Exception as e:
            print(f"An error occurred: {e}")
        

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()