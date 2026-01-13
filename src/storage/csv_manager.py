"""CSV manager for paper persistence."""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from omegaconf import DictConfig


class CSVManager:
    """Manage CSV storage for arXiv papers."""

    def __init__(self, config: DictConfig):
        """
        Initialize CSV manager.

        Args:
            config: OmegaConf configuration object
        """
        self.config = config
        self.csv_path = Path(config.storage.csv_path)
        self.init_filename = config.storage.init_filename
        self.daily_dir = config.storage.daily_dir

        # Create directories
        self.csv_path.mkdir(parents=True, exist_ok=True)
        self.daily_path = self.csv_path / self.daily_dir
        self.daily_path.mkdir(parents=True, exist_ok=True)

    def save_papers_to_csv(
        self,
        papers: List[Dict],
        mode: str = 'build',
        append: bool = False,
        show_progress: bool = True
    ) -> str:
        """
        Save papers to CSV file.

        Args:
            papers: List of paper dictionaries
            mode: 'build' or 'update' (determines filename)
            append: If True, append to existing file instead of overwriting
            show_progress: Whether to show progress messages

        Returns:
            Path to the created CSV file
        """
        if not papers:
            if show_progress:
                print("警告: 没有论文数据需要保存")
            return ""

        # Determine filename
        if mode == 'build':
            csv_file = self.csv_path / self.init_filename
        else:  # update mode
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_file = self.daily_path / f"{timestamp}.csv"

        # Determine write mode
        file_exists = csv_file.exists()
        write_mode = 'a' if (append and file_exists) else 'w'
        write_header = not (append and file_exists)

        # Write CSV with UTF-8 BOM encoding
        with open(csv_file, write_mode, encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['id', 'title', 'abstract', 'authors', 'published', 'url'],
                quoting=csv.QUOTE_MINIMAL
            )

            if write_header:
                writer.writeheader()

            for paper in papers:
                # Serialize authors list to semicolon-separated string
                authors_str = ';'.join(paper['authors']) if isinstance(paper['authors'], list) else paper['authors']

                row = {
                    'id': paper['id'],
                    'title': paper['title'],
                    'abstract': paper['abstract'],
                    'authors': authors_str,
                    'published': paper['published'],
                    'url': paper['url']
                }
                writer.writerow(row)

        if show_progress:
            action = "追加" if (append and file_exists) else "保存"
            print(f"✓ 已{action} {len(papers)} 篇论文到: {csv_file}")

        return str(csv_file)

    def load_papers_from_csv(self, csv_path: Optional[str] = None) -> List[Dict]:
        """
        Load papers from CSV file.

        Args:
            csv_path: Path to CSV file. If None, uses default init_data.csv

        Returns:
            List of paper dictionaries
        """
        if csv_path is None:
            csv_path = str(self.csv_path / self.init_filename)

        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV文件不存在: {csv_path}")

        papers = []
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Deserialize authors string to list
                authors_list = row['authors'].split(';') if row['authors'] else []

                paper = {
                    'id': row['id'],
                    'title': row['title'],
                    'abstract': row['abstract'],
                    'authors': authors_list,
                    'published': row['published'],
                    'url': row['url']
                }
                papers.append(paper)

        print(f"✓ 从 {csv_path} 加载了 {len(papers)} 篇论文")
        return papers

    def get_latest_daily_csv(self) -> Optional[str]:
        """
        Get the path to the latest daily CSV file.

        Returns:
            Path to latest CSV, or None if no files exist
        """
        csv_files = sorted(self.daily_path.glob('*.csv'), reverse=True)
        if csv_files:
            return str(csv_files[0])
        return None

    def list_daily_csvs(self) -> List[str]:
        """
        List all daily CSV files.

        Returns:
            List of CSV file paths, sorted by date (newest first)
        """
        csv_files = sorted(self.daily_path.glob('*.csv'), reverse=True)
        return [str(f) for f in csv_files]

    def get_csv_info(self, csv_path: str) -> Dict:
        """
        Get information about a CSV file.

        Args:
            csv_path: Path to CSV file

        Returns:
            Dictionary with file info (path, size, paper_count)
        """
        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV文件不存在: {csv_path}")

        # Count papers
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            paper_count = sum(1 for _ in reader)

        # Get file size
        file_size = csv_file.stat().st_size
        size_mb = file_size / (1024 * 1024)

        return {
            'path': str(csv_file),
            'filename': csv_file.name,
            'size_bytes': file_size,
            'size_mb': round(size_mb, 2),
            'paper_count': paper_count
        }

    def get_min_published_date(self, csv_path: Optional[str] = None) -> Optional[datetime]:
        """
        Get the minimum published date from a CSV file.
        Used for build mode resume to find the earliest paper.

        Args:
            csv_path: Path to CSV file. If None, uses init_data.csv

        Returns:
            Minimum published datetime, or None if file doesn't exist or is empty
        """
        if csv_path is None:
            csv_path = str(self.csv_path / self.init_filename)

        csv_file = Path(csv_path)
        if not csv_file.exists():
            return None

        min_date = None
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        date_str = row['published']
                        dt = datetime.strptime(date_str, '%Y-%m-%d')
                        if min_date is None or dt < min_date:
                            min_date = dt
                    except (ValueError, KeyError):
                        continue  # Skip rows with invalid dates
        except Exception as e:
            print(f"警告：读取CSV时出错: {e}")
            return None

        return min_date

    def get_max_published_date(self, csv_path: Optional[str] = None) -> Optional[datetime]:
        """
        Get the maximum published date from a CSV file.
        Used for update mode to find the latest paper.

        Args:
            csv_path: Path to CSV file. If None, uses init_data.csv

        Returns:
            Maximum published datetime, or None if file doesn't exist or is empty
        """
        if csv_path is None:
            csv_path = str(self.csv_path / self.init_filename)

        csv_file = Path(csv_path)
        if not csv_file.exists():
            return None

        max_date = None
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        date_str = row['published']
                        dt = datetime.strptime(date_str, '%Y-%m-%d')
                        if max_date is None or dt > max_date:
                            max_date = dt
                    except (ValueError, KeyError):
                        continue  # Skip rows with invalid dates
        except Exception as e:
            print(f"警告：读取CSV时出错: {e}")
            return None

        return max_date

    def get_max_published_date_from_daily(self) -> Optional[datetime]:
        """
        Get the maximum published date from all daily CSV files.
        Used for update mode to find the latest paper from all daily updates.

        Returns:
            Maximum published datetime across all daily files, or None if no daily files exist
        """
        csv_files = self.list_daily_csvs()
        if not csv_files:
            return None

        max_date = None
        for csv_file in csv_files:
            file_max = self.get_max_published_date(csv_file)
            if file_max and (max_date is None or file_max > max_date):
                max_date = file_max

        return max_date

