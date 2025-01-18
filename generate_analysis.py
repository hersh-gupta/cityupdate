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
    
    # Read the metrics
    with open("cityscore_metrics.json", "r") as f:
        metrics = json.load(f)
    
    # Get analysis from Claude
    anthropic = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    with open("system_prompt.txt", "r") as f:
        system_prompt = f.read()
    
    message = anthropic.messages.create(
        model=claude_model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(metrics)}]
    )
    
    analysis = message.content[0].text
    # Using the date from 'calculated at', but there might be a better way to get this
    metrics_date = datetime.strptime(metrics['311 CALL CENTER PERFORMANCE']['calculated_at'], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')
    
    # Generate HTML
    html = generate_html(analysis, metrics_date, claude_model)
    
    # Save today's analysis
    os.makedirs("docs", exist_ok=True)
    with open(f"docs/{metrics_date}.html", "w") as f:
        f.write(html)
    
    # Update index to point to latest
    with open("docs/index.html", "w") as f:
        f.write(html)

if __name__ == "__main__":
    main()