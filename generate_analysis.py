from anthropic import Anthropic
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

claude_model = 'claude-haiku-4-5-20251001'
system_prompt_file = 'data/system_prompt.txt'
metrics_file = 'data/cityscore_metrics.json'
base_template = 'templates/template.html'
dates_template = 'templates/all_dates_template.html'

def strftime_filter(date, format='%A, %B %d, %Y'):
    if isinstance(date, str):
        # If date is a string, try to parse it first
        date = datetime.strptime(date, '%Y-%m-%d')  # Adjust format based on your input
    return date.strftime(format)

def find_previous_date(current_date, docs_path):
    """Find the most recent date before the current date that has an analysis file"""
    # Get all existing date files
    date_files = []
    for f in docs_path.glob('????-??-??.html'):
        try:
            date = datetime.strptime(f.stem, '%Y-%m-%d')
            if date < datetime.strptime(current_date, '%Y-%m-%d'):
                date_files.append(f.stem)
        except ValueError:
            continue
    
    # Sort dates in reverse chronological order
    date_files.sort(reverse=True)
    
    # Return the most recent date or None if no previous dates exist
    return date_files[0] if date_files else None

def generate_html(analysis, metrics_date, lm_model):
    env = Environment(loader=FileSystemLoader('.'))
    env.filters['strftime'] = strftime_filter
    template = env.get_template(base_template)
    
    # Find the previous date
    docs_path = Path('docs')
    previous_date = find_previous_date(metrics_date, docs_path)
    
    return template.render(
        metrics_date=metrics_date,
        analysis=analysis,
        lm_model=lm_model,
        generated_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        previous_date=previous_date
    )

def generate_all_dates_page():
    """Generate the all-dates.html page listing all available analyses"""
    env = Environment(loader=FileSystemLoader('.'))
    env.filters['strftime'] = strftime_filter
    template = env.get_template(dates_template)
    
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
    try:
        print("\n=== Starting CityUpdate Analysis Generation ===")
        
        # Read the metrics
        print("\n📊 Reading metrics file...")
        try:
            with open(metrics_file, "r") as f:
                metrics = json.load(f)
            print("✅ Successfully loaded metrics data")
        except FileNotFoundError:
            print("❌ ERROR: cityscore_metrics.json not found!")
            raise
        except json.JSONDecodeError:
            print("❌ ERROR: Invalid JSON in metrics file!")
            raise
            
        # Get analysis from Claude
        print("\n🤖 Initializing Claude API...")
        try:
            anthropic = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            with open(system_prompt_file, "r") as f:
                system_prompt = f.read()
            print("✅ Successfully loaded system prompt")
            
            print("\n📝 Generating analysis with Claude...")
            message = anthropic.messages.create(
                model=claude_model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": json.dumps(metrics)}]
            )
            print("✅ Successfully received analysis from Claude")
            
        except KeyError:
            print("❌ ERROR: ANTHROPIC_API_KEY not found in environment!")
            raise
        except Exception as e:
            print(f"❌ ERROR calling Claude API: {str(e)}")
            raise
            
        analysis = message.content[0].text
        
        # Extract date from metrics
        print("\n📅 Extracting metrics date...")
        try:
            calc_ts = metrics['311 CALL CENTER PERFORMANCE']['calculated_at']

            # Try parsing with microseconds first (old format), then without (new format)
            try:
                metrics_date = datetime.strptime(calc_ts, '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')
            except ValueError:
                # New API format: 2026-01-21T11:31:24
                metrics_date = datetime.strptime(calc_ts, '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d')

            print(f"✅ Analysis date: {metrics_date}")
        except KeyError:
            print("❌ ERROR: Could not find calculated_at timestamp in metrics!")
            raise
        except ValueError as e:
            print(f"❌ ERROR: Invalid timestamp format in metrics: {e}")
            raise
            
        # Generate HTML
        print("\n🔨 Generating HTML...")
        html = generate_html(analysis, metrics_date, claude_model)
        print("✅ Successfully generated HTML")
        
        # Save files
        print("\n💾 Saving generated files...")
        try:
            os.makedirs("docs", exist_ok=True)
            
            # Save today's analysis
            today_file = f"docs/{metrics_date}.html"
            with open(today_file, "w") as f:
                f.write(html)
            print(f"✅ Saved analysis to {today_file}")
            
            # Update index
            with open("docs/index.html", "w") as f:
                f.write(html)
            print("✅ Updated index.html")
            
            # Generate all-dates page
            print("\n📑 Generating all-dates page...")
            generate_all_dates_page()
            print("✅ Updated all-dates.html")
            
        except Exception as e:
            print(f"❌ ERROR saving files: {str(e)}")
            raise
            
        print("\n✨ Analysis generation completed successfully! ✨\n")
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: Analysis generation failed!")
        print(f"Error details: {str(e)}")
        raise

if __name__ == "__main__":
    main()