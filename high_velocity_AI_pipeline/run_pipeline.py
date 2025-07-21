#!/usr/bin/env python3
"""
High-Velocity AI Pipeline - Main Runner
Production entry point for the high-velocity trading pipeline

This script provides:
- Command-line interface for pipeline execution
- Configuration management and validation
- Development and production modes
- Comprehensive logging setup
- Graceful shutdown handling
- Performance monitoring and export
"""

import asyncio
import argparse
import sys
import os
import signal
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.pipeline_core import HighVelocityPipeline
    from src.config_manager import PipelineConfig, ConfigurationManager, load_config_from_file
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("💡 Make sure you're running from the project root directory")
    print("💡 Try running: python setup.py first to install dependencies")
    sys.exit(1)


class PipelineRunner:
    """
    Main pipeline runner with comprehensive lifecycle management
    """
    
    def __init__(self):
        self.pipeline: Optional[HighVelocityPipeline] = None
        self.config: Optional[PipelineConfig] = None
        self.start_time: Optional[datetime] = None
        self.shutdown_requested = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        signal_name = signal.Signals(signum).name
        print(f"\n🛑 Received {signal_name}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    def setup_logging(self, config: PipelineConfig):
        """Setup comprehensive logging configuration"""
        
        # Create logs directory if needed
        if config.log_file:
            log_path = Path(config.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, config.log_level.upper(), logging.INFO),
            format=config.log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                *([] if not config.log_file else [logging.FileHandler(config.log_file)])
            ]
        )
        
        # Set specific logger levels
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('openai').setLevel(logging.WARNING)
        
        logger = logging.getLogger(__name__)
        logger.info("Logging configured successfully")
        
        if config.log_file:
            logger.info(f"Log file: {config.log_file}")
    
    def load_configuration(self, config_file: Optional[str] = None, 
                          dev_mode: bool = False) -> PipelineConfig:
        """Load and validate pipeline configuration"""
        
        try:
            if config_file:
                # Load from specific file
                config_path = Path(config_file)
                if not config_path.exists():
                    raise FileNotFoundError(f"Configuration file not found: {config_file}")
                
                config = load_config_from_file(config_path)
                print(f"✅ Configuration loaded from: {config_file}")
                
            else:
                # Load from environment variables
                config = PipelineConfig.load_from_env()
                print("✅ Configuration loaded from environment variables")
            
            # Development mode overrides
            if dev_mode:
                self._apply_dev_mode_overrides(config)
                print("🔧 Development mode overrides applied")
            
            # Validate configuration
            if not config.validate():
                raise ValueError("Configuration validation failed")
            
            print("✅ Configuration validated successfully")
            
            # Log key configuration values
            print(f"🎯 Target throughput: {config.target_throughput} msg/sec")
            print(f"⚡ Latency threshold: {config.latency_threshold_ms}ms")
            print(f"🤖 Default agent: {config.default_agent}")
            print(f"📊 Export directory: {config.export_directory}")
            
            return config
            
        except Exception as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)
    
    def _apply_dev_mode_overrides(self, config: PipelineConfig):
        """Apply development mode configuration overrides"""
        config.log_level = "DEBUG"
        config.target_throughput = min(config.target_throughput, 100.0)  # Limit throughput in dev
        config.message_batch_size = min(config.message_batch_size, 20)   # Smaller batches
        config.metrics_update_interval_seconds = 0.5  # More frequent updates
        config.market_symbols_count = min(config.market_symbols_count, 6)  # Fewer symbols
    
    async def run_pipeline(self, config: PipelineConfig, duration_seconds: Optional[float] = None):
        """Run the pipeline with specified configuration"""
        
        print(f"\n🚀 Starting High-Velocity AI Pipeline...")
        print(f"📅 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Initialize pipeline
            self.pipeline = HighVelocityPipeline(config)
            self.start_time = datetime.now()
            
            # Create pipeline task
            pipeline_task = asyncio.create_task(self.pipeline.start())
            
            # Run for specified duration or until shutdown
            if duration_seconds:
                print(f"⏱️ Pipeline will run for {duration_seconds} seconds")
                
                try:
                    await asyncio.wait_for(pipeline_task, timeout=duration_seconds)
                except asyncio.TimeoutError:
                    print(f"\n⏰ Duration limit reached ({duration_seconds}s)")
                    await self.pipeline.stop()
                    
            else:
                print("🔄 Pipeline running indefinitely (Ctrl+C to stop)")
                
                # Wait for shutdown signal
                while not self.shutdown_requested:
                    await asyncio.sleep(1)
                
                print("\n🛑 Shutdown requested, stopping pipeline...")
                await self.pipeline.stop()
            
            # Wait for pipeline to finish
            try:
                await asyncio.wait_for(pipeline_task, timeout=30)
            except asyncio.TimeoutError:
                print("⚠️ Pipeline shutdown timeout, forcing termination")
                pipeline_task.cancel()
        
        except Exception as e:
            print(f"❌ Pipeline error: {e}")
            if self.pipeline:
                await self.pipeline.stop()
            raise
        
        finally:
            await self._cleanup_and_export()
    
    async def _cleanup_and_export(self):
        """Cleanup and export pipeline results"""
        if not self.pipeline:
            return
        
        try:
            print("\n📊 Generating performance summary...")
            
            # Get final performance summary
            summary = self.pipeline.get_performance_summary()
            
            # Display summary
            self._display_performance_summary(summary)
            
            # Export results
            print("\n💾 Exporting results...")
            export_results = await self.pipeline.export_results()
            
            if export_results.get('csv_file'):
                print(f"✅ CSV exported: {export_results['csv_file']}")
            
            if export_results.get('json_file'):
                print(f"✅ JSON report exported: {export_results['json_file']}")
            
            print("\n✅ Pipeline shutdown completed successfully")
            
        except Exception as e:
            print(f"⚠️ Export error: {e}")
    
    def _display_performance_summary(self, summary: Dict[str, Any]):
        """Display formatted performance summary"""
        
        print("\n" + "="*60)
        print("📈 PERFORMANCE SUMMARY")
        print("="*60)
        
        pipeline_summary = summary.get('pipeline_summary', {})
        
        # Basic statistics
        duration = pipeline_summary.get('duration_seconds', 0)
        total_messages = pipeline_summary.get('total_messages_processed', 0)
        messages_per_sec = pipeline_summary.get('messages_per_second', 0)
        success_rate = pipeline_summary.get('success_rate_percent', 0)
        
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📨 Total messages: {total_messages:,}")
        print(f"🚀 Throughput: {messages_per_sec:.1f} msg/sec")
        print(f"✅ Success rate: {success_rate:.1f}%")
        
        # Performance metrics
        perf_metrics = summary.get('performance_metrics', {})
        if perf_metrics:
            latency = perf_metrics.get('latency', {})
            print(f"\n📊 Latency Metrics:")
            print(f"   P50: {latency.get('p50_ms', 0):.1f}ms")
            print(f"   P95: {latency.get('p95_ms', 0):.1f}ms")
            print(f"   P99: {latency.get('p99_ms', 0):.1f}ms")
        
        # Agent swap statistics
        swap_stats = summary.get('agent_swap_stats', {})
        if swap_stats:
            print(f"\n🔄 Agent Swaps:")
            print(f"   Total swaps: {swap_stats.get('total_swaps', 0)}")
            print(f"   Current agent: {swap_stats.get('current_agent', 'unknown')}")
        
        # Circuit breaker status
        cb_status = summary.get('circuit_breaker_status', {})
        if cb_status:
            print(f"\n🔌 Circuit Breaker:")
            print(f"   State: {cb_status.get('state', 'unknown')}")
            print(f"   Trip count: {cb_status.get('trip_count', 0)}")
        
        print("="*60)
    
    def run_health_check(self, config: PipelineConfig) -> bool:
        """Run system health check"""
        print("🏥 Running health check...")
        
        try:
            # Basic configuration validation
            if not config.validate():
                print("❌ Configuration validation failed")
                return False
            
            # Check API keys
            if not config.openai_api_key:
                print("❌ OpenAI API key missing")
                return False
            
            if not config.groq_api_key:
                print("❌ GROQ API key missing")
                return False
            
            # Check export directory
            export_dir = Path(config.export_directory)
            export_dir.mkdir(exist_ok=True)
            
            if not os.access(export_dir, os.W_OK):
                print(f"❌ Export directory not writable: {export_dir}")
                return False
            
            print("✅ Health check passed")
            return True
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    def display_configuration(self, config: PipelineConfig):
        """Display current configuration"""
        print("\n🔧 CURRENT CONFIGURATION")
        print("="*50)
        
        config_dict = config.to_dict()
        
        # Group by categories
        categories = {
            "Performance": ['latency_threshold_ms', 'target_throughput', 'message_batch_size'],
            "Agents": ['default_agent', 'max_agent_swaps', 'openai_model', 'groq_model'],
            "System": ['max_message_queue_size', 'max_memory_usage_mb'],
            "Monitoring": ['enable_csv_export', 'export_directory', 'metrics_update_interval_seconds'],
            "Deployment": ['deployment_env', 'log_level']
        }
        
        for category, fields in categories.items():
            print(f"\n📂 {category}:")
            for field in fields:
                if field in config_dict:
                    value = config_dict[field]
                    print(f"   {field}: {value}")
        
        print("="*50)


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="High-Velocity AI Pipeline for Financial Trading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                              # Run with environment config
  python run_pipeline.py --config config/production.json  # Use specific config
  python run_pipeline.py --dev                        # Development mode
  python run_pipeline.py --duration 300               # Run for 5 minutes
  python run_pipeline.py --health-check               # Check system health
  python run_pipeline.py --show-config                # Display configuration
        """
    )
    
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--dev', action='store_true', help='Enable development mode')
    parser.add_argument('--duration', type=float, help='Run duration in seconds')
    parser.add_argument('--health-check', action='store_true', help='Run health check only')
    parser.add_argument('--show-config', action='store_true', help='Show configuration and exit')
    parser.add_argument('--benchmark', action='store_true', help='Enable benchmark mode')
    parser.add_argument('--quiet', action='store_true', help='Reduce output verbosity')
    
    args = parser.parse_args()
    
    # Create runner
    runner = PipelineRunner()
    
    try:
        # Load configuration
        config = runner.load_configuration(args.config, args.dev or args.benchmark)
        
        # Benchmark mode overrides
        if args.benchmark:
            config.target_throughput = 1000.0  # High throughput for benchmarking
            config.latency_threshold_ms = 80.0  # Stricter latency requirements
            config.log_level = "WARNING"  # Reduce logging overhead
            config.market_symbols_count = 20  # More symbols for load
            print("🏁 Benchmark mode enabled")
        
        # Setup logging
        if not args.quiet:
            runner.setup_logging(config)
        
        # Handle specific commands
        if args.health_check:
            success = runner.run_health_check(config)
            sys.exit(0 if success else 1)
        
        if args.show_config:
            runner.display_configuration(config)
            return
        
        # Run the pipeline
        if not args.quiet:
            print(f"🌟 High-Velocity AI Pipeline v1.0.0")
            print(f"🔧 Mode: {'Development' if args.dev else 'Benchmark' if args.benchmark else 'Production'}")
        
        # Execute pipeline
        asyncio.run(runner.run_pipeline(config, args.duration))
        
    except KeyboardInterrupt:
        print("\n👋 Pipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()