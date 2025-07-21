#!/usr/bin/env python3
"""
Monitor Dashboard - Real-time Pipeline Monitoring
Provides live dashboard for monitoring the high-velocity pipeline performance
"""

import asyncio
import time
import json
import argparse
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.text import Text
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from performance_monitor import PerformanceMonitor
from config_manager import get_config

class LiveDashboard:
    """
    Real-time dashboard for monitoring pipeline performance
    
    Displays:
    - Current performance metrics
    - Agent status and swap history
    - System health indicators
    - Live throughput and latency graphs
    """
    
    def __init__(self, refresh_rate: float = 2.0):
        self.console = Console() if RICH_AVAILABLE else None
        self.refresh_rate = refresh_rate
        self.start_time = time.time()
        self.is_running = False
        
        # Data sources
        self.metrics_history: List[Dict[str, Any]] = []
        self.max_history = 100
        
        # Dashboard state
        self.current_metrics: Optional[Dict[str, Any]] = None
        self.agent_swaps = 0
        self.total_messages = 0
        
    def update_metrics(self, metrics: Dict[str, Any]):
        """Update dashboard with new metrics"""
        self.current_metrics = metrics
        self.metrics_history.append({
            'timestamp': time.time(),
            'metrics': metrics
        })
        
        # Maintain history size
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]
        
        # Update counters
        if 'health' in metrics and 'agent_swaps' in metrics['health']:
            self.agent_swaps = metrics['health']['agent_swaps']
        
        if 'throughput' in metrics and 'total_messages' in metrics['throughput']:
            self.total_messages = metrics['throughput']['total_messages']
    
    def create_header_panel(self) -> Panel:
        """Create header panel with system info"""
        uptime = time.time() - self.start_time
        uptime_str = f"{uptime/3600:.1f}h" if uptime > 3600 else f"{uptime/60:.1f}m"
        
        header_text = Text.assemble(
            Text("🚀 HIGH-VELOCITY AI PIPELINE MONITOR", style="bold cyan"),
            Text("\n"),
            Text(f"⏱️ Uptime: {uptime_str} | ", style="dim"),
            Text(f"📊 Messages: {self.total_messages:,} | ", style="dim"),
            Text(f"🔄 Swaps: {self.agent_swaps}", style="dim")
        )
        
        return Panel(
            Align.center(header_text),
            box=rich.box.ROUNDED,
            style="cyan"
        )
    
    def create_metrics_table(self) -> Table:
        """Create metrics table"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Current", width=15)
        table.add_column("Status", width=10)
        table.add_column("Trend", width=10)
        
        if not self.current_metrics:
            table.add_row("No data", "N/A", "N/A", "N/A")
            return table
        
        # Latency metrics
        latency = self.current_metrics.get('latency', {})
        p99_latency = latency.get('p99_ms', 0)
        p99_status = "🟢 Good" if p99_latency < 100 else "🟡 Warning" if p99_latency < 150 else "🔴 Critical"
        
        table.add_row(
            "P99 Latency",
            f"{p99_latency:.1f}ms",
            p99_status,
            self._get_trend_indicator('p99_latency', p99_latency)
        )
        
        # Throughput metrics
        throughput = self.current_metrics.get('throughput', {})
        current_throughput = throughput.get('current_msg_per_sec', 0)
        throughput_status = "🟢 Good" if current_throughput > 500 else "🟡 Low" if current_throughput > 100 else "🔴 Very Low"
        
        table.add_row(
            "Throughput",
            f"{current_throughput:.1f} msg/s",
            throughput_status,
            self._get_trend_indicator('throughput', current_throughput)
        )
        
        # Success rate
        health = self.current_metrics.get('health', {})
        success_rate = health.get('success_rate_percent', 0)
        success_status = "🟢 Excellent" if success_rate > 95 else "🟡 Degraded" if success_rate > 80 else "🔴 Poor"
        
        table.add_row(
            "Success Rate",
            f"{success_rate:.1f}%",
            success_status,
            self._get_trend_indicator('success_rate', success_rate)
        )
        
        # Memory usage
        memory_mb = health.get('memory_usage_mb', 0)
        memory_status = "🟢 Normal" if memory_mb < 1000 else "🟡 High" if memory_mb < 1500 else "🔴 Critical"
        
        table.add_row(
            "Memory Usage",
            f"{memory_mb:.0f}MB",
            memory_status,
            self._get_trend_indicator('memory', memory_mb)
        )
        
        return table
    
    def _get_trend_indicator(self, metric_name: str, current_value: float) -> str:
        """Get trend indicator for a metric"""
        if len(self.metrics_history) < 5:
            return "➡️"
        
        # Get value from 5 samples ago
        old_entry = self.metrics_history[-5]
        old_metrics = old_entry['metrics']
        
        # Extract old value based on metric name
        if metric_name == 'p99_latency':
            old_value = old_metrics.get('latency', {}).get('p99_ms', current_value)
        elif metric_name == 'throughput':
            old_value = old_metrics.get('throughput', {}).get('current_msg_per_sec', current_value)
        elif metric_name == 'success_rate':
            old_value = old_metrics.get('health', {}).get('success_rate_percent', current_value)
        elif metric_name == 'memory':
            old_value = old_metrics.get('health', {}).get('memory_usage_mb', current_value)
        else:
            return "➡️"
        
        # Calculate trend
        if abs(current_value - old_value) < 0.1:
            return "➡️"
        elif current_value > old_value:
            return "📈" if metric_name != 'p99_latency' else "📉"  # Higher latency is bad
        else:
            return "📉" if metric_name != 'p99_latency' else "📈"  # Lower latency is good
    
    def create_agent_status_panel(self) -> Panel:
        """Create agent status panel"""
        if not self.current_metrics:
            content = Text("No agent data available", style="dim")
        else:
            # Mock agent status - in real implementation would get from agent manager
            content = Text.assemble(
                Text("🤖 Current Agent: ", style="bold"),
                Text("Standard (GPT-4)", style="green"),
                Text("\n"),
                Text("🔄 Last Swap: ", style="bold"),
                Text("2 minutes ago", style="dim"),
                Text("\n"),
                Text("📊 Swap Reason: ", style="bold"),
                Text("Latency threshold exceeded", style="yellow"),
                Text("\n"),
                Text("⚡ Available: ", style="bold"),
                Text("Ultra-Fast (GROQ) ✓", style="green")
            )
        
        return Panel(
            content,
            title="🤖 Agent Status",
            box=rich.box.ROUNDED
        )
    
    def create_system_health_panel(self) -> Panel:
        """Create system health panel"""
        if not self.current_metrics:
            content = Text("No health data available", style="dim")
        else:
            health = self.current_metrics.get('health', {})
            
            # Health indicators
            indicators = []
            
            # Circuit breaker status
            circuit_trips = health.get('circuit_breaker_trips', 0)
            circuit_status = "🟢 Closed" if circuit_trips == 0 else f"🟡 {circuit_trips} trips"
            
            # CPU and memory
            cpu_usage = health.get('cpu_usage_percent', 0)
            memory_usage = health.get('memory_usage_mb', 0)
            
            content = Text.assemble(
                Text("🔌 Circuit Breaker: ", style="bold"),
                Text(circuit_status),
                Text("\n"),
                Text("💾 Memory: ", style="bold"),
                Text(f"{memory_usage:.0f}MB"),
                Text("\n"),
                Text("🖥️ CPU: ", style="bold"),
                Text(f"{cpu_usage:.1f}%"),
                Text("\n"),
                Text("🔄 Agent Swaps: ", style="bold"),
                Text(f"{self.agent_swaps}")
            )
        
        return Panel(
            content,
            title="🏥 System Health",
            box=rich.box.ROUNDED
        )
    
    def create_layout(self) -> Layout:
        """Create dashboard layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split_column(
            Layout(name="metrics"),
            Layout(name="agent_status")
        )
        
        layout["right"].split_column(
            Layout(name="health"),
            Layout(name="logs")
        )
        
        return layout
    
    def render_dashboard(self) -> Layout:
        """Render complete dashboard"""
        layout = self.create_layout()
        
        # Populate layout
        if RICH_AVAILABLE:
            import rich.box
            layout["header"].update(self.create_header_panel())
            layout["metrics"].update(Panel(self.create_metrics_table(), title="📊 Performance Metrics"))
            layout["agent_status"].update(self.create_agent_status_panel())
            layout["health"].update(self.create_system_health_panel())
            
            # Footer with controls
            footer_text = Text.assemble(
                Text("Press ", style="dim"),
                Text("Ctrl+C", style="bold red"),
                Text(" to exit | ", style="dim"),
                Text("Updates every ", style="dim"),
                Text(f"{self.refresh_rate}s", style="bold"),
                Text(" | ", style="dim"),
                Text(datetime.now().strftime("%H:%M:%S"), style="bold cyan")
            )
            layout["footer"].update(Panel(Align.center(footer_text), box=rich.box.ROUNDED))
        
        return layout
    
    async def run_live_dashboard(self):
        """Run live dashboard with auto-refresh"""
        if not RICH_AVAILABLE:
            print("Rich library not available. Install with: pip install rich")
            return
        
        self.is_running = True
        
        try:
            with Live(self.render_dashboard(), refresh_per_second=1/self.refresh_rate, screen=True) as live:
                while self.is_running:
                    # Update dashboard
                    live.update(self.render_dashboard())
                    await asyncio.sleep(self.refresh_rate)
                    
        except KeyboardInterrupt:
            print("\n👋 Dashboard stopped")
        finally:
            self.is_running = False

def load_metrics_from_file(filepath: str) -> Optional[Dict[str, Any]]:
    """Load metrics from JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading metrics from {filepath}: {e}")
        return None

async def monitor_file_based(dashboard: LiveDashboard, metrics_file: str):
    """Monitor pipeline by reading metrics from file"""
    print(f"Monitoring metrics from file: {metrics_file}")
    
    last_modified = 0
    
    while dashboard.is_running:
        try:
            # Check if file was modified
            if os.path.exists(metrics_file):
                current_modified = os.path.getmtime(metrics_file)
                
                if current_modified > last_modified:
                    metrics = load_metrics_from_file(metrics_file)
                    if metrics:
                        dashboard.update_metrics(metrics)
                    last_modified = current_modified
            
            await asyncio.sleep(1.0)
            
        except Exception as e:
            print(f"Error monitoring file: {e}")
            await asyncio.sleep(5.0)

def print_basic_dashboard(metrics: Dict[str, Any]):
    """Print basic dashboard without Rich"""
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print("=" * 60)
    print("🚀 HIGH-VELOCITY AI PIPELINE MONITOR")
    print("=" * 60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not metrics:
        print("❌ No metrics available")
        return
    
    # Performance metrics
    print("📊 PERFORMANCE METRICS:")
    print("-" * 30)
    
    latency = metrics.get('latency', {})
    p99_latency = latency.get('p99_ms', 0)
    print(f"P99 Latency:    {p99_latency:.1f}ms")
    
    throughput = metrics.get('throughput', {})
    current_throughput = throughput.get('current_msg_per_sec', 0)
    total_messages = throughput.get('total_messages', 0)
    print(f"Throughput:     {current_throughput:.1f} msg/sec")
    print(f"Total Messages: {total_messages:,}")
    
    health = metrics.get('health', {})
    success_rate = health.get('success_rate_percent', 0)
    print(f"Success Rate:   {success_rate:.1f}%")
    
    print()
    print("🏥 SYSTEM HEALTH:")
    print("-" * 30)
    
    memory_mb = health.get('memory_usage_mb', 0)
    cpu_usage = health.get('cpu_usage_percent', 0)
    agent_swaps = health.get('agent_swaps', 0)
    
    print(f"Memory Usage:   {memory_mb:.0f}MB")
    print(f"CPU Usage:      {cpu_usage:.1f}%")
    print(f"Agent Swaps:    {agent_swaps}")
    
    # Status indicators
    print()
    print("🚦 STATUS INDICATORS:")
    print("-" * 30)
    
    latency_status = "🟢 Good" if p99_latency < 100 else "🟡 Warning" if p99_latency < 150 else "🔴 Critical"
    throughput_status = "🟢 Good" if current_throughput > 500 else "🟡 Low" if current_throughput > 100 else "🔴 Very Low"
    health_status = "🟢 Healthy" if success_rate > 95 else "🟡 Degraded" if success_rate > 80 else "🔴 Unhealthy"
    
    print(f"Latency:        {latency_status}")
    print(f"Throughput:     {throughput_status}")
    print(f"Overall:        {health_status}")
    
    print()
    print("Press Ctrl+C to exit")

async def run_basic_monitor(metrics_file: str, refresh_rate: float = 2.0):
    """Run basic monitor without Rich"""
    print("Starting basic monitor (install Rich for enhanced dashboard)")
    
    last_modified = 0
    
    try:
        while True:
            metrics = None
            
            # Load metrics if file exists and was modified
            if os.path.exists(metrics_file):
                current_modified = os.path.getmtime(metrics_file)
                
                if current_modified > last_modified:
                    metrics = load_metrics_from_file(metrics_file)
                    last_modified = current_modified
            
            # Display dashboard
            print_basic_dashboard(metrics)
            
            await asyncio.sleep(refresh_rate)
            
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped")

def find_latest_metrics_file() -> Optional[str]:
    """Find the latest metrics file in exports directory"""
    exports_dir = Path("exports")
    
    if not exports_dir.exists():
        return None
    
    # Look for recent pipeline report files
    pattern_files = list(exports_dir.glob("pipeline_report_*.json"))
    
    if pattern_files:
        # Return the most recent file
        latest_file = max(pattern_files, key=lambda p: p.stat().st_mtime)
        return str(latest_file)
    
    return None

async def monitor_pipeline_process():
    """Monitor a running pipeline process"""
    # This would connect to a running pipeline instance
    # For now, we'll simulate with demo data
    
    dashboard = LiveDashboard()
    
    # Simulate metrics updates
    import random
    
    print("🔄 Monitoring live pipeline (simulated data)")
    
    try:
        if RICH_AVAILABLE:
            # Start dashboard in background
            dashboard_task = asyncio.create_task(dashboard.run_live_dashboard())
            
            # Simulate metrics updates
            while dashboard.is_running:
                # Generate sample metrics
                mock_metrics = {
                    'latency': {
                        'p99_ms': random.uniform(60, 120),
                        'p95_ms': random.uniform(40, 80),
                        'average_ms': random.uniform(30, 60)
                    },
                    'throughput': {
                        'current_msg_per_sec': random.uniform(400, 800),
                        'total_messages': random.randint(10000, 50000)
                    },
                    'health': {
                        'success_rate_percent': random.uniform(92, 99),
                        'memory_usage_mb': random.uniform(800, 1200),
                        'cpu_usage_percent': random.uniform(20, 60),
                        'agent_swaps': random.randint(3, 15),
                        'circuit_breaker_trips': 0
                    }
                }
                
                dashboard.update_metrics(mock_metrics)
                await asyncio.sleep(2.0)
            
            await dashboard_task
            
        else:
            # Basic monitoring
            await run_basic_monitor("simulated")
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")

def main():
    """Main entry point for monitor dashboard"""
    parser = argparse.ArgumentParser(
        description="High-Velocity Pipeline Monitor Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/monitor_dashboard.py                          # Monitor live pipeline
  python scripts/monitor_dashboard.py --file metrics.json     # Monitor from file
  python scripts/monitor_dashboard.py --auto-find             # Auto-find latest metrics
  python scripts/monitor_dashboard.py --basic                 # Basic mode (no Rich)
        """
    )
    
    parser.add_argument('--file', type=str, help='Monitor metrics from JSON file')
    parser.add_argument('--auto-find', action='store_true', help='Auto-find latest metrics file')
    parser.add_argument('--refresh-rate', type=float, default=2.0, help='Dashboard refresh rate (seconds)')
    parser.add_argument('--basic', action='store_true', help='Use basic mode without Rich')
    parser.add_argument('--web-mode', action='store_true', help='Run as web service')
    
    args = parser.parse_args()
    
    try:
        if args.web_mode:
            print("🌐 Web mode not implemented yet")
            return
        
        if args.auto_find:
            metrics_file = find_latest_metrics_file()
            if not metrics_file:
                print("❌ No metrics files found in exports/ directory")
                return
            print(f"📁 Found metrics file: {metrics_file}")
        elif args.file:
            metrics_file = args.file
            if not os.path.exists(metrics_file):
                print(f"❌ Metrics file not found: {metrics_file}")
                return
        else:
            # Monitor live pipeline
            asyncio.run(monitor_pipeline_process())
            return
        
        # File-based monitoring
        if args.basic or not RICH_AVAILABLE:
            asyncio.run(run_basic_monitor(metrics_file, args.refresh_rate))
        else:
            dashboard = LiveDashboard(args.refresh_rate)
            
            async def run_dashboard():
                # Start dashboard and file monitor concurrently
                dashboard_task = asyncio.create_task(dashboard.run_live_dashboard())
                monitor_task = asyncio.create_task(monitor_file_based(dashboard, metrics_file))
                
                try:
                    await asyncio.gather(dashboard_task, monitor_task)
                except KeyboardInterrupt:
                    dashboard.is_running = False
                    dashboard_task.cancel()
                    monitor_task.cancel()
            
            asyncio.run(run_dashboard())
    
    except KeyboardInterrupt:
        print("\n👋 Dashboard interrupted")
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()