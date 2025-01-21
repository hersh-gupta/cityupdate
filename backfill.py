import httpx
import json
from datetime import datetime, timedelta
from pathlib import Path
from generate_analysis import generate_html, claude_model
from anthropic import Anthropic
import os
from urllib.parse import quote
import time
from jinja2 import Environment, FileSystemLoader

def strftime_filter(date, format='%A, %B %d, %Y'):
    if isinstance(date, str):
        # If date is a string, try to parse it first
        date = datetime.strptime(date, '%Y-%m-%d')  # Adjust format based on your input
    return date.strftime(format)

def get_metrics_for_date(date):
    """Get metrics for a specific date using the CityScore API"""
    base_url = 'https://data.boston.gov/api/3/action/datastore_search_sql'
    
    sql_query = f"""
    SELECT * 
    FROM "dd657c02-3443-4c00-8b29-56a40cfe7ee4" 
    WHERE score_calculated_ts >= '{date} 00:00:00'
    AND score_calculated_ts < '{date} 23:59:59.999999'
    """
    
    encoded_sql = quote(sql_query)
    full_url = f"{base_url}?sql={encoded_sql}"
    
    response = httpx.get(full_url, timeout=10.0)
    response.raise_for_status()
    return response.json()

def process_metrics(raw_data):
    """Convert raw API data into the expected metrics format"""
    metrics = {}
    for record in raw_data['result']['records']:
        metric_name = record['metric_name']
        metrics[metric_name] = {
            'title': metric_name,
            'definition': 'No definition available',
            'calculated_at': record['score_calculated_ts'],
            'target': record['target'],
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

def generate_all_dates_page():
    """Generate the all-dates.html page listing all available analyses"""
    env = Environment(loader=FileSystemLoader('.'))
    env.filters['strftime'] = strftime_filter
    template = env.get_template('all_dates_template.html')
    
    # Get all date files
    docs_path = Path("docs")
    date_files = []
    for f in docs_path.glob("????-??-??.html"):
        try:
            datetime.strptime(f.stem, "%Y-%m-%d")
            date_files.append(f.stem)
        except ValueError:
            continue
    
    # Sort dates in reverse chronological order
    date_files.sort(reverse=True)
    
    # Generate the page
    html = template.render(dates=date_files)
    
    with open("docs/all-dates.html", "w") as f:
        f.write(html)

def main():
    # Initialize Anthropic client
    anthropic = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    # Load system prompt
    with open("system_prompt.txt", "r") as f:
        system_prompt = f.read()
    
    # Create docs directory if it doesn't exist
    Path("docs").mkdir(exist_ok=True)
    
    # Generate analyses for each day in January 2025
    start_date = "2025-01-15"
    end_date = "2025-01-20"  # Or current date
    
    current_date = start_date
    while current_date <= end_date:
        print(f"\nProcessing date: {current_date}")
        
        try:
            # Check if analysis already exists
            if Path(f"docs/{current_date}.html").exists():
                print(f"Analysis already exists for {current_date}, skipping...")
                current_date = (datetime.strptime(current_date, "%Y-%m-%d") + 
                              timedelta(days=1)).strftime("%Y-%m-%d")
                continue
            
            # Get metrics for the date
            raw_data = get_metrics_for_date(current_date)
            
            if not raw_data['result']['records']:
                print(f"No data available for {current_date}")
                current_date = (datetime.strptime(current_date, "%Y-%m-%d") + 
                              timedelta(days=1)).strftime("%Y-%m-%d")
                continue
            
            # Process metrics
            metrics = process_metrics(raw_data)
            
            # Generate analysis using Claude
            message = anthropic.messages.create(
                model=claude_model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": json.dumps(metrics)}]
            )
            
            analysis = message.content[0].text
            
            # Generate and save HTML
            html = generate_html(
                analysis=analysis,
                metrics_date=current_date,
                lm_model=claude_model
            )
            
            with open(f"docs/{current_date}.html", "w") as f:
                f.write(html)
                
            print(f"Successfully generated analysis for {current_date}")
            
            # Generate updated all-dates page
            generate_all_dates_page()
            
            # Sleep to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing {current_date}: {str(e)}")
        
        # Move to next date
        current_date = (datetime.strptime(current_date, "%Y-%m-%d") + 
                       timedelta(days=1)).strftime("%Y-%m-%d")

if __name__ == "__main__":
    main()