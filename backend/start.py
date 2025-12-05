#!/usr/bin/env python3
"""
Comprehensive startup script for the RAG API application.
Handles:
1. Docker services startup (PostgreSQL, Redis, MinIO, Qdrant, Prometheus, Loki, Grafana)
2. Application startup
"""
import subprocess
import sys
import time
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9091")
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")


def run_command(cmd, check=True, shell=False, capture_output=False):
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        if isinstance(cmd, str):
            result = subprocess.run(
                cmd, shell=True, check=check, 
                capture_output=capture_output, text=True
            )
        else:
            result = subprocess.run(
                cmd, check=check, shell=shell,
                capture_output=capture_output, text=True
            )
        if capture_output:
            return result.stdout.strip()
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if capture_output and e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        if check:
            return False
        return False


def wait_for_service(url, service_name, max_wait=20, check_path="/ping"):
    """Wait for a service to be ready."""
    print(f"Waiting for {service_name} to be ready...")
    waited = 0
    while waited < max_wait:
        try:
            response = requests.get(f"{url}{check_path}", timeout=5)
            if response.status_code in [200, 204]:
                print(f"✓ {service_name} is ready!")
                return True
        except (requests.exceptions.RequestException, requests.exceptions.ConnectionError):
            pass
        
        time.sleep(2)
        waited += 2
        if waited % 10 == 0:
            print(f"  Still waiting... ({waited}/{max_wait}s)")
    
    print(f"✗ {service_name} did not become ready within {max_wait} seconds")
    return False


def start_docker_services(rebuild=False):
    """Start all Docker services using docker-compose."""
    print("\n" + "="*60)
    print("STEP 1: Starting Docker Services")
    print("="*60)
    
    # Check if docker-compose is available
    if not run_command(["docker-compose", "--version"], check=False, capture_output=True):
        print("Error: docker-compose not found. Please install docker-compose.")
        sys.exit(1)
    
    # Start services
    if rebuild:
        print("Rebuilding and starting Docker services...")
        run_command(["docker-compose", "up", "-d", "--build"])
    else:
        print("Starting Docker services (use --rebuild to rebuild images)...")
        run_command(["docker-compose", "up", "-d"])
    
    # Wait for key services
    print("\nWaiting for services to be healthy...")
    
    # Check PostgreSQL using pg_isready (wait for container to be running first)
    print("Checking PostgreSQL...")
    postgres_ready = False
    
    # First, wait for container to exist and be running
    for i in range(30): 
        result = run_command(
            ["docker", "ps", "--filter", "name=postgres", "--format", "{{.Status}}"],
            check=False,
            capture_output=True
        )
        if result and "Up" in result:
            break
        time.sleep(2)
    
    # Now check if PostgreSQL is ready to accept connections
    for i in range(60):  
        result = run_command(
            ["docker", "exec", "postgres", "pg_isready", "-U", "postgres", "-d", "hcp"],
            check=False,
            capture_output=True
        )
        if result and ("accepting connections" in result.lower() or result.strip() == "/var/run/postgresql:5432 - accepting connections"):
            print("✓ PostgreSQL is ready!")
            postgres_ready = True
            break
        time.sleep(2)
        if i % 5 == 0 and i > 0:
            print(f"  Still waiting for PostgreSQL... ({i*2}s)")
    
    if not postgres_ready:
        print("Warning: PostgreSQL may not be fully ready, but continuing...")
    
    # Check other HTTP services
    http_services = [
        ("http://localhost:6379", "Redis", "/"),
        ("http://localhost:9000", "MinIO", "/minio/health/live"),
        ("http://localhost:6333", "Qdrant", "/health"),
        (PROMETHEUS_URL, "Prometheus", "/-/healthy"),
        (LOKI_URL, "Loki", "/ready"),
        (GRAFANA_URL, "Grafana", "/api/health"),
    ]
    
    for url, name, path in http_services:
        if not wait_for_service(url, name, max_wait=20, check_path=path):
            print(f"Warning: {name} may not be fully ready, but continuing...")
    
    print("\n✓ All Docker services started!")
    return True


def verify_observability_stack():
    """Verify Prometheus and Loki are ready."""
    print("\n" + "="*60)
    print("STEP 2: Verifying Observability Stack")
    print("="*60)
    
    # Check Prometheus
    print("Checking Prometheus...")
    if wait_for_service(PROMETHEUS_URL, "Prometheus", max_wait=30, check_path="/-/healthy"):
        print("✓ Prometheus is ready!")
    else:
        print("⚠ Warning: Prometheus may not be fully ready")
    
    # Check Loki
    print("Checking Loki...")
    if wait_for_service(LOKI_URL, "Loki", max_wait=30, check_path="/ready"):
        print("✓ Loki is ready!")
    else:
        print("⚠ Warning: Loki may not be fully ready")
    
    # Check Grafana datasources (Prometheus and Loki are auto-provisioned)
    print("Checking Grafana...")
    if wait_for_service(GRAFANA_URL, "Grafana", max_wait=30, check_path="/api/health"):
        print("✓ Grafana is ready!")
        print("  Prometheus and Loki datasources are auto-provisioned")
    else:
        print("⚠ Warning: Grafana may not be fully ready")
    
    return True


def start_application():
    """Start the FastAPI application."""
    print("\n" + "="*60)
    print("STEP 3: Starting Application")
    print("="*60)
    
    import uvicorn
    
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting RAG API server...")
    print(f"Server will run on: http://{host}:{port}")
    print("\n" + "="*60)
    print("Application is ready!")
    print("="*60)
    print(f"\nAPI: http://{host}:{port}")
    print(f"Metrics: http://{host}:{port}/metrics")
    print(f"Prometheus: {PROMETHEUS_URL}")
    print(f"Loki: {LOKI_URL}")
    print(f"Grafana: {GRAFANA_URL}")
    print(f"MinIO Console: http://localhost:9001")
    print("\nPress Ctrl+C to stop the server\n")
    
 
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    workers = int(os.getenv("UVICORN_WORKERS", "1" if not is_production else "2"))
    
    if is_production:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            workers=workers,
            log_level="info",
            access_log=True,
            reload=False
        )
    else:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True,
            log_level="info",
            access_log=True
        )


def cleanup_docker_resources():
    """Clean up Docker volumes and networks before rebuild."""
    print("\n" + "="*60)
    print("Cleaning up Docker resources...")
    print("="*60)
    
    # Stop and remove containers
    print("Stopping containers...")
    run_command(["docker-compose", "down", "-v"], check=False)
    
    # Remove unused volumes
    print("Removing unused volumes...")
    run_command(["docker", "volume", "prune", "-f"], check=False)
    
    # Remove unused networks
    print("Removing unused networks...")
    run_command(["docker", "network", "prune", "-f"], check=False)
    
    # Remove dangling images
    print("Removing dangling images...")
    run_command(["docker", "image", "prune", "-f"], check=False)
    
    print("✓ Cleanup complete!")
    return True


def main():
    """Main function to orchestrate the startup process."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Start RAG API application with all services")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild Docker images before starting services"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean up volumes and networks before starting (use with --rebuild)"
    )
    parser.add_argument(
        "--no-app",
        action="store_true",
        help="Only start services and setup, don't start the API server"
    )
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("RAG API Startup Script")
    print("="*60)
    print("\nThis script will:")
    print("  1. Start all Docker services (PostgreSQL, Redis, MinIO, Qdrant, Prometheus, Loki, Grafana)")
    print("  2. Verify observability stack (Prometheus, Loki, Grafana)")
    if not args.no_app:
        print("  3. Start the FastAPI application")
    print("\n" + "="*60)
    
    try:
        # Cleanup if requested
        if args.clean:
            cleanup_docker_resources()
            print("\nWaiting 3 seconds after cleanup...")
            time.sleep(3)
        
        # Step 1: Start Docker services
        if not start_docker_services(rebuild=args.rebuild):
            print("Failed to start Docker services. Exiting.")
            sys.exit(1)
        
        # Give services a moment to fully initialize
        print("\nWaiting 5 seconds for services to stabilize...")
        time.sleep(5)
        
        # Step 2: Verify observability stack
        verify_observability_stack()
        
        # Step 3: Start the application (unless --no-app flag is set)
        if not args.no_app:
            start_application()
        else:
            print("\n" + "="*60)
            print("Setup Complete!")
            print("="*60)
            print("\nAll services are running. Start the API server manually with:")
            print("  python3 start.py --no-app  # (services already running)")
            print("  or")
            print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8080")
            print(f"\nAPI: http://0.0.0.0:8080")
            print(f"Metrics: http://0.0.0.0:8080/metrics")
            print(f"Prometheus: {PROMETHEUS_URL}")
            print(f"Loki: {LOKI_URL}")
            print(f"Grafana: {GRAFANA_URL}")
            print(f"MinIO Console: http://localhost:9001")
        
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
