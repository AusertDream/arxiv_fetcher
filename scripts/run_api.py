#!/usr/bin/env python3
"""API server entry point."""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.config_loader import load_config
from src.core.builder import ArxivDatabaseBuilder
from src.core.searcher import ArxivSearcher
from src.api.app import create_app


def main():
    """Run the Flask API server."""
    parser = argparse.ArgumentParser(description='arXiv RAG API Server')
    parser.add_argument('--config', default='config/default.yaml', help='Config file path')
    parser.add_argument('--host', help='Host to bind (overrides config)')
    parser.add_argument('--port', type=int, help='Port to bind (overrides config)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    try:
        # Load configuration
        print("Loading configuration...")
        config = load_config(args.config)

        # Initialize builder and searcher
        print("Initializing builder and searcher...")
        builder = ArxivDatabaseBuilder(config)
        searcher = ArxivSearcher(config, db_manager=builder.db_manager)

        # Create Flask app
        app = create_app(config, builder=builder, searcher=searcher)

        # Get server config
        host = args.host or config.api.host
        port = args.port or config.api.port
        debug = args.debug or config.api.debug

        print("\n" + "="*70)
        print("Starting arXiv RAG API Server")
        print("="*70)
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Debug: {debug}")
        print(f"\nAPI Documentation (Swagger UI):")
        print(f"  http://{host if host != '0.0.0.0' else 'localhost'}:{port}/docs")
        print(f"\nAvailable endpoints:")
        print(f"  GET  /api/v1/health              - Health check")
        print(f"  GET  /api/v1/stats               - Database statistics")
        print(f"  POST /api/v1/search              - Search papers")
        print(f"  POST /api/v1/incremental_update  - Incremental update")
        print(f"  POST /api/v1/add_papers          - Add papers from JSON")
        print(f"  DELETE /api/v1/papers/<id>       - Delete paper")
        print("="*70 + "\n")

        # Run server
        app.run(host=host, port=port, debug=debug)

    except Exception as e:
        print(f"\nError starting server: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
