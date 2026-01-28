from barometer.paths import get_graphs_dir 
from barometer.data import load_data
import matplotlib
matplotlib.use('Agg')  # headless backend for background operation
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
import click
import logging
from qbstyles import mpl_style
from pathlib import Path


mpl_style(dark=True)
def generate_line_graph(df, output, days):
    """Standard line graph"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.plot(df['timestamp'], df['pressure_hpa'], 
            linewidth=2, color='#2E86AB', label='Barometric Pressure')
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Pressure (hPa)', fontsize=12)
    ax.set_title(f'Barometric Pressure - Last {days} Days', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_smooth_graph(df, output, days, window=12):
    """Line graph with rolling average"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Original data
    ax.plot(df['timestamp'], df['pressure_hpa'], 
            linewidth=1, color='#2E86AB', alpha=0.4, label='Raw Data')
    
    # Rolling average
    df['rolling_avg'] = df['pressure_hpa'].rolling(window=window, center=True).mean()
    ax.plot(df['timestamp'], df['rolling_avg'], 
            linewidth=2.5, color='#A23B72', label=f'{window}-point Moving Average')
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Pressure (hPa)', fontsize=12)
    ax.set_title(f'Barometric Pressure with Trend - Last {days} Days', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_area_graph(df, output, days):
    """Filled area chart"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.fill_between(df['timestamp'], df['pressure_hpa'], 
                     alpha=0.4, color='#2E86AB', label='Pressure')
    ax.plot(df['timestamp'], df['pressure_hpa'], 
            linewidth=2, color='#1A5F7A', label='Trend Line')
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Pressure (hPa)', fontsize=12)
    ax.set_title(f'Barometric Pressure Area - Last {days} Days', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_daily_summary(df, output, days):
    """Daily min/max/avg bars"""
    # Group by date
    df['date'] = df['timestamp'].dt.date
    daily = df.groupby('date').agg({
        'pressure_hpa': ['min', 'max', 'mean']
    }).reset_index()
    daily.columns = ['date', 'min', 'max', 'mean']
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = range(len(daily))
    
    # Draw bars for range
    for i, row in daily.iterrows():
        ax.plot([i, i], [row['min'], row['max']], 
                color='#2E86AB', linewidth=8, alpha=0.3)
        ax.scatter(i, row['mean'], color='#A23B72', s=50, zorder=3)
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Pressure (hPa)', fontsize=12)
    ax.set_title(f'Daily Pressure Summary - Last {days} Days', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([d.strftime('%m/%d') for d in daily['date']], rotation=45)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#2E86AB', linewidth=8, alpha=0.3, label='Min-Max Range'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#A23B72', 
               markersize=8, label='Daily Average')
    ]
    ax.legend(handles=legend_elements)
    
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_distribution(df, output, days):
    """Histogram of pressure values"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.hist(df['pressure_hpa'], bins=30, color='#2E86AB', alpha=0.7, edgecolor='black')
    
    # Add mean and median lines
    mean_val = df['pressure_hpa'].mean()
    median_val = df['pressure_hpa'].median()
    
    ax.axvline(mean_val, color='#A23B72', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f} hPa')
    ax.axvline(median_val, color='#F18F01', linestyle='--', linewidth=2, label=f'Median: {median_val:.2f} hPa')
    
    ax.set_xlabel('Pressure (hPa)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(f'Pressure Distribution - Last {days} Days', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_rate_of_change(df, output, days):
    """Pressure change over time"""
    # Calculate hourly change
    df = df.sort_values('timestamp')
    df['change'] = df['pressure_hpa'].diff()
    df['hours_diff'] = df['timestamp'].diff().dt.total_seconds() / 3600
    df['hourly_change'] = df['change'] / df['hours_diff']
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = ['#EF476F' if x < 0 else '#06D6A0' for x in df['hourly_change']]
    ax.bar(df['timestamp'], df['hourly_change'], color=colors, alpha=0.6, width=0.01)
    
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Pressure Change (hPa/hour)', fontsize=12)
    ax.set_title(f'Rate of Pressure Change - Last {days} Days', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45)
    
    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#06D6A0', alpha=0.6, label='Rising'),
        Patch(facecolor='#EF476F', alpha=0.6, label='Falling')
    ]
    ax.legend(handles=legend_elements)
    
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_dashboard(df, output, days):
    """Multi-panel dashboard view"""
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # 1. Main time series (top, full width)
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(df['timestamp'], df['pressure_hpa'], linewidth=2, color='#2E86AB')
    ax1.set_title('Pressure Over Time', fontweight='bold')
    ax1.set_ylabel('Pressure (hPa)')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    # 2. Distribution
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.hist(df['pressure_hpa'], bins=20, color='#2E86AB', alpha=0.7, edgecolor='black')
    ax2.set_title('Distribution', fontweight='bold')
    ax2.set_xlabel('Pressure (hPa)')
    ax2.set_ylabel('Frequency')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 3. Rate of change
    ax3 = fig.add_subplot(gs[1, 1])
    df_sorted = df.sort_values('timestamp')
    df_sorted['change'] = df_sorted['pressure_hpa'].diff()
    colors = ['#EF476F' if x < 0 else '#06D6A0' for x in df_sorted['change']]
    ax3.bar(range(len(df_sorted)), df_sorted['change'], color=colors, alpha=0.6)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_title('Reading-to-Reading Change', fontweight='bold')
    ax3.set_ylabel('Change (hPa)')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. Statistics box
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.axis('off')
    stats_text = f"""
    STATISTICS
    ──────────────────
    Current:    {df['pressure_hpa'].iloc[-1]:.2f} hPa
    Average:    {df['pressure_hpa'].mean():.2f} hPa
    Minimum:    {df['pressure_hpa'].min():.2f} hPa
    Maximum:    {df['pressure_hpa'].max():.2f} hPa
    Range:      {df['pressure_hpa'].max() - df['pressure_hpa'].min():.2f} hPa
    Std Dev:    {df['pressure_hpa'].std():.2f} hPa
    """
    ax4.text(0.1, 0.5, stats_text, fontsize=11, verticalalignment='center', 
             fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    # 5. Trend indicator
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.axis('off')
    
    # Calculate 24h trend
    if len(df) > 1:
        recent_avg = df.tail(min(12, len(df)))['pressure_hpa'].mean()
        older_avg = df.head(min(12, len(df)))['pressure_hpa'].mean()
        trend = recent_avg - older_avg
        
        trend_text = "RISING ↗" if trend > 0.5 else "FALLING ↘" if trend < -0.5 else "STABLE →"
        trend_color = '#06D6A0' if trend > 0.5 else '#EF476F' if trend < -0.5 else '#FFD166'
        
        ax5.text(0.5, 0.6, 'TREND', fontsize=14, ha='center', fontweight='bold')
        ax5.text(0.5, 0.4, trend_text, fontsize=24, ha='center', 
                color=trend_color, fontweight='bold')
        ax5.text(0.5, 0.2, f'{trend:+.2f} hPa', fontsize=12, ha='center')
    
    fig.suptitle(f'Barometer Dashboard - Last {days} Days', fontsize=16, fontweight='bold')
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def apply_theme(theme: str):
    if theme == "dark":
        mpl_style(dark=True)
    else:
        mpl_style(dark=False)


def generate_graph(days=7, output=None, graph_type='line',
                   include_archives=False, theme="dark"):
    days = int(days)
    if output is None:
        output = get_graphs_dir() / 'pressure.png'
    else:
        output = Path(output)
        
    apply_theme(theme)


    df = load_data(include_archives=include_archives)
    
    if df is None or df.empty:
        click.echo("No data available to graph")
        return None
    
    cutoff = datetime.now() - timedelta(days=days)
    df_filtered = df[df['timestamp'] > cutoff].copy()
    
    if df_filtered.empty:
        click.echo(f"No data available for the last {days} days")
        return None
    
    output.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if graph_type == 'line':
            generate_line_graph(df_filtered, str(output), days)
        elif graph_type == 'smooth':
            generate_smooth_graph(df_filtered, str(output), days)
        elif graph_type == 'area':
            generate_area_graph(df_filtered, str(output), days)
        elif graph_type == 'daily':
            generate_daily_summary(df_filtered, str(output), days)
        elif graph_type == 'distribution':
            generate_distribution(df_filtered, str(output), days)
        elif graph_type == 'change':
            generate_rate_of_change(df_filtered, str(output), days)
        elif graph_type == 'dashboard':
            generate_dashboard(df_filtered, str(output), days)
        elif graph_type == 'all':
            base_name = output.stem
            ext = output.suffix or '.png'
            
            generate_line_graph(df_filtered, str(output.parent / f'{base_name}_line{ext}'), days)
            generate_smooth_graph(df_filtered, str(output.parent / f'{base_name}_smooth{ext}'), days)
            generate_area_graph(df_filtered, str(output.parent / f'{base_name}_area{ext}'), days)
            generate_daily_summary(df_filtered, str(output.parent / f'{base_name}_daily{ext}'), days)
            generate_distribution(df_filtered, str(output.parent / f'{base_name}_distribution{ext}'), days)
            generate_rate_of_change(df_filtered, str(output.parent / f'{base_name}_change{ext}'), days)
            generate_dashboard(df_filtered, str(output.parent / f'{base_name}_dashboard{ext}'), days)
            
            click.echo(f"Generated 7 graphs in {output.parent}")
            return None
        else:
            click.echo(f"Unknown graph type: {graph_type}")
            return None
        
        click.echo(f"Graph saved to {output}")
        return output
        
    except Exception as e:
        click.echo(f"Error generating graph: {e}")
        logging.error(f"Graph generation failed: {e}")
        return None
