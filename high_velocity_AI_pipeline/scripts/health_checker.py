#!/usr/bin/env python3
"""
Health Checker - Pipeline Health Monitoring and Diagnostics
Comprehensive health checking for the high-velocity pipeline system
"""

import asyncio
import argparse
import json
import sys
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import urllib.request
import urllib.error

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config_manager import PipelineConfig, ConfigurationManager
from performance_monitor import PerformanceMonitor

class HealthStatus:
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class HealthCheck:
    """Individual health check result"""
    
    def __init__(self, name: str, status: str, message: str, details: Dict[str, Any] = None):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }

class SystemHealthChecker:
    """
    Comprehensive system health checker
    
    Performs various health checks including:
    - Configuration validation
    - API connectivity
    - System resources
    - File permissions
    - Performance metrics
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig.load_from_env()
        self.checks: List[HealthCheck] = []
        
        # Configure logging
        logging.basicConfig(level=logging.WARNING)
        self.logger = logging.getLogger(__name__)
    
    def add_check(self, check: HealthCheck):
        """Add a health check result"""
        self.checks.append(check)
    
    def check_configuration(self) -> HealthCheck:
        """Check configuration validity"""
        try:
            if self.config.validate():
                return HealthCheck(
                    "configuration",
                    HealthStatus.HEALTHY,
                    "Configuration is valid",
                    {
                        "latency_threshold": self.config.latency_threshold_ms,
                        "target_throughput": self.config.target_throughput,
                        "batch_size": self.config.message_batch_size
                    }
                )
            else:
                return HealthCheck(
                    "configuration",
                    HealthStatus.UNHEALTHY,
                    "Configuration validation failed"
                )
        except Exception as e:
            return HealthCheck(
                "configuration",
                HealthStatus.CRITICAL,
                f"Configuration error: {e}"
            )
    
    def check_environment_variables(self) -> HealthCheck:
        """Check required environment variables"""
        required_vars = ['OPENAI_API_KEY', 'GROQ_API_KEY']
        optional_vars = ['WANDB_API_KEY']
        
        missing_required = []
        missing_optional = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)
        
        for var in optional_vars:
            if not os.getenv(var):
                missing_optional.append(var)
        
        if missing_required:
            return HealthCheck(
                "environment_variables",
                HealthStatus.CRITICAL,
                f"Missing required environment variables: {', '.join(missing_required)}",
                {
                    "missing_required": missing_required,
                    "missing_optional": missing_optional
                }
            )
        elif missing_optional:
            return HealthCheck(
                "environment_variables",
                HealthStatus.DEGRADED,
                f"Missing optional environment variables: {', '.join(missing_optional)}",
                {
                    "missing_optional": missing_optional
                }
            )
        else:
            return HealthCheck(
                "environment_variables",
                HealthStatus.HEALTHY,
                "All environment variables present"
            )
    
    def check_api_connectivity(self) -> HealthCheck:
        """Check API connectivity"""
        api_status = {}
        overall_status = HealthStatus.HEALTHY
        
        # Check OpenAI API
        try:
            # Simple connectivity test (doesn't use actual API key)
            response = urllib.request.urlopen('https://api.openai.com/v1/models', timeout=10)
            if response.status == 200 or response.status == 401:  # 401 is OK (auth required)
                api_status['openai'] = 'reachable'
            else:
                api_status['openai'] = f'error_{response.status}'
                overall_status = HealthStatus.DEGRADED
        except Exception as e:
            api_status['openai'] = f'unreachable: {str(e)[:50]}'
            overall_status = HealthStatus.DEGRADED
        
        # Check GROQ API
        try:
            response = urllib.request.urlopen('https://api.groq.com/openai/v1/models', timeout=10)
            if response.status == 200 or response.status == 401:
                api_status['groq'] = 'reachable'
            else:
                api_status['groq'] = f'error_{response.status}'
                overall_status = HealthStatus.DEGRADED
        except Exception as e:
            api_status['groq'] = f'unreachable: {str(e)[:50]}'
            overall_status = HealthStatus.DEGRADED
        
        # Check Weights & Biases (optional)
        try:
            response = urllib.request.urlopen('https://api.wandb.ai/api/v1/files', timeout=10)
            api_status['wandb'] = 'reachable'
        except Exception as e:
            api_status['wandb'] = f'unreachable: {str(e)[:50]}'
            # Don't degrade overall status for optional service
        
        message = "API connectivity check completed"
        if overall_status != HealthStatus.HEALTHY:
            message += " with issues"
        
        return HealthCheck(
            "api_connectivity",
            overall_status,
            message,
            api_status
        )
    
    def check_system_resources(self) -> HealthCheck:
        """Check system resource availability"""
        try:
            import psutil
            
            # Memory check
            memory = psutil.virtual_memory()
            available_memory_mb = memory.available / 1024 / 1024
            memory_usage_percent = memory.percent
            
            # CPU check
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Disk check
            disk = psutil.disk_usage('/')
            disk_free_gb = disk.free / 1024 / 1024 / 1024
            disk_usage_percent = (disk.used / disk.total) * 100
            
            # Determine status
            status = HealthStatus.HEALTHY
            issues = []
            
            if available_memory_mb < 500:  # Less than 500MB available
                status = HealthStatus.DEGRADED
                issues.append("Low available memory")
            
            if memory_usage_percent > 90:
                status = HealthStatus.UNHEALTHY
                issues.append("High memory usage")
            
            if cpu_percent > 80:
                status = HealthStatus.DEGRADED
                issues.append("High CPU usage")
            
            if disk_free_gb < 1:  # Less than 1GB free
                status = HealthStatus.DEGRADED
                issues.append("Low disk space")
            
            if cpu_count < 2:
                issues.append("Limited CPU cores")
            
            message = "System resources OK" if not issues else f"Issues: {', '.join(issues)}"
            
            return HealthCheck(
                "system_resources",
                status,
                message,
                {
                    "memory": {
                        "available_mb": round(available_memory_mb),
                        "usage_percent": round(memory_usage_percent, 1)
                    },
                    "cpu": {
                        "usage_percent": round(cpu_percent, 1),
                        "core_count": cpu_count
                    },
                    "disk": {
                        "free_gb": round(disk_free_gb, 1),
                        "usage_percent": round(disk_usage_percent, 1)
                    }
                }
            )
            
        except ImportError:
            return HealthCheck(
                "system_resources",
                HealthStatus.UNKNOWN,
                "psutil not available - cannot check system resources",
                {"psutil_available": False}
            )
        except Exception as e:
            return HealthCheck(
                "system_resources",
                HealthStatus.UNKNOWN,
                f"Resource check failed: {e}"
            )
    
    def check_file_permissions(self) -> HealthCheck:
        """Check file and directory permissions"""
        checks = {}
        status = HealthStatus.HEALTHY
        
        # Check export directory
        export_dir = Path(self.config.export_directory)
        try:
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permission
            test_file = export_dir / ".health_check"
            test_file.write_text("test")
            test_file.unlink()
            
            checks['export_directory'] = 'writable'
        except Exception as e:
            checks['export_directory'] = f'not_writable: {e}'
            status = HealthStatus.UNHEALTHY
        
        # Check logs directory
        if self.config.log_file:
            log_dir = Path(self.config.log_file).parent
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                
                # Test write permission
                test_file = log_dir / ".health_check"
                test_file.write_text("test")
                test_file.unlink()
                
                checks['log_directory'] = 'writable'
            except Exception as e:
                checks['log_directory'] = f'not_writable: {e}'
                status = HealthStatus.DEGRADED
        
        # Check config directory
        config_dir = Path("config")
        if config_dir.exists():
            checks['config_directory'] = 'readable' if os.access(config_dir, os.R_OK) else 'not_readable'
        else:
            checks['config_directory'] = 'missing'
            status = HealthStatus.DEGRADED
        
        message = "File permissions OK" if status == HealthStatus.HEALTHY else "File permission issues detected"
        
        return HealthCheck(
            "file_permissions",
            status,
            message,
            checks
        )
    
    def check_recent_performance(self) -> HealthCheck:
        """Check recent performance metrics"""
        exports_dir = Path(self.config.export_directory)
        
        if not exports_dir.exists():
            return HealthCheck(
                "recent_performance",
                HealthStatus.UNKNOWN,
                "No exports directory found - pipeline may not have run yet"
            )
        
        # Look for recent performance files
        recent_files = []
        cutoff_time = time.time() - 3600  # Last hour
        
        for file_path in exports_dir.glob("pipeline_report_*.json"):
            if file_path.stat().st_mtime > cutoff_time:
                recent_files.append(file_path)
        
        if not recent_files:
            return HealthCheck(
                "recent_performance",
                HealthStatus.UNKNOWN,
                "No recent performance data found"
            )
        
        # Analyze most recent file
        latest_file = max(recent_files, key=lambda p: p.stat().st_mtime)
        
        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
            
            summary = data.get('pipeline_summary', {})
            p99_latency = summary.get('final_p99_latency_ms', 0)
            success_rate = summary.get('success_rate_percent', 0)
            throughput = summary.get('average_throughput_msg_per_sec', 0)
            
            # Evaluate performance
            status = HealthStatus.HEALTHY
            issues = []
            
            if p99_latency > 150:
                status = HealthStatus.DEGRADED
                issues.append(f"High P99 latency: {p99_latency:.1f}ms")
            
            if success_rate < 95:
                status = HealthStatus.DEGRADED
                issues.append(f"Low success rate: {success_rate:.1f}%")
            
            if throughput < 100:
                status = HealthStatus.DEGRADED
                issues.append(f"Low throughput: {throughput:.1f} msg/s")
            
            message = "Recent performance OK" if not issues else f"Performance issues: {', '.join(issues)}"
            
            return HealthCheck(
                "recent_performance",
                status,
                message,
                {
                    "p99_latency_ms": p99_latency,
                    "success_rate_percent": success_rate,
                    "throughput_msg_per_sec": throughput,
                    "last_run": datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat()
                }
            )
            
        except Exception as e:
            return HealthCheck(
                "recent_performance",
                HealthStatus.UNKNOWN,
                f"Error reading performance data: {e}"
            )
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        print("🔍 Running comprehensive health checks...")
        
        # Run all checks
        checks_to_run = [
            ("Configuration", self.check_configuration),
            ("Environment Variables", self.check_environment_variables),
            ("API Connectivity", self.check_api_connectivity),
            ("System Resources", self.check_system_resources),
            ("File Permissions", self.check_file_permissions),
            ("Recent Performance", self.check_recent_performance)
        ]
        
        self.checks = []
        
        for check_name, check_func in checks_to_run:
            print(f"  📋 {check_name}...", end=" ")
            
            try:
                check_result = check_func()
                self.checks.append(check_result)
                
                # Status indicator
                if check_result.status == HealthStatus.HEALTHY:
                    print("✅")
                elif check_result.status == HealthStatus.DEGRADED:
                    print("⚠️")
                elif check_result.status == HealthStatus.UNHEALTHY:
                    print("❌")
                elif check_result.status == HealthStatus.CRITICAL:
                    print("🚨")
                else:
                    print("❓")
                    
            except Exception as e:
                error_check = HealthCheck(
                    check_name.lower().replace(" ", "_"),
                    HealthStatus.CRITICAL,
                    f"Check failed: {e}"
                )
                self.checks.append(error_check)
                print("💥")
        
        # Calculate overall health
        overall_status = self._calculate_overall_status()
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": [check.to_dict() for check in self.checks],
            "summary": self._generate_summary()
        }
    
    def _calculate_overall_status(self) -> str:
        """Calculate overall system health status"""
        status_counts = {
            HealthStatus.CRITICAL: 0,
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.DEGRADED: 0,
            HealthStatus.HEALTHY: 0,
            HealthStatus.UNKNOWN: 0
        }
        
        for check in self.checks:
            status_counts[check.status] += 1
        
        # Determine overall status
        if status_counts[HealthStatus.CRITICAL] > 0:
            return HealthStatus.CRITICAL
        elif status_counts[HealthStatus.UNHEALTHY] > 0:
            return HealthStatus.UNHEALTHY
        elif status_counts[HealthStatus.DEGRADED] > 1:  # Multiple degraded checks
            return HealthStatus.UNHEALTHY
        elif status_counts[HealthStatus.DEGRADED] > 0:
            return HealthStatus.DEGRADED
        elif status_counts[HealthStatus.UNKNOWN] > 2:  # Too many unknown checks
            return HealthStatus.UNKNOWN
        else:
            return HealthStatus.HEALTHY
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate health check summary"""
        status_counts = {}
        failed_checks = []
        warnings = []
        
        for check in self.checks:
            status_counts[check.status] = status_counts.get(check.status, 0) + 1
            
            if check.status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]:
                failed_checks.append(f"{check.name}: {check.message}")
            elif check.status == HealthStatus.DEGRADED:
                warnings.append(f"{check.name}: {check.message}")
        
        return {
            "total_checks": len(self.checks),
            "status_counts": status_counts,
            "failed_checks": failed_checks,
            "warnings": warnings,
            "ready_for_production": len(failed_checks) == 0 and len(warnings) <= 1
        }

def print_health_report(health_data: Dict[str, Any]):
    """Print formatted health report"""
    overall_status = health_data["overall_status"]
    
    # Header
    print("\n" + "=" * 60)
    print("🏥 PIPELINE HEALTH CHECK REPORT")
    print("=" * 60)
    print(f"📅 Generated: {health_data['timestamp']}")
    
    # Overall status
    status_icons = {
        HealthStatus.HEALTHY: "🟢",
        HealthStatus.DEGRADED: "🟡", 
        HealthStatus.UNHEALTHY: "🔴",
        HealthStatus.CRITICAL: "🚨",
        HealthStatus.UNKNOWN: "❓"
    }
    
    status_icon = status_icons.get(overall_status, "❓")
    print(f"🎯 Overall Status: {status_icon} {overall_status.upper()}")
    
    # Summary
    summary = health_data["summary"]
    print(f"\n📊 Summary: {summary['total_checks']} checks performed")
    print(f"✅ Ready for production: {'Yes' if summary['ready_for_production'] else 'No'}")
    
    # Status breakdown
    if summary["status_counts"]:
        print(f"\n📈 Status Breakdown:")
        for status, count in summary["status_counts"].items():
            icon = status_icons.get(status, "❓")
            print(f"  {icon} {status}: {count}")
    
    # Failed checks
    if summary["failed_checks"]:
        print(f"\n❌ Failed Checks:")
        for check in summary["failed_checks"]:
            print(f"  • {check}")
    
    # Warnings
    if summary["warnings"]:
        print(f"\n⚠️ Warnings:")
        for warning in summary["warnings"]:
            print(f"  • {warning}")
    
    # Detailed results
    print(f"\n📋 Detailed Results:")
    for check_data in health_data["checks"]:
        status_icon = status_icons.get(check_data["status"], "❓")
        print(f"  {status_icon} {check_data['name']}: {check_data['message']}")
        
        # Show details for failed/degraded checks
        if check_data["status"] in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY, HealthStatus.DEGRADED] and check_data["details"]:
            for key, value in check_data["details"].items():
                print(f"      {key}: {value}")
    
    print("=" * 60)

async def run_health_endpoint(port: int = 8080):
    """Run health check as HTTP endpoint"""
    try:
        from aiohttp import web
        
        async def health_handler(request):
            checker = SystemHealthChecker()
            health_data = await checker.run_all_checks()
            
            # Return appropriate HTTP status
            status_map = {
                HealthStatus.HEALTHY: 200,
                HealthStatus.DEGRADED: 200,
                HealthStatus.UNHEALTHY: 503,
                HealthStatus.CRITICAL: 503,
                HealthStatus.UNKNOWN: 503
            }
            
            status_code = status_map.get(health_data["overall_status"], 503)
            
            return web.json_response(health_data, status=status_code)
        
        app = web.Application()
        app.router.add_get('/health', health_handler)
        app.router.add_get('/health/detailed', health_handler)
        
        print(f"🌐 Health endpoint running on http://localhost:{port}/health")
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)  # Check every hour
        except KeyboardInterrupt:
            print("\n👋 Health endpoint stopped")
        finally:
            await runner.cleanup()
            
    except ImportError:
        print("❌ aiohttp not available. Install with: pip install aiohttp")
    except Exception as e:
        print(f"❌ Failed to start health endpoint: {e}")

def main():
    """Main entry point for health checker"""
    parser = argparse.ArgumentParser(
        description="High-Velocity Pipeline Health Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/health_checker.py                    # Full health check
  python scripts/health_checker.py --check-only       # Quick check (for Docker health)
  python scripts/health_checker.py --config production.json  # Use specific config
  python scripts/health_checker.py --endpoint         # Run as HTTP endpoint
  python scripts/health_checker.py --json             # Output JSON format
        """
    )
    
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--check-only', action='store_true', help='Quick health check (exit code only)')
    parser.add_argument('--endpoint', action='store_true', help='Run as HTTP health endpoint')
    parser.add_argument('--port', type=int, default=8080, help='Port for HTTP endpoint')
    parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    parser.add_argument('--save-report', type=str, help='Save detailed report to file')
    parser.add_argument('--quiet', action='store_true', help='Suppress output (except errors)')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        if args.config:
            config_manager = ConfigurationManager(args.config)
            config = config_manager.get_config()
        else:
            config = PipelineConfig.load_from_env()
        
        # Run health endpoint
        if args.endpoint:
            asyncio.run(run_health_endpoint(args.port))
            return
        
        # Run health checks
        checker = SystemHealthChecker(config)
        health_data = asyncio.run(checker.run_all_checks())
        
        # Quick check mode (for Docker health checks)
        if args.check_only:
            overall_status = health_data["overall_status"]
            
            if not args.quiet:
                status_icons = {
                    HealthStatus.HEALTHY: "✅",
                    HealthStatus.DEGRADED: "⚠️", 
                    HealthStatus.UNHEALTHY: "❌",
                    HealthStatus.CRITICAL: "🚨",
                    HealthStatus.UNKNOWN: "❓"
                }
                icon = status_icons.get(overall_status, "❓")
                print(f"{icon} {overall_status}")
            
            # Exit with appropriate code
            if overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                sys.exit(0)
            else:
                sys.exit(1)
        
        # Output results
        if args.json:
            print(json.dumps(health_data, indent=2))
        else:
            if not args.quiet:
                print_health_report(health_data)
        
        # Save report if requested
        if args.save_report:
            with open(args.save_report, 'w') as f:
                json.dump(health_data, f, indent=2)
            if not args.quiet:
                print(f"\n💾 Report saved to: {args.save_report}")
        
        # Exit code based on overall health
        overall_status = health_data["overall_status"]
        if overall_status == HealthStatus.HEALTHY:
            sys.exit(0)
        elif overall_status == HealthStatus.DEGRADED:
            sys.exit(0)  # Degraded is still acceptable
        else:
            sys.exit(1)
    
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n👋 Health check interrupted")
        sys.exit(1)
    except Exception as e:
        if not args.quiet:
            print(f"❌ Health check failed: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()