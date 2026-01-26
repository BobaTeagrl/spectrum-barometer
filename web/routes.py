from flask import Blueprint, render_template, send_from_directory, redirect, url_for, flash, request
from barometer.data import load_data
from barometer.graphs import generate_graph
from barometer.paths import get_graphs_dir
from barometer.actions import archive_old_data, get_statistics, get_latest_reading, scrape_single_reading
from time import time

bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    theme = request.args.get("theme", "dark")
    latest = get_latest_reading()
    graphs_dir = get_graphs_dir()
    graphs = list(graphs_dir.glob('*.png'))

    return render_template(
        "dashboard.html",
        latest=latest,
        has_graphs=len(graphs) > 0,
        theme=theme,
        graph_ts=int(time())  
    )

@bp.route("/graph/<name>")
def graph_file(name):
    
    return send_from_directory(get_graphs_dir(), name)


@bp.route("/generate", methods=["POST"])
def generate():
    theme = request.form.get("theme", "dark")
    
    try:
        result = generate_graph(days=7, output=None, graph_type='dashboard', include_archives=False)
        if result:
            flash("Graph generated successfully!", "success")
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
    
    result = archive_old_data(keep_days=90)
    
    if result['success']:
        flash(result['message'], "success")
    else:
        flash(result['message'], "error")
    
    return redirect(url_for("main.dashboard"))


@bp.route("/stats")
def stats():
   
    stats_data = get_statistics(include_archives=False)
    
    return render_template("stats.html", stats=stats_data)
