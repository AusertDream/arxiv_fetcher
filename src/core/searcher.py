"""RAG search engine with dual similarity scoring."""

from omegaconf import DictConfig
from typing import List, Dict

from ..database.chromadb_manager import ChromaDBManager


class ArxivSearcher:
    """Search arXiv papers using semantic similarity."""

    def __init__(self, config: DictConfig, db_manager: ChromaDBManager = None):
        """
        Initialize the searcher.

        Args:
            config: OmegaConf configuration object
            db_manager: Optional ChromaDB manager instance (creates new if not provided)
        """
        self.config = config
        self.db_manager = db_manager or ChromaDBManager(config)

    def search(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Search papers with dual similarity scoring using separate queries.

        Process:
        1. Query title documents separately (type='title')
        2. Query abstract documents separately (type='abstract')
        3. Merge results by paper_id and calculate combined scores
        4. Sort by final score and return top-K

        Args:
            query: Natural language search query
            top_k: Number of top results to return (default from config)

        Returns:
            List of paper dictionaries with scores
        """
        if top_k is None:
            top_k = self.config.search.default_top_k

        # Cap top_k at max_top_k
        top_k = min(top_k, self.config.search.max_top_k)

        # Query more than needed for better coverage
        query_size = top_k * 2

        # Query 1: Title documents only
        title_results = self.db_manager.query_with_filter(
            query_texts=[query],
            n_results=query_size,
            where={"type": "title"}
        )

        # Query 2: Abstract documents only
        abstract_results = self.db_manager.query_with_filter(
            query_texts=[query],
            n_results=query_size,
            where={"type": "abstract"}
        )

        # Collect all paper IDs and their scores
        papers_dict = {}

        # Process title results
        if title_results['ids'] and len(title_results['ids'][0]) > 0:
            for i, doc_id in enumerate(title_results['ids'][0]):
                paper_id = doc_id.rsplit('_', 1)[0]
                distance = title_results['distances'][0][i]
                similarity = 1 - distance

                if paper_id not in papers_dict:
                    metadata = title_results['metadatas'][0][i]
                    papers_dict[paper_id] = {
                        'paper_id': paper_id,
                        'title': metadata['full_title'],
                        'authors': metadata['authors'].split(','),
                        'published': metadata['published'],
                        'url': metadata['url'],
                        'title_similarity': similarity,
                        'abstract_similarity': 0.0
                    }
                else:
                    papers_dict[paper_id]['title_similarity'] = similarity

        # Process abstract results
        if abstract_results['ids'] and len(abstract_results['ids'][0]) > 0:
            for i, doc_id in enumerate(abstract_results['ids'][0]):
                paper_id = doc_id.rsplit('_', 1)[0]
                distance = abstract_results['distances'][0][i]
                similarity = 1 - distance

                if paper_id not in papers_dict:
                    metadata = abstract_results['metadatas'][0][i]
                    papers_dict[paper_id] = {
                        'paper_id': paper_id,
                        'title': metadata['full_title'],
                        'authors': metadata['authors'].split(','),
                        'published': metadata['published'],
                        'url': metadata['url'],
                        'title_similarity': 0.0,
                        'abstract_similarity': similarity
                    }
                else:
                    papers_dict[paper_id]['abstract_similarity'] = similarity

        # Calculate final scores with weights
        title_weight = self.config.search.title_weight
        abstract_weight = self.config.search.abstract_weight

        for paper in papers_dict.values():
            paper['score'] = (
                paper['title_similarity'] * title_weight +
                paper['abstract_similarity'] * abstract_weight
            )

        # Sort by score (descending) and return top-K
        # Note: We keep all papers, not filtering by requiring both title and abstract
        sorted_papers = sorted(
            papers_dict.values(),
            key=lambda x: x['score'],
            reverse=True
        )

        return sorted_papers[:top_k]

    def get_stats(self) -> Dict:
        """Get database statistics."""
        return self.db_manager.get_stats()
