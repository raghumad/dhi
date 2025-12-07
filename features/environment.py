import json
import os
import time
import datetime
import html

# --- HTML TEMPLATE ---
# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Dhi Test Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 20px; background: #f4f6f8; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .summary {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; flex: 1; text-align: center; }}
        .card h3 {{ margin: 0 0 5px 0; font-size: 24px; color: #333; }}
        .card span {{ color: #666; font-size: 14px; }}
        
        .scenario {{ border: 1px solid #ddd; border-radius: 6px; margin-bottom: 15px; overflow: hidden; }}
        .scenario-header {{ padding: 12px 15px; background: #fff; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
        .scenario-header:hover {{ background: #f8f9fa; }}
        .scenario-header.passed {{ border-left: 5px solid #2ecc71; }}
        .scenario-header.failed {{ border-left: 5px solid #e74c3c; }}
        
        .steps {{ display: none; padding: 15px; background: #fafafa; border-top: 1px solid #ddd; }}
        .step {{ margin-bottom: 8px; padding: 8px; background: white; border-radius: 4px; border: 1px solid #eee; }}
        .step.passed {{ color: #27ae60; }}
        .step.failed {{ color: #c0392b; }}
        
        .metrics {{ margin-top: 10px; padding: 10px; background: #e8f6f3; border-radius: 4px; font-size: 14px; border: 1px solid #d4efdf; }}
        .logs {{ margin-top: 10px; padding: 10px; background: #2c3e50; color: #fff; border-radius: 4px; font-family: monospace; font-size: 12px; white-space: pre-wrap; }}
        
        /* Utility */
        .badge {{ padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; color: white; }}
        .bg-green {{ background: #2ecc71; }}
        .bg-red {{ background: #e74c3c; }}
    </style>
    <script>
        function toggle(id) {{
            var el = document.getElementById(id);
            el.style.display = el.style.display === 'block' ? 'none' : 'block';
        }}
    </script>
</head>
<body>
    <div class="container">
        <h1>Dhi (धी) Test Report</h1>
        <div class="summary">
            <div class="card"><h3>{total}</h3><span>Total Scenarios</span></div>
            <div class="card" style="color: #2ecc71"><h3>{passed}</h3><span>Passed</span></div>
            <div class="card" style="color: #e74c3c"><h3>{failed}</h3><span>Failed</span></div>
            <div class="card"><h3>{duration:.2f}s</h3><span>Total Duration</span></div>
        </div>
        
        {content}
        
        <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
            Generated {timestamp}
        </div>
    </div>
</body>
</html>
"""

def before_all(context):
    # Ensure out directory exists
    os.makedirs("out", exist_ok=True)
    
    context.report_data = []
    context.start_time = time.time()
    context.report_file = "out/test_report.html"
    context.perf_report_file = "out/test_performance_report.json"

def before_scenario(context, scenario):
    context.scenario_data = {
        "name": scenario.name,
        "steps": [],
        "start_time": time.time(),
        "status": "passed",
        "logs": [],
        "metrics": {}
    }
    # Initialize metric collection for steps
    context.scenario_perf = {}

def after_step(context, step):
    context.scenario_data["steps"].append({
        "name": step.name,
        "status": step.status,
        "keyword": step.keyword,
        "duration": step.duration
    })
    if step.status == "failed":
        context.scenario_data["status"] = "failed"

def after_scenario(context, scenario):
    end_time = time.time()
    context.scenario_data["duration"] = end_time - context.scenario_data["start_time"]
    context.scenario_data["status"] = str(scenario.status)
    
    # Capture metrics collected in steps
    if hasattr(context, 'scenario_perf'):
        context.scenario_data["metrics"] = context.scenario_perf
        
    context.report_data.append(context.scenario_data)

def after_all(context):
    total_duration = time.time() - context.start_time
    passed = sum(1 for s in context.report_data if s['status'] == 'Status.passed')
    failed = sum(1 for s in context.report_data if s['status'] == 'Status.failed')
    total = len(context.report_data)
    
    html_content = ""
    for idx, scen in enumerate(context.report_data):
        scen_id = f"scen_{idx}"
        status_class = "passed" if scen['status'] == 'Status.passed' else "failed"
        
        # Steps HTML
        steps_html = ""
        for step in scen['steps']:
            icon = "✓" if step['status'] == 'passed' else "✗"
            cls = "passed" if step['status'] == 'passed' else "failed"
            steps_html += f'<div class="step {cls}"><b>{step["keyword"]}</b> {html.escape(step["name"])} <span style="float:right; color:#999">{step["duration"]:.3f}s</span></div>'
            
        # Metrics HTML
        metrics_html = ""
        if scen['metrics']:
            metrics_html = '<div class="metrics"><b>Telemetry:</b><br>'
            for k, v in scen['metrics'].items():
                metrics_html += f'{k}: <b>{v:.4f}</b><br>'
            metrics_html += '</div>'
            
        html_content += f"""
        <div class="scenario">
            <div class="scenario-header {status_class}" onclick="toggle('{scen_id}')">
                <div>
                    <b>{html.escape(scen['name'])}</b>
                </div>
                <div>
                    <span class="badge {'bg-green' if status_class=='passed' else 'bg-red'}">{scen['status']}</span>
                    <span style="color:#999; margin-left:10px">{scen['duration']:.2f}s</span>
                </div>
            </div>
            <div id="{scen_id}" class="steps">
                {steps_html}
                {metrics_html}
            </div>
        </div>
        """
        
    final_html = HTML_TEMPLATE.format(
        total=total,
        passed=passed,
        failed=failed,
        duration=total_duration,
        content=html_content,
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    with open(context.report_file, "w") as f:
        f.write(final_html)
        
    print(f"\n[Report] HTML Report generated: {context.report_file}")
