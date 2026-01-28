from flask import Blueprint, render_template, send_from_directory, redirect, url_for, flash, request
from barometer.data import load_data
from barometer.graphs import generate_graph
from barometer.paths import get_graphs_dir
from barometer.actions import archive_old_data, get_statistics, get_latest_reading, scrape_single_reading
from time import time
from barometer.background import start_monitoring, stop_monitoring, get_monitor_info

bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    theme = request.args.get("theme", "dark")
    latest = get_latest_reading()
    graphs_dir = get_graphs_dir()
    graphs = list(graphs_dir.glob('*.png'))
    monitor_info = get_monitor_info() 

    return render_template(
        "dashboard.html",
        latest=latest,
        has_graphs=len(graphs) > 0,
        theme=theme,
        graph_ts=int(time()),
        monitor=monitor_info,
        graph_types=['line', 'smooth', 'area', 'daily', 'distribution', 'change', 'dashboard'],
    )

@bp.route("/graph/<name>")
def graph_file(name):
    
    return send_from_directory(get_graphs_dir(), name)


@bp.route("/generate", methods=["POST"])
def generate():
    theme = request.form.get("theme", "dark")
    days = request.form.get("days", 7, type=int)
    graph_type = request.form.get("graph_type", "dashboard")
    
    try:
        if graph_type == 'all':
            # gwnerate all graph types
            result = generate_graph(
                days=days, 
                output=get_graphs_dir() / 'pressure.png',
                graph_type='all', 
                include_archives=False, 
                theme=theme
            )
            flash("All graphs generated successfully!", "success")
        else:
            # map graph types to filenames
            filename_map = {
                'line': 'pressure_line.png',
                'smooth': 'pressure_smooth.png',
                'area': 'pressure_area.png',
                'daily': 'pressure_daily.png',
                'distribution': 'pressure_distribution.png',
                'change': 'pressure_change.png',
                'dashboard': 'pressure.png'
            }
            
            output_file = get_graphs_dir() / filename_map.get(graph_type, 'pressure.png')
            
            result = generate_graph(
                days=days, 
                output=output_file, 
                graph_type=graph_type, 
                include_archives=False, 
                theme=theme
            )
            
            if result or graph_type == 'dashboard':  # dashboard doesn't return a path
                flash(f"{graph_type.title()} graph generated successfully!", "success")
            else:
                flash("Failed to generate graph", "error")
    except Exception as e:
        flash(f"Error generating graph: {e}", "error")

    return redirect(url_for("main.dashboard"))


@bp.route("/scrape", methods=["POST"])
def scrape():
    
    result = scrape_single_reading()
    
    if result['success']:
        flash(result['message'], "success")
    else:
        flash(result['message'], "error")
    
    return redirect(url_for("main.dashboard"))


@bp.route("/archive", methods=["POST"])
def archive():
    keep_days = request.form.get("keep_days", 90, type=int)
    
    result = archive_old_data(keep_days=keep_days)
    
    if result['success']:
        flash(result['message'], "success")
    else:
        flash(result['message'], "error")
    
    return redirect(url_for("main.dashboard"))


@bp.route("/stats")
def stats():
   
    stats_data = get_statistics(include_archives=False)
    
    return render_template("stats.html", stats=stats_data)


@bp.route("/monitor/start", methods=["POST"])
def monitor_start():
    interval = request.form.get('interval', 300, type=int)
    
    result = start_monitoring(interval)
    
    if result['success']:
        flash(result['message'], "success")
    else:
        flash(result['message'], "error")
    
    return redirect(url_for("main.dashboard"))


@bp.route("/monitor/stop", methods=["POST"])
def monitor_stop():
    result = stop_monitoring()
    
    if result['success']:
        flash(result['message'], "success")
    else:
        flash(result['message'], "error")
    
    return redirect(url_for("main.dashboard"))