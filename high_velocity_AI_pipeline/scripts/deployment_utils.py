#!/usr/bin/env python3
"""
Deployment Utils - Production Deployment Automation
Utilities for deploying and managing the high-velocity pipeline in production
"""

import asyncio
import argparse
import json
import sys
import os
import subprocess
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config_manager import PipelineConfig, ConfigurationManager

class DeploymentManager:
    """
    Production deployment manager
    
    Handles:
    - Docker deployments
    - Kubernetes deployments
    - Environment validation
    - Health monitoring
    - Rollback procedures
    """
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.deployment_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def validate_prerequisites(self) -> bool:
        """Validate deployment prerequisites"""
        print("🔍 Validating deployment prerequisites...")
        
        checks = []
        
        # Check Docker
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                checks.append(("Docker", True, result.stdout.strip()))
            else:
                checks.append(("Docker", False, "Docker not available"))
        except FileNotFoundError:
            checks.append(("Docker", False, "Docker command not found"))
        
        # Check Docker Compose
        try:
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                checks.append(("Docker Compose", True, result.stdout.strip()))
            else:
                checks.append(("Docker Compose", False, "Docker Compose not available"))
        except FileNotFoundError:
            checks.append(("Docker Compose", False, "Docker Compose command not found"))
        
        # Check environment file
        env_file = self.project_root / ".env"
        if env_file.exists():
            checks.append(("Environment File", True, f"Found: {env_file}"))
        else:
            checks.append(("Environment File", False, "Missing .env file"))
        
        # Check configuration
        config_file = self.project_root / "config" / f"{self.environment}.json"
        if config_file.exists():
            checks.append(("Configuration", True, f"Found: {config_file}"))
        else:
            checks.append(("Configuration", False, f"Missing config for {self.environment}"))
        
        # Print results
        all_passed = True
        for name, passed, details in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {name}: {details}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def build_docker_image(self, tag: Optional[str] = None) -> bool:
        """Build Docker image"""
        if tag is None:
            tag = f"high-velocity-pipeline:{self.deployment_timestamp}"
        
        print(f"🏗️ Building Docker image: {tag}")
        
        try:
            # Build production image
            cmd = [
                'docker', 'build',
                '-t', tag,
                '--target', 'production',
                str(self.project_root)
            ]
            
            result = subprocess.run(cmd, cwd=self.project_root)
            
            if result.returncode == 0:
                print(f"✅ Docker image built successfully: {tag}")
                return True
            else:
                print(f"❌ Docker build failed")
                return False
                
        except Exception as e:
            print(f"❌ Docker build error: {e}")
            return False
    
    def deploy_docker_compose(self, detached: bool = True) -> bool:
        """Deploy using Docker Compose"""
        print(f"🚀 Deploying with Docker Compose...")
        
        try:
            # Build and start services
            cmd = ['docker-compose', 'up']
            if detached:
                cmd.append('-d')
            
            # Add build flag
            cmd.append('--build')
            
            result = subprocess.run(cmd, cwd=self.project_root)
            
            if result.returncode == 0:
                print("✅ Docker Compose deployment successful")
                
                # Show running services
                self.show_docker_status()
                return True
            else:
                print("❌ Docker Compose deployment failed")
                return False
                
        except Exception as e:
            print(f"❌ Docker Compose error: {e}")
            return False
    
    def deploy_kubernetes(self, namespace: str = "default") -> bool:
        """Deploy to Kubernetes"""
        print(f"☸️ Deploying to Kubernetes namespace: {namespace}")
        
        k8s_dir = self.project_root / "k8s"
        if not k8s_dir.exists():
            print("❌ Kubernetes manifests not found")
            return False
        
        try:
            # Check kubectl
            result = subprocess.run(['kubectl', 'version', '--client'], capture_output=True)
            if result.returncode != 0:
                print("❌ kubectl not available")
                return False
            
            # Create namespace if it doesn't exist
            subprocess.run(['kubectl', 'create', 'namespace', namespace], capture_output=True)
            
            # Apply manifests
            manifest_files = list(k8s_dir.glob("*.yaml"))
            
            for manifest in manifest_files:
                print(f"  📄 Applying {manifest.name}")
                cmd = ['kubectl', 'apply', '-f', str(manifest), '-n', namespace]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"❌ Failed to apply {manifest.name}: {result.stderr}")
                    return False
            
            print("✅ Kubernetes deployment successful")
            
            # Show deployment status
            self.show_kubernetes_status(namespace)
            return True
            
        except Exception as e:
            print(f"❌ Kubernetes deployment error: {e}")
            return False
    
    def show_docker_status(self):
        """Show Docker container status"""
        print("\n📊 Docker Container Status:")
        try:
            result = subprocess.run(
                ['docker-compose', 'ps'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            print(result.stdout)
        except Exception as e:
            print(f"Error getting Docker status: {e}")
    
    def show_kubernetes_status(self, namespace: str = "default"):
        """Show Kubernetes deployment status"""
        print(f"\n📊 Kubernetes Status (namespace: {namespace}):")
        try:
            # Show pods
            result = subprocess.run(
                ['kubectl', 'get', 'pods', '-n', namespace],
                capture_output=True,
                text=True
            )
            print("Pods:")
            print(result.stdout)
            
            # Show services
            result = subprocess.run(
                ['kubectl', 'get', 'services', '-n', namespace],
                capture_output=True,
                text=True
            )
            print("Services:")
            print(result.stdout)
            
        except Exception as e:
            print(f"Error getting Kubernetes status: {e}")
    
    def generate_env_template(self):
        """Generate environment template for deployment"""
        template_path = self.project_root / f".env.{self.environment}"
        
        template_content = f"""# High-Velocity AI Pipeline - {self.environment.upper()} Environment
# Generated: {datetime.now().isoformat()}

# =============================================================================
# API KEYS (REQUIRED - REPLACE WITH ACTUAL VALUES)
# =============================================================================
OPENAI_API_KEY=your-openai-key-here
GROQ_API_KEY=your-groq-key-here
WANDB_API_KEY=your-wandb-key-here

# =============================================================================
# DEPLOYMENT CONFIGURATION
# =============================================================================
DEPLOYMENT_ENV={self.environment}
INSTANCE_ID=hvp-{self.environment}-001
DEPLOYMENT_TIMESTAMP={self.deployment_timestamp}

# =============================================================================
# PIPELINE CONFIGURATION (PRODUCTION TUNED)
# =============================================================================
PIPELINE_LATENCY_THRESHOLD_MS=100
PIPELINE_SAFE_LATENCY_THRESHOLD_MS=70
PIPELINE_SAFE_THROUGHPUT_THRESHOLD=600
PIPELINE_COOLDOWN_PERIOD_SECONDS=20
PIPELINE_TARGET_THROUGHPUT=800
PIPELINE_MESSAGE_BATCH_SIZE=100

# =============================================================================
# MONITORING AND LOGGING
# =============================================================================
PIPELINE_ENABLE_CSV_EXPORT=true
PIPELINE_ENABLE_WEAVE_TRACING=true
PIPELINE_LOG_LEVEL=INFO
PIPELINE_EXPORT_DIRECTORY=exports

# =============================================================================
# HEALTH AND MONITORING PORTS
# =============================================================================
HEALTH_CHECK_PORT=8080
METRICS_PORT=8081
"""
        
        with open(template_path, 'w') as f:
            f.write(template_content)
        
        print(f"📝 Environment template created: {template_path}")
        print(f"⚠️  Please update with actual API keys before deployment!")
    
    def create_kubernetes_manifests(self):
        """Create Kubernetes deployment manifests"""
        k8s_dir = self.project_root / "k8s"
        k8s_dir.mkdir(exist_ok=True)
        
        # Deployment manifest
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "high-velocity-pipeline",
                "labels": {"app": "hvp"}
            },
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": "hvp"}},
                "template": {
                    "metadata": {"labels": {"app": "hvp"}},
                    "spec": {
                        "containers": [{
                            "name": "hvp-pipeline",
                            "image": "high-velocity-pipeline:latest",
                            "ports": [
                                {"containerPort": 8080, "name": "health"},
                                {"containerPort": 8081, "name": "metrics"}
                            ],
                            "env": [
                                {"name": "DEPLOYMENT_ENV", "value": "kubernetes"},
                                {"name": "OPENAI_API_KEY", "valueFrom": {"secretKeyRef": {"name": "hvp-secrets", "key": "openai-api-key"}}},
                                {"name": "GROQ_API_KEY", "valueFrom": {"secretKeyRef": {"name": "hvp-secrets", "key": "groq-api-key"}}},
                                {"name": "WANDB_API_KEY", "valueFrom": {"secretKeyRef": {"name": "hvp-secrets", "key": "wandb-api-key"}}}
                            ],
                            "livenessProbe": {
                                "httpGet": {"path": "/health", "port": 8080},
                                "initialDelaySeconds": 60,
                                "periodSeconds": 30
                            },
                            "readinessProbe": {
                                "httpGet": {"path": "/health", "port": 8080},
                                "initialDelaySeconds": 30,
                                "periodSeconds": 10
                            },
                            "resources": {
                                "requests": {"memory": "1Gi", "cpu": "500m"},
                                "limits": {"memory": "2Gi", "cpu": "1000m"}
                            }
                        }],
                        "imagePullPolicy": "IfNotPresent"
                    }
                }
            }
        }
        
        # Service manifest
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": "hvp-service",
                "labels": {"app": "hvp"}
            },
            "spec": {
                "selector": {"app": "hvp"},
                "ports": [
                    {"name": "health", "port": 8080, "targetPort": 8080},
                    {"name": "metrics", "port": 8081, "targetPort": 8081}
                ],
                "type": "ClusterIP"
            }
        }
        
        # ConfigMap for configuration
        config_map = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "hvp-config",
                "labels": {"app": "hvp"}
            },
            "data": {
                "production.json": json.dumps({
                    "performance_thresholds": {
                        "latency_threshold_ms": 100.0,
                        "safe_latency_threshold_ms": 70.0,
                        "safe_throughput_threshold": 600.0,
                        "cooldown_period_seconds": 20.0
                    },
                    "target_performance": {
                        "target_throughput": 800.0,
                        "message_batch_size": 100,
                        "batch_interval_seconds": 0.125
                    }
                }, indent=2)
            }
        }
        
        # Secrets template
        secrets = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": "hvp-secrets",
                "labels": {"app": "hvp"}
            },
            "type": "Opaque",
            "stringData": {
                "openai-api-key": "your-openai-key-here",
                "groq-api-key": "your-groq-key-here",
                "wandb-api-key": "your-wandb-key-here"
            }
        }
        
        # Write manifests
        manifests = [
            ("deployment.yaml", deployment),
            ("service.yaml", service),
            ("configmap.yaml", config_map),
            ("secrets.yaml", secrets)
        ]
        
        for filename, manifest in manifests:
            with open(k8s_dir / filename, 'w') as f:
                yaml.dump(manifest, f, default_flow_style=False)
        
        print(f"📝 Kubernetes manifests created in: {k8s_dir}")
        print("⚠️  Update secrets.yaml with actual API keys before applying!")
    
    async def health_check_loop(self, endpoint: str = "http://localhost:8080/health", max_attempts: int = 30):
        """Monitor deployment health"""
        print(f"🏥 Monitoring deployment health: {endpoint}")
        
        import aiohttp
        
        for attempt in range(max_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            health_data = await response.json()
                            overall_status = health_data.get("overall_status", "unknown")
                            
                            if overall_status in ["healthy", "degraded"]:
                                print(f"✅ Deployment healthy (attempt {attempt + 1})")
                                return True
                            else:
                                print(f"⚠️ Deployment status: {overall_status} (attempt {attempt + 1})")
                        else:
                            print(f"❌ Health check failed: HTTP {response.status} (attempt {attempt + 1})")
                            
            except Exception as e:
                print(f"🔄 Health check error: {e} (attempt {attempt + 1})")
            
            if attempt < max_attempts - 1:
                await asyncio.sleep(10)  # Wait 10 seconds between attempts
        
        print(f"❌ Deployment health check failed after {max_attempts} attempts")
        return False
    
    def rollback_docker_compose(self):
        """Rollback Docker Compose deployment"""
        print("🔄 Rolling back Docker Compose deployment...")
        
        try:
            # Stop current deployment
            subprocess.run(['docker-compose', 'down'], cwd=self.project_root)
            
            # Could implement more sophisticated rollback logic here
            print("✅ Rollback completed")
            
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
    
    def cleanup_deployment(self):
        """Cleanup deployment resources"""
        print("🧹 Cleaning up deployment resources...")
        
        try:
            # Stop Docker Compose
            subprocess.run(['docker-compose', 'down', '-v'], cwd=self.project_root, capture_output=True)
            
            # Remove unused Docker images
            subprocess.run(['docker', 'image', 'prune', '-f'], capture_output=True)
            
            print("✅ Cleanup completed")
            
        except Exception as e:
            print(f"❌ Cleanup error: {e}")

def main():
    """Main entry point for deployment utils"""
    parser = argparse.ArgumentParser(
        description="High-Velocity Pipeline Deployment Utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/deployment_utils.py deploy-docker           # Deploy with Docker Compose
  python scripts/deployment_utils.py deploy-k8s             # Deploy to Kubernetes
  python scripts/deployment_utils.py build --tag v1.0       # Build Docker image
  python scripts/deployment_utils.py health-check           # Monitor deployment health
  python scripts/deployment_utils.py generate-manifests     # Create K8s manifests
  python scripts/deployment_utils.py cleanup                # Cleanup resources
        """
    )
    
    parser.add_argument('command', choices=[
        'deploy-docker', 'deploy-k8s', 'build', 'health-check',
        'generate-manifests', 'generate-env', 'status', 'cleanup', 'rollback'
    ], help='Deployment command to execute')
    
    parser.add_argument('--environment', default='production', help='Deployment environment')
    parser.add_argument('--tag', help='Docker image tag')
    parser.add_argument('--namespace', default='default', help='Kubernetes namespace')
    parser.add_argument('--endpoint', default='http://localhost:8080/health', help='Health check endpoint')
    parser.add_argument('--detached', action='store_true', help='Run in detached mode')
    
    args = parser.parse_args()
    
    try:
        deployer = DeploymentManager(args.environment)
        
        if args.command == 'deploy-docker':
            if deployer.validate_prerequisites():
                success = deployer.deploy_docker_compose(detached=args.detached)
                if success:
                    # Monitor health
                    healthy = asyncio.run(deployer.health_check_loop(args.endpoint))
                    if not healthy:
                        print("⚠️ Deployment completed but health check failed")
                        sys.exit(1)
                else:
                    sys.exit(1)
            else:
                print("❌ Prerequisites validation failed")
                sys.exit(1)
        
        elif args.command == 'deploy-k8s':
            if deployer.validate_prerequisites():
                success = deployer.deploy_kubernetes(args.namespace)
                sys.exit(0 if success else 1)
            else:
                sys.exit(1)
        
        elif args.command == 'build':
            success = deployer.build_docker_image(args.tag)
            sys.exit(0 if success else 1)
        
        elif args.command == 'health-check':
            healthy = asyncio.run(deployer.health_check_loop(args.endpoint))
            sys.exit(0 if healthy else 1)
        
        elif args.command == 'generate-manifests':
            deployer.create_kubernetes_manifests()
        
        elif args.command == 'generate-env':
            deployer.generate_env_template()
        
        elif args.command == 'status':
            deployer.show_docker_status()
            deployer.show_kubernetes_status(args.namespace)
        
        elif args.command == 'cleanup':
            deployer.cleanup_deployment()
        
        elif args.command == 'rollback':
            deployer.rollback_docker_compose()
        
    except KeyboardInterrupt:
        print("\n👋 Deployment interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Deployment error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()