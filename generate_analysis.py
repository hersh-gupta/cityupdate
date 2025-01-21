from anthropic import Anthropic
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import json
import os
from pathlib import Path

claude_model = 'claude-3-5-sonnet-20241022'

def strftime_filter(date, format='%A, %B %d, %Y'):
    if isinstance(date, str):
        # If date is a string, try to parse it first
        date = datetime.strptime(date, '%Y-%m-%d')  # Adjust format based on your input
    return date.strftime(format)

def generate_html(analysis, metrics_date, lm_model):
    env = Environment(loader=FileSystemLoader('.'))
    env.filters['strftime'] = strftime_filter
    template = env.get_template('template.html')
    
    # List existing analysis files to find the previous date
    docs_path = Path('docs')
    existing_dates = [f.stem for f in docs_path.glob('????-??-??.html')]
    existing_dates.sort()
    try:
        current_index = existing_dates.index(metrics_date)
        previous_date = existing_dates[current_index - 1] if current_index > 0 else None
    except ValueError:
        previous_date = None
    
    return template.render(
        metrics_date=metrics_date,
        analysis=analysis,
        lm_model=lm_model,
        generated_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        previous_date=previous_date
    )

def main():
    try:
        print("\n=== Starting CityUpdate Analysis Generation ===")
        
        # Read the metrics
        print("\n📊 Reading metrics file...")
        try:
            with open("cityscore_metrics.json", "r") as f:
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
            with open("system_prompt.txt", "r") as f:
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
            metrics_date = datetime.strptime(
                metrics['311 CALL CENTER PERFORMANCE']['calculated_at'], 
                '%Y-%m-%d %H:%M:%S.%f'
            ).strftime('%Y-%m-%d')
            print(f"✅ Analysis date: {metrics_date}")
        except KeyError:
            print("❌ ERROR: Could not find calculated_at timestamp in metrics!")
            raise
        except ValueError:
            print("❌ ERROR: Invalid timestamp format in metrics!")
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