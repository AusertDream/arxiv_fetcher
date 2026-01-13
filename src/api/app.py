"""Flask application factory for arXiv RAG API."""

from flask import Flask
from flask_restx import Api
from omegaconf import DictConfig


def create_app(config: DictConfig, builder=None, searcher=None) -> Flask:
    """
    Create and configure Flask application.

    Args:
        config: OmegaConf configuration object
        builder: ArxivDatabaseBuilder instance
        searcher: ArxivSearcher instance

    Returns:
        Configured Flask application
    """
    app = Flask(__name__)

    # Store config and instances in app
    app.config['ARXIV_CONFIG'] = config
    app.config['BUILDER'] = builder
    app.config['SEARCHER'] = searcher

    # Initialize Flask-RESTX with Swagger UI
    api = Api(
        app,
        version='1.0',
        title='arXiv RAG API',
        description='RESTful API for arXiv AI/LLM paper search and management',
        doc='/docs',  # Swagger UI at /docs
        prefix='/api/v1'
    )

    # Register routes
    from .routes import register_routes
    register_routes(api)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500

    return app
