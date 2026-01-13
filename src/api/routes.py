"""API routes with Flask-RESTX and Swagger documentation."""

from flask import request, current_app
from flask_restx import Api, Namespace, Resource, fields
import os


def register_routes(api: Api):
    """
    Register all API routes.

    Args:
        api: Flask-RESTX Api instance
    """
    # Create namespace (empty path since api already has /api/v1 prefix)
    ns = api.namespace('', description='arXiv paper operations')

    # Define models for Swagger documentation
    search_model = api.model('SearchRequest', {
        'query': fields.String(required=True, description='搜索查询（自然语言）', example='large language models'),
        'top_k': fields.Integer(default=10, description='返回结果数量', example=10)
    })

    incremental_update_model = api.model('IncrementalUpdate', {
        'max_results': fields.Integer(description='最大获取论文数（默认使用config配置：9000，-1表示不限制）', example=9000),
        'batch_size': fields.Integer(description='批次大小（默认使用config配置：50）', example=50)
    })

    add_papers_model = api.model('AddPapers', {
        'json_path': fields.String(required=True, description='JSON 文件路径', example='new_papers.json')
    })

    paper_result_model = api.model('PaperResult', {
        'paper_id': fields.String(description='论文 ID'),
        'title': fields.String(description='论文标题'),
        'authors': fields.List(fields.String, description='作者列表'),
        'published': fields.String(description='发表日期'),
        'url': fields.String(description='论文链接'),
        'score': fields.Float(description='相似度评分'),
        'title_similarity': fields.Float(description='标题相似度'),
        'abstract_similarity': fields.Float(description='摘要相似度')
    })

    search_response_model = api.model('SearchResponse', {
        'results': fields.List(fields.Nested(paper_result_model), description='搜索结果'),
        'query': fields.String(description='查询文本'),
        'top_k': fields.Integer(description='返回数量'),
        'total_results': fields.Integer(description='实际结果数')
    })

    stats_model = api.model('Stats', {
        'total_documents': fields.Integer(description='文档总数'),
        'total_papers': fields.Integer(description='论文总数'),
        'collection_name': fields.String(description='集合名称'),
        'database_path': fields.String(description='数据库路径')
    })

    # Health check endpoint
    @ns.route('/health')
    class Health(Resource):
        @ns.doc('health_check', description='健康检查')
        def get(self):
            """健康检查"""
            return {'status': 'ok', 'service': 'arxiv-rag-api'}

    # Stats endpoint
    @ns.route('/stats')
    class Stats(Resource):
        @ns.doc('get_stats', description='获取数据库统计信息')
        @ns.marshal_with(stats_model)
        def get(self):
            """获取数据库统计"""
            try:
                searcher = current_app.config['SEARCHER']
                return searcher.get_stats()
            except Exception as e:
                api.abort(500, f'Error getting stats: {str(e)}')

    # Search endpoint
    @ns.route('/search')
    class Search(Resource):
        @ns.doc('search_papers', description='使用自然语言搜索论文')
        @ns.expect(search_model, validate=True)
        @ns.marshal_with(search_response_model)
        def post(self):
            """搜索论文"""
            try:
                data = request.json

                if not data or 'query' not in data:
                    api.abort(400, 'Missing query parameter')

                query = data.get('query', '')
                top_k = data.get('top_k')

                searcher = current_app.config['SEARCHER']
                results = searcher.search(query, top_k)

                return {
                    'results': results,
                    'query': query,
                    'top_k': top_k or current_app.config['ARXIV_CONFIG'].search.default_top_k,
                    'total_results': len(results)
                }
            except Exception as e:
                api.abort(500, f'Search error: {str(e)}')

    # Incremental update endpoint
    @ns.route('/incremental_update')
    class IncrementalUpdate(Resource):
        @ns.doc('incremental_update', description='从 arXiv 增量更新论文数据库')
        @ns.expect(incremental_update_model)
        def post(self):
            """增量更新数据库"""
            try:
                data = request.json or {}

                # Use config values as defaults if not provided in request
                arxiv_config = current_app.config['ARXIV_CONFIG']
                max_results = data.get('max_results') if data.get('max_results') is not None else arxiv_config.arxiv.max_results
                batch_size = data.get('batch_size') if data.get('batch_size') is not None else arxiv_config.arxiv.batch_size

                builder = current_app.config['BUILDER']
                stats = builder.incremental_update(
                    max_results=max_results,
                    batch_size=batch_size,
                    show_progress=False  # Don't show progress in API
                )

                return {
                    'status': 'success',
                    'message': f'Added {stats.get("new_papers_added", 0)} new papers',
                    'stats': stats
                }
            except Exception as e:
                api.abort(500, f'Update error: {str(e)}')

    # Add papers endpoint
    @ns.route('/add_papers')
    class AddPapers(Resource):
        @ns.doc('add_papers', description='从 JSON 文件添加论文')
        @ns.expect(add_papers_model, validate=True)
        def post(self):
            """从 JSON 添加论文"""
            try:
                data = request.json

                if not data or 'json_path' not in data:
                    api.abort(400, 'Missing json_path parameter')

                json_path = data.get('json_path')

                if not os.path.exists(json_path):
                    api.abort(404, f'File not found: {json_path}')

                builder = current_app.config['BUILDER']
                stats = builder.add_papers_from_json(json_path)

                return {
                    'status': 'success',
                    'message': f'Added {stats.get("papers_added", 0)} papers',
                    'stats': stats
                }
            except Exception as e:
                api.abort(500, f'Add papers error: {str(e)}')

    # Delete papers endpoint
    @ns.route('/papers/<string:paper_id>')
    @ns.param('paper_id', '论文 ID')
    class DeletePaper(Resource):
        @ns.doc('delete_paper', description='删除指定论文')
        def delete(self, paper_id):
            """删除论文"""
            try:
                builder = current_app.config['BUILDER']
                stats = builder.delete_papers([paper_id])

                return {
                    'status': 'success',
                    'message': f'Deleted paper {paper_id}',
                    'papers_deleted': stats.get('papers_deleted', 0)
                }
            except Exception as e:
                api.abort(500, f'Delete error: {str(e)}')
