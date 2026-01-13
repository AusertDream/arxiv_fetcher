"""Database builder for arXiv RAG system."""

from omegaconf import DictConfig
from typing import List, Dict, Optional
from datetime import timedelta
import json

from ..database.chromadb_manager import ChromaDBManager
from ..storage.csv_manager import CSVManager
from .fetcher import ArxivFetcher


class ArxivDatabaseBuilder:
    """Build and manage the arXiv paper database."""

    def __init__(self, config: DictConfig):
        """
        Initialize the builder.

        Args:
            config: OmegaConf configuration object
        """
        self.config = config
        self.db_manager = ChromaDBManager(config)
        self.csv_manager = CSVManager(config)
        self.fetcher = ArxivFetcher(config)
        print("✓ Builder initialized\n")

    def incremental_update(
        self,
        max_results: int = 100,
        batch_size: Optional[int] = None,
        show_progress: bool = True
    ) -> Dict:
        """
        Incrementally update the database with new papers from arXiv.

        This is the primary method for adding papers. It automatically:
        - Loads existing paper IDs to avoid duplicates
        - Fetches new papers from arXiv
        - Stores them in batches to ChromaDB

        Args:
            max_results: Maximum number of papers to fetch
            batch_size: Papers per batch (default from config)
            show_progress: Whether to show progress

        Returns:
            Dictionary with statistics
        """
        print("Starting incremental update...")

        # 智能确定起始点(与update_fetch保持一致)
        custom_start_date = None

        # 优先检查daily CSV
        daily_max_date = self.csv_manager.get_max_published_date_from_daily()
        if daily_max_date:
            custom_start_date = daily_max_date + timedelta(seconds=1)
            if show_progress:
                print(f"✓ 从daily CSV检测到最新日期: {daily_max_date.strftime('%Y-%m-%d')}")
                print(f"  将爬取 {custom_start_date.strftime('%Y-%m-%d')} 到当前时间的新论文\n")
        else:
            # 检查init_data.csv
            init_max_date = self.csv_manager.get_max_published_date()
            if init_max_date:
                custom_start_date = init_max_date + timedelta(seconds=1)
                if show_progress:
                    print(f"✓ 从init_data.csv检测到最新日期: {init_max_date.strftime('%Y-%m-%d')}")
                    print(f"  将爬取 {custom_start_date.strftime('%Y-%m-%d')} 到当前时间的新论文\n")
            else:
                print("\n❌ 错误: 未找到init_data.csv和daily CSV")
                print("   请先执行以下命令初始化数据库:")
                print("   python scripts/run_builder.py build --mode all\n")
                import sys
                sys.exit(1)

        # Load existing IDs for deduplication
        existing_ids = self.db_manager.get_existing_paper_ids()

        if show_progress:
            print(f"Existing papers in database: {len(existing_ids)}\n")

        # Define batch callback to store papers as they're fetched
        stored_count = 0

        def batch_callback(batch: List[Dict]):
            nonlocal stored_count
            count = self.db_manager.add_papers(batch, show_progress=False)
            stored_count += count

        # Fetch papers with incremental storage
        papers = self.fetcher.fetch(
            max_results=max_results,
            existing_ids=existing_ids,
            batch_callback=batch_callback,
            batch_size=batch_size,
            show_progress=show_progress,
            custom_start_date=custom_start_date  # 传递智能起始点
        )

        # Get final stats
        stats = self.db_manager.get_stats()
        stats['new_papers_added'] = len(papers)

        if show_progress:
            print(f"\n✓ Incremental update complete")
            print(f"  New papers added: {len(papers)}")
            print(f"  Total papers in DB: {stats['total_papers']}")

        return stats

    def build_fetch(
        self,
        max_results: int = -1,
        batch_size: Optional[int] = None,
        show_progress: bool = True,
        resume: bool = True
    ) -> str:
        """
        Build模式：爬取论文并保存到init_data.csv（不嵌入）。

        支持断点续爬：如果init_data.csv存在且resume=True，
        则从CSV中最小的published日期继续往更早时间爬取。

        Args:
            max_results: 最大论文数量（-1表示全部）
            batch_size: 批次大小
            show_progress: 是否显示进度
            resume: 是否启用断点续爬（默认True）

        Returns:
            CSV文件路径
        """
        print("="*70)
        print("Build模式 - 阶段1: 爬取论文到CSV")
        print("="*70)

        # 检查是否需要断点续爬
        custom_end_date = None
        append_mode = False

        if resume:
            min_date = self.csv_manager.get_min_published_date()
            if min_date:
                custom_end_date = min_date - timedelta(seconds=1)
                append_mode = True
                print(f"✓ 检测到现有数据，最早日期: {min_date.strftime('%Y-%m-%d')}")
                print(f"  将从该日期继续往更早时间爬取")
                print(f"  模式: 追加到init_data.csv\n")
            else:
                print("未检测到现有数据，将执行完整爬取\n")
        else:
            print("注意: 断点续爬已禁用，将重新爬取全部论文\n")

        # Build模式不检查existing_ids，爬取全量数据
        all_papers = []

        def batch_callback(batch: List[Dict]):
            nonlocal all_papers
            all_papers.extend(batch)

        # 爬取论文
        papers = self.fetcher.fetch(
            max_results=max_results,
            existing_ids=set(),  # 不检查已存在的
            batch_callback=batch_callback,
            batch_size=batch_size,
            show_progress=show_progress,
            custom_end_date=custom_end_date  # 传递断点续爬的结束时间
        )

        # 保存到CSV（使用追加模式）
        csv_path = self.csv_manager.save_papers_to_csv(
            papers,
            mode='build',
            append=append_mode,  # 断点续爬时使用追加模式
            show_progress=True
        )

        print(f"\n✓ Build fetch完成")
        print(f"  本次爬取: {len(papers)} 篇")
        print(f"  CSV文件: {csv_path}")
        print("="*70)

        return csv_path

    def build_embed(
        self,
        csv_path: Optional[str] = None,
        show_progress: bool = True
    ) -> Dict:
        """
        Build模式：从CSV加载论文并嵌入到ChromaDB。

        这是初始化数据库的第二阶段，从CSV读取数据并嵌入到向量数据库。

        Args:
            csv_path: CSV文件路径（None则使用默认的init_data.csv）
            show_progress: 是否显示进度

        Returns:
            统计信息字典
        """
        print("="*70)
        print("Build模式 - 阶段2: 从CSV嵌入到ChromaDB")
        print("="*70)

        # 从CSV加载论文
        papers = self.csv_manager.load_papers_from_csv(csv_path)

        if not papers:
            print("警告: CSV中没有论文数据")
            return {'papers_added': 0}

        # 去重（与ChromaDB中已有的比较）
        existing_ids = self.db_manager.get_existing_paper_ids()
        new_papers = [p for p in papers if p['id'] not in existing_ids]

        if len(new_papers) < len(papers):
            print(f"发现 {len(papers) - len(new_papers)} 篇重复论文，将跳过")

        if not new_papers:
            print("所有论文都已存在，无需嵌入")
            return {'papers_added': 0}

        print(f"开始嵌入 {len(new_papers)} 篇论文...")

        # 嵌入到ChromaDB
        count = self.db_manager.add_papers(new_papers, show_progress=show_progress)

        stats = self.db_manager.get_stats()
        stats['papers_added'] = count

        print(f"\n✓ Build embed完成")
        print(f"  新增论文: {count}")
        print(f"  总论文数: {stats['total_papers']}")
        print("="*70)

        return stats

    def update_fetch(
        self,
        max_results: int = 100,
        batch_size: Optional[int] = None,
        show_progress: bool = True
    ) -> str:
        """
        Update模式：增量爬取新论文并保存到daily CSV（不嵌入）。

        智能起始点：
        - 如果存在daily/*.csv，从其中最大published日期开始
        - 否则从init_data.csv中最大published日期开始
        - 爬取到当前日期

        Args:
            max_results: 最大论文数量
            batch_size: 批次大小
            show_progress: 是否显示进度

        Returns:
            CSV文件路径
        """
        print("="*70)
        print("Update模式 - 阶段1: 增量爬取到CSV")
        print("="*70)

        # 智能确定起始点
        custom_start_date = None

        # 优先检查daily CSV
        daily_max_date = self.csv_manager.get_max_published_date_from_daily()
        if daily_max_date:
            custom_start_date = daily_max_date + timedelta(seconds=1)
            print(f"✓ 从daily CSV检测到最新日期: {daily_max_date.strftime('%Y-%m-%d')}")
            print(f"  将爬取 {custom_start_date.strftime('%Y-%m-%d')} 到当前时间的新论文")
            print(f"  注意: 批次从当前时间往回爬,最终到达 {custom_start_date.strftime('%Y-%m-%d')}\n")
        else:
            # 检查init_data.csv
            init_max_date = self.csv_manager.get_max_published_date()
            if init_max_date:
                custom_start_date = init_max_date + timedelta(seconds=1)
                print(f"✓ 从init_data.csv检测到最新日期: {init_max_date.strftime('%Y-%m-%d')}")
                print(f"  将爬取 {custom_start_date.strftime('%Y-%m-%d')} 到当前时间的新论文")
                print(f"  注意: 批次从当前时间往回爬,最终到达 {custom_start_date.strftime('%Y-%m-%d')}\n")
            else:
                print("\n❌ 错误: 未找到init_data.csv和daily CSV")
                print("   请先执行以下命令初始化数据库:")
                print("   python scripts/run_builder.py build --mode all\n")
                import sys
                sys.exit(1)

        # 加载现有ID用于去重
        existing_ids = self.db_manager.get_existing_paper_ids()

        if show_progress:
            print(f"数据库中现有论文: {len(existing_ids)}\n")

        # 爬取新论文
        all_papers = []

        def batch_callback(batch: List[Dict]):
            nonlocal all_papers
            all_papers.extend(batch)

        papers = self.fetcher.fetch(
            max_results=max_results,
            existing_ids=existing_ids,
            batch_callback=batch_callback,
            batch_size=batch_size,
            show_progress=show_progress,
            custom_start_date=custom_start_date  # 智能起始点
        )

        # 保存到daily CSV
        csv_path = self.csv_manager.save_papers_to_csv(
            papers,
            mode='update',
            show_progress=True
        )

        print(f"\n✓ Update fetch完成")
        print(f"  新论文数: {len(papers)}")
        if csv_path:
            print(f"  CSV文件: {csv_path}")
        print("="*70)

        return csv_path

    def update_embed(
        self,
        csv_path: Optional[str] = None,
        show_progress: bool = True
    ) -> Dict:
        """
        Update模式：从CSV加载论文并嵌入到ChromaDB。

        这是增量更新的第二阶段，从daily CSV读取数据并嵌入到向量数据库。

        Args:
            csv_path: CSV文件路径（None则使用最新的daily CSV）
            show_progress: 是否显示进度

        Returns:
            统计信息字典
        """
        print("="*70)
        print("Update模式 - 阶段2: 从CSV嵌入到ChromaDB")
        print("="*70)

        # 如果未指定CSV，使用最新的daily CSV
        if csv_path is None:
            csv_path = self.csv_manager.get_latest_daily_csv()
            if csv_path is None:
                print("错误: 未找到daily CSV文件")
                return {'papers_added': 0}
            print(f"使用最新的CSV: {csv_path}\n")

        # 从CSV加载论文
        papers = self.csv_manager.load_papers_from_csv(csv_path)

        if not papers:
            print("警告: CSV中没有论文数据")
            return {'papers_added': 0}

        # 再次去重（防止重复运行embed）
        existing_ids = self.db_manager.get_existing_paper_ids()
        new_papers = [p for p in papers if p['id'] not in existing_ids]

        if len(new_papers) < len(papers):
            print(f"发现 {len(papers) - len(new_papers)} 篇重复论文，将跳过")

        if not new_papers:
            print("所有论文都已存在，无需嵌入")
            return {'papers_added': 0}

        print(f"开始嵌入 {len(new_papers)} 篇论文...")

        # 嵌入到ChromaDB
        count = self.db_manager.add_papers(new_papers, show_progress=show_progress)

        stats = self.db_manager.get_stats()
        stats['papers_added'] = count

        print(f"\n✓ Update embed完成")
        print(f"  新增论文: {count}")
        print(f"  总论文数: {stats['total_papers']}")
        print("="*70)

        return stats

    def add_papers(self, papers: List[Dict]) -> Dict:
        """
        Add papers from a list.

        Args:
            papers: List of paper dictionaries

        Returns:
            Dictionary with statistics
        """
        print(f"Adding {len(papers)} papers to database...")

        count = self.db_manager.add_papers(papers, show_progress=True)

        stats = self.db_manager.get_stats()
        stats['papers_added'] = count

        print(f"✓ Added {count} papers")

        return stats

    def add_papers_from_json(self, json_path: str) -> Dict:
        """
        Add papers from a JSON file.

        Args:
            json_path: Path to JSON file with papers

        Returns:
            Dictionary with statistics
        """
        print(f"Loading papers from {json_path}...")

        with open(json_path, 'r', encoding='utf-8') as f:
            papers = json.load(f)

        return self.add_papers(papers)

    def delete_papers(self, paper_ids: List[str]) -> Dict:
        """
        Delete papers from the database.

        Args:
            paper_ids: List of paper IDs to delete

        Returns:
            Dictionary with statistics
        """
        print(f"Deleting {len(paper_ids)} papers...")

        count = self.db_manager.delete_papers(paper_ids)

        stats = self.db_manager.get_stats()
        stats['papers_deleted'] = count

        print(f"✓ Deleted {count} papers")

        return stats

    def clear_database(self):
        """Clear all papers from the database."""
        print("Clearing database...")
        self.db_manager.clear_collection()
        print("✓ Database cleared")

    def get_stats(self) -> Dict:
        """
        Get database statistics.

        Returns:
            Dictionary with statistics
        """
        return self.db_manager.get_stats()

    def rebuild_from_json(self, json_path: str, clear_first: bool = True) -> Dict:
        """
        Rebuild database from a JSON file.

        Args:
            json_path: Path to JSON file
            clear_first: Whether to clear existing data first

        Returns:
            Dictionary with statistics
        """
        if clear_first:
            self.clear_database()

        return self.add_papers_from_json(json_path)
