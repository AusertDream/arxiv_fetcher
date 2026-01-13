"""ChromaDB client manager for vector database operations."""

import chromadb
from chromadb.utils import embedding_functions
from omegaconf import DictConfig
import os
from typing import List, Set, Dict, Optional
from tqdm import tqdm


class ChromaDBManager:
    """Manage ChromaDB operations including embedding and storage."""

    def __init__(self, config: DictConfig):
        """
        Initialize ChromaDB manager.

        Args:
            config: OmegaConf configuration object
        """
        self.config = config
        self.embedding_function = None
        self.client = None
        self.collection = None

        self._setup_embedding_model()
        self._setup_chromadb()

    def _setup_embedding_model(self):
        """Initialize embedding model with GPU configuration."""
        model_path = self.config.embedding.model_path
        device = self.config.embedding.device
        normalize = self.config.embedding.normalize

        print(f"Loading embedding model: {model_path}")
        print(f"Device: {device}")

        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_path,
            device=device,
            normalize_embeddings=normalize
        )

        # 检测并显示嵌入维度
        try:
            test_embedding = self.embedding_function(['test'])
            embedding_dim = len(test_embedding[0])
            print(f"✓ Embedding model loaded (dimension: {embedding_dim})")
        except Exception as e:
            print(f"✓ Embedding model loaded (dimension: unknown)")
            print(f"  Warning: Could not detect dimension - {e}")

    def _setup_chromadb(self):
        """Initialize ChromaDB client and collection."""
        db_path = self.config.database.path
        collection_name = self.config.database.collection_name

        # Create database directory if needed
        os.makedirs(db_path, exist_ok=True)
        print(f"Database path: {db_path}")

        # Initialize persistent client
        self.client = chromadb.PersistentClient(path=db_path)

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )

        print(f"✓ Collection '{collection_name}' ready")

    def add_papers(self, papers: List[Dict], show_progress: bool = True) -> int:
        """
        Add papers to the database with dual embedding (title + abstract).

        Args:
            papers: List of paper dictionaries with keys: id, title, abstract, authors, published, url
            show_progress: Whether to show progress bar

        Returns:
            Number of papers added
        """
        if not papers:
            return 0

        documents = []
        ids = []
        metadatas = []

        iterator = tqdm(papers, desc="Preparing documents") if show_progress else papers

        for paper in iterator:
            # Title document
            documents.append(paper['title'])
            ids.append(f"{paper['id']}_title")
            metadatas.append({
                'paper_id': paper['id'],
                'type': 'title',
                'full_title': paper['title'],
                'authors': ','.join(paper['authors']) if isinstance(paper['authors'], list) else paper['authors'],
                'published': paper['published'],
                'url': paper['url']
            })

            # Abstract document
            documents.append(paper['abstract'])
            ids.append(f"{paper['id']}_abstract")
            metadatas.append({
                'paper_id': paper['id'],
                'type': 'abstract',
                'full_title': paper['title'],
                'authors': ','.join(paper['authors']) if isinstance(paper['authors'], list) else paper['authors'],
                'published': paper['published'],
                'url': paper['url']
            })

        # Batch add to ChromaDB
        batch_size = self.config.embedding.batch_size
        total_batches = (len(documents) + batch_size - 1) // batch_size

        if show_progress:
            print(f"\nAdding {len(documents)} documents in {total_batches} batches...")

        iterator = tqdm(range(0, len(documents), batch_size), desc="Storing batches") if show_progress else range(0, len(documents), batch_size)

        for i in iterator:
            batch_docs = documents[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]

            self.collection.add(
                documents=batch_docs,
                ids=batch_ids,
                metadatas=batch_metas
            )

        return len(papers)

    def delete_papers(self, paper_ids: List[str]) -> int:
        """
        Delete papers from the database.

        Args:
            paper_ids: List of paper IDs to delete

        Returns:
            Number of papers deleted
        """
        if not paper_ids:
            return 0

        # Delete both title and abstract documents for each paper
        doc_ids = []
        for paper_id in paper_ids:
            doc_ids.append(f"{paper_id}_title")
            doc_ids.append(f"{paper_id}_abstract")

        try:
            self.collection.delete(ids=doc_ids)
            return len(paper_ids)
        except Exception as e:
            print(f"Error deleting papers: {e}")
            return 0

    def get_existing_paper_ids(self) -> Set[str]:
        """
        Get set of existing paper IDs in the database.

        Returns:
            Set of paper IDs
        """
        try:
            existing_data = self.collection.get()
            if existing_data and existing_data['metadatas']:
                return {meta['paper_id'] for meta in existing_data['metadatas']}
            return set()
        except Exception as e:
            print(f"Warning: Could not load existing IDs ({e})")
            return set()

    def clear_collection(self):
        """Clear all documents from the collection."""
        try:
            collection_name = self.config.database.collection_name
            self.client.delete_collection(name=collection_name)
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print("✓ Collection cleared")
        except Exception as e:
            print(f"Error clearing collection: {e}")

    def count_documents(self) -> int:
        """Get total number of documents in the collection."""
        return self.collection.count()

    def count_papers(self) -> int:
        """Get total number of papers (documents / 2)."""
        return self.collection.count() // 2

    def get_stats(self) -> Dict:
        """
        Get database statistics.

        Returns:
            Dictionary with statistics
        """
        count = self.collection.count()
        return {
            'total_documents': count,
            'total_papers': count // 2,
            'collection_name': self.config.database.collection_name,
            'database_path': self.config.database.path
        }

    def query(self, query_texts: List[str], n_results: int = 10) -> Dict:
        """
        Query the collection for similar documents.

        Args:
            query_texts: List of query strings
            n_results: Number of results to return

        Returns:
            Query results from ChromaDB
        """
        return self.collection.query(
            query_texts=query_texts,
            n_results=n_results
        )

    def query_with_filter(
        self,
        query_texts: List[str],
        n_results: int = 10,
        where: Optional[Dict] = None
    ) -> Dict:
        """
        Query the collection with metadata filter.

        Args:
            query_texts: List of query strings
            n_results: Number of results to return
            where: Metadata filter (e.g., {"type": "title"})

        Returns:
            Query results from ChromaDB
        """
        kwargs = {
            'query_texts': query_texts,
            'n_results': n_results
        }

        if where is not None:
            kwargs['where'] = where

        return self.collection.query(**kwargs)
