import httpx
import csv
import json
from urllib.parse import quote
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

metric_defs_file = 'metric_definitions.csv'
output_file = 'cityscore_metrics.json'
base_url: str = 'https://data.boston.gov/api/3/action/datastore_search_sql'
sql_query: str = 'SELECT * from "dd657c02-3443-4c00-8b29-56a40cfe7ee4" WHERE "latest_score_flag" LIKE \'1\''

def load_metric_definitions(file_path: str) -> Dict[str, Dict[str, str]]:
    """Load metric definitions from CSV file"""
    try:
        definitions = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                definitions[row['metric_name']] = {
                    'metric_title': row['metric_title'],
                    'definition': row['definition']
                }
        return definitions
    except FileNotFoundError:
        print(f"❌ Definition file {file_path} not found!")
        raise
    except Exception as e:
        print(f"❌ Error loading definitions: {str(e)}")
        raise

def get_latest_score(url: str, sql: str) -> Dict[str, Any]:
    """Get the latest CityScore via API"""
    try:
        encoded_sql = quote(sql, safe='')
        full_url = f"{url}?sql={encoded_sql}"
        
        print("  Sending API request...")
        start_time = datetime.now()
        resp = httpx.get(full_url, timeout=10.0)
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        print(f"  Request completed in {elapsed_time:.2f} seconds")
        
        resp.raise_for_status()
        return resp.json()
        
    except httpx.TimeoutException:
        print("❌ API request timed out after 10 seconds")
        raise
    except httpx.HTTPStatusError as e:
        print(f"❌ API returned error status {e.response.status_code}")
        raise
    except json.JSONDecodeError:
        print("❌ Invalid JSON in API response")
        raise
    except Exception as e:
        print(f"❌ API request failed: {str(e)}")
        raise

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
            
            if metric_name not in definitions:
                print(f"⚠️  Warning: No definition found for metric {metric_name}")
            
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
        
    except KeyError as e:
        print(f"❌ Missing required field in API response: {str(e)}")
        raise
    except Exception as e:
        print(f"❌ Error processing metrics: {str(e)}")
        raise

def needs_update(metrics: Dict[str, Any], docs_path: str = 'docs') -> bool:
    """Check if metrics need to be analyzed"""
    try:
        calc_ts = metrics['311 CALL CENTER PERFORMANCE']['calculated_at']
        metrics_date = datetime.strptime(calc_ts, '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')
        
        existing_file = Path(docs_path) / f"{metrics_date}.html"
        return not existing_file.exists()
        
    except Exception as e:
        print(f"❌ Error checking update status: {str(e)}")
        # If there's any error, return True to ensure we don't miss updates
        return True

def main() -> None:
    """Main function to fetch and process CityScore metrics"""
    print("\n=== Starting CityScore Metrics Collection ===")
    
    try:
        # Load metric definitions
        print("\n📚 Loading metric definitions...")
        definitions = load_metric_definitions(metric_defs_file)
        print(f"✅ Successfully loaded {len(definitions)} metric definitions")
        
        # Get metrics from API
        print("\n🌐 Fetching CityScore data from data.boston.gov...")
        raw_data = get_latest_score(base_url, sql_query)
        record_count = len(raw_data.get('result', {}).get('records', []))
        print(f"✅ Successfully retrieved {record_count} records from API")
        
        # Process metrics
        print("\n🔄 Processing metrics data...")
        metrics = parse_metric_scores(raw_data, definitions)
        metric_count = len(metrics)
        print(f"✅ Successfully processed {metric_count} metrics")
        
        # Save to file
        print("\n💾 Saving metrics to file...")
        with open(output_file, 'w', encoding='utf8') as f:
            json.dump(metrics, f, indent=2)
        file_size = Path(output_file).stat().st_size / 1024  # Size in KB
        print(f"✅ Successfully saved metrics to {output_file} ({file_size:.1f}KB)")
        
        # Check for updates
        print("\n🔍 Checking if analysis update is needed...")
        needs_new_analysis = needs_update(metrics)
        status = "🔄 Update needed" if needs_new_analysis else "⏭️ No update needed"
        print(f"\n{status}")
        # This specific format is needed for GitHub Actions
        print(f"\nNeeds analysis update: {needs_new_analysis}")
        
        print("\n✨ Metrics collection completed successfully! ✨\n")
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: Metrics collection failed!")
        print(f"Error details: {str(e)}")
        raise

if __name__ == "__main__":
    main()