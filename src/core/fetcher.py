"""arXiv paper fetcher with incremental crawling support."""

import arxiv
from omegaconf import DictConfig
from datetime import datetime, timedelta
from typing import List, Set, Optional, Callable, Dict
from tqdm import tqdm
import time


class ArxivFetcher:
    """Fetch papers from arXiv with filtering and incremental support."""

    def __init__(self, config: DictConfig):
        """
        Initialize fetcher.

        Args:
            config: OmegaConf configuration object
        """
        self.config = config

    def calculate_date_range(self) -> Optional[datetime]:
        """
        Calculate start date based on config.

        Returns:
            Start date for filtering, or None if disabled
        """
        time_config = self.config.arxiv.time_filter

        if not time_config.get('enabled', False):
            return None

        mode = time_config.mode
        value = time_config.value
        now = datetime.now()

        if mode == 'days':
            return now - timedelta(days=value)
        elif mode == 'weeks':
            return now - timedelta(weeks=value)
        elif mode == 'months':
            return now - timedelta(days=value * 30)
        elif mode == 'years':
            return now - timedelta(days=value * 365)
        else:
            print(f"Warning: Unknown time filter mode '{mode}'. Filtering disabled.")
            return None

    def _format_arxiv_date(self, dt: datetime, end_of_day: bool = False) -> str:
        """
        Format datetime for arXiv API query (YYYYMMDDHHMMSS).

        Args:
            dt: Datetime object
            end_of_day: If True, use 235959, otherwise 000000

        Returns:
            Formatted string (YYYYMMDDHHMMSS)
        """
        if end_of_day:
            return dt.strftime('%Y%m%d') + '235959'
        else:
            return dt.strftime('%Y%m%d%H%M%S')

    def _build_query_with_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """
        Build arXiv query with date range.

        Args:
            start_date: Start of date range
            end_date: End of date range (precise timestamp)

        Returns:
            Query string with submittedDate filter
        """
        base_query = ("cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV OR cat:cs.NE OR "
                      "cat:cs.RO OR cat:cs.MA OR cat:cs.IR OR cat:cs.HC OR cat:stat.ML")
        start_str = self._format_arxiv_date(start_date, end_of_day=False)
        end_str = self._format_arxiv_date(end_date, end_of_day=False)  # Use precise timestamp
        return f"({base_query}) AND submittedDate:[{start_str} TO {end_str}]"

    def _extract_earliest_date(self, papers: List) -> Optional[datetime]:
        """
        Extract the earliest published date from a list of papers.

        Args:
            papers: List of arxiv.Result objects

        Returns:
            Earliest published datetime, or None if empty
        """
        if not papers:
            return None
        dates = [p.published.replace(tzinfo=None) for p in papers]
        return min(dates)

    def _should_stop_batching(
        self,
        earliest_date: Optional[datetime],
        start_date: datetime,
        threshold_days: float = 1.0
    ) -> bool:
        """
        Determine if batching should stop.

        Args:
            earliest_date: Earliest date in current batch
            start_date: Target start date
            threshold_days: Stop threshold in days

        Returns:
            True if should stop, False otherwise
        """
        if earliest_date is None:
            return True  # No papers in batch

        # Check if earliest_date is close to start_date
        time_diff_days = (earliest_date - start_date).total_seconds() / 86400
        return time_diff_days <= threshold_days  # Reached target date range

    def fetch(
        self,
        max_results: Optional[int] = None,
        existing_ids: Optional[Set[str]] = None,
        batch_callback: Optional[Callable[[List[Dict]], None]] = None,
        batch_size: Optional[int] = None,
        show_progress: bool = True,
        custom_start_date: Optional[datetime] = None,
        custom_end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Fetch papers from arXiv with incremental support.

        Args:
            max_results: Maximum number of papers to fetch
            existing_ids: Set of existing paper IDs to skip (for deduplication)
            batch_callback: Callback function called for each batch of papers
            batch_size: Number of papers per batch (default from config)
            show_progress: Whether to show progress bar
            custom_start_date: Custom start date (overrides config). Papers FROM this date
            custom_end_date: Custom end date (overrides config). Papers TO this date

        Returns:
            List of paper dictionaries
        """
        if max_results is None:
            max_results = self.config.arxiv.max_results

        # Handle -1 as unlimited
        unlimited = False
        if max_results == -1:
            unlimited = True
            max_results = 50000  # Use a large number for arXiv API
            if show_progress:
                print("Note: max_results=-1 means unlimited, will fetch all matching papers")

        if batch_size is None:
            batch_size = self.config.arxiv.batch_size

        # Get fetch interval (delay between batches)
        fetch_interval = self.config.arxiv.get('fetch_interval', 0)
        if fetch_interval < 0:
            fetch_interval = 0  # Ensure non-negative

        if existing_ids is None:
            existing_ids = set()

        # Calculate date range for filtering
        if custom_start_date is not None:
            start_date = custom_start_date
        else:
            start_date = self.calculate_date_range()
            if start_date is None:
                # If time filter disabled, use 2 days ago as default
                start_date = datetime.now() - timedelta(days=2)

        if custom_end_date is not None:
            current_end_date = custom_end_date
        else:
            current_end_date = datetime.now()

        batch_threshold_days = self.config.arxiv.get('batch_threshold_days', 1.0)

        if show_progress:
            print("="*70)
            print("Fetching arXiv papers (BATCH MODE)")
            print("="*70)
            print(f"Categories: cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, cs.RO, cs.MA, cs.IR, cs.HC, stat.ML")
            print(f"Time window: {start_date.strftime('%Y-%m-%d')} to {current_end_date.strftime('%Y-%m-%d')}")
            if unlimited:
                print(f"Max results: UNLIMITED (all matching papers)")
            else:
                print(f"Max results: {max_results}")
            print(f"Batch size: {batch_size}")
            if fetch_interval > 0:
                print(f"Fetch interval: {fetch_interval}s (delay between batches)")
            print(f"Existing papers to skip: {len(existing_ids)}")
            print(f"\n⚠️  Note: Batches iterate from newest to oldest")
            print(f"      First batch will contain papers near {current_end_date.strftime('%Y-%m-%d')}")
            print(f"      Last batch will reach {start_date.strftime('%Y-%m-%d')}")
            print("="*70 + "\n")

        client = arxiv.Client()

        # Statistics
        batch = []
        all_papers = []
        total_fetched = 0
        skipped = 0
        batch_num = 0
        consecutive_empty_batches = 0  # Track consecutive batches with no new papers
        max_consecutive_empty = 5  # Stop after 5 consecutive empty batches

        # Progress bar
        if show_progress:
            if unlimited:
                pbar = tqdm(desc="Fetching (unlimited)", unit="paper",
                           bar_format='{desc}: {n_fmt} papers | {rate_fmt} | {elapsed}')
            else:
                pbar = tqdm(total=max_results, desc="Fetching papers", unit="paper")
        else:
            pbar = None

        try:
            # Batch loop with time-based iteration
            while True:
                batch_num += 1
                papers_before_batch = len(all_papers)  # Record count before this batch

                # Build query with date range for this batch
                query = self._build_query_with_date_range(start_date, current_end_date)

                # Create search for this batch
                search = arxiv.Search(
                    query=query,
                    max_results=batch_size,
                    sort_by=arxiv.SortCriterion.SubmittedDate,
                    sort_order=arxiv.SortOrder.Descending
                )

                # Fetch papers in this batch with retry logic
                batch_start_time = time.time()

                # Retry configuration
                max_retries = getattr(self.config.arxiv, 'retry_max_attempts', 3)
                base_sleep = getattr(self.config.arxiv, 'retry_base_sleep', 5.0)
                retry_count = 0
                batch_success = False

                while retry_count <= max_retries:
                    # 关键修复：每次重试前清空数据
                    batch_raw_papers = []

                    try:
                        for paper in client.results(search):
                            batch_raw_papers.append(paper)

                            # Extract paper ID
                            paper_id = paper.entry_id.split("/")[-1]

                            # Skip if already exists
                            if paper_id in existing_ids:
                                skipped += 1
                                continue

                            # Format paper data
                            paper_dict = {
                                'id': paper_id,
                                'title': paper.title,
                                'authors': [author.name for author in paper.authors],
                                'abstract': paper.summary.replace("\n", " ").strip(),
                                'published': paper.published.strftime("%Y-%m-%d"),
                                'url': paper.entry_id
                            }

                            batch.append(paper_dict)
                            all_papers.append(paper_dict)

                            # Add to existing_ids to prevent duplicates within this fetch session
                            existing_ids.add(paper_id)

                            # Process batch if size reached
                            if len(batch) >= batch_size:
                                if batch_callback:
                                    batch_callback(batch)
                                batch = []

                            # Update progress bar
                            if pbar is not None:
                                pbar.update(1)
                                if not unlimited:
                                    pbar.set_postfix({
                                        'batch': batch_num,
                                        'new': len(all_papers),
                                        'skipped': skipped
                                    })
                                else:
                                    pbar.set_postfix({
                                        'batch': batch_num,
                                        'new': len(all_papers),
                                        'skipped': skipped
                                    })

                            # Check if we've reached max_results (for limited mode)
                            if not unlimited and len(all_papers) >= max_results:
                                break

                        # Batch completed successfully
                        batch_success = True
                        break  # Exit retry loop

                    except Exception as e:
                        error_msg = str(e)
                        is_rate_limit = '429' in error_msg or 'rate limit' in error_msg.lower()

                        if is_rate_limit and retry_count < max_retries:
                            retry_count += 1
                            sleep_time = base_sleep * (2 ** (retry_count - 1))  # Exponential backoff: 5s, 10s, 20s
                            if show_progress:
                                print(f"\n⚠️  遇到速率限制 (HTTP 429)")
                                print(f"   重试 {retry_count}/{max_retries}，等待 {sleep_time:.1f}秒...\n")
                            time.sleep(sleep_time)
                        else:
                            # Non-rate-limit error or max retries reached
                            if show_progress:
                                print(f"\nWarning: Error in batch {batch_num}: {e}")
                                if retry_count >= max_retries:
                                    print(f"已达最大重试次数 ({max_retries})，跳过此批次\n")
                                else:
                                    print("Continuing with next batch...\n")
                            break  # Exit retry loop, continue to next batch

                # 在重试循环外部统计
                total_fetched += len(batch_raw_papers)

                # Count new papers in this batch
                papers_in_this_batch = len(all_papers) - papers_before_batch

                # Check if batch failed after all retries
                if not batch_success and len(batch_raw_papers) == 0:
                    if show_progress:
                        print("批次重试后仍无数据，停止爬取")
                    break  # Exit main batch loop

                # Extract earliest date from this batch
                earliest_date = self._extract_earliest_date(batch_raw_papers)

                if show_progress:
                    batch_time = time.time() - batch_start_time
                    earliest_str = earliest_date.strftime('%Y-%m-%d %H:%M') if earliest_date else 'N/A'
                    print(f"Batch {batch_num}: {len(batch_raw_papers)} papers fetched, {papers_in_this_batch} new, earliest: {earliest_str} ({batch_time:.1f}s)")

                # Check stopping conditions
                if earliest_date is None:
                    if show_progress:
                        print(f"No more papers returned. Stopping.\n")
                    break

                if self._should_stop_batching(earliest_date, start_date, batch_threshold_days):
                    if show_progress:
                        print(f"Reached target date range (earliest: {earliest_date.strftime('%Y-%m-%d')}). Stopping.\n")
                    break

                # Check if we've reached max_results (for limited mode)
                if not unlimited and len(all_papers) >= max_results:
                    if show_progress:
                        print(f"Reached max_results limit ({max_results}). Stopping.\n")
                    break

                # Update end_date for next batch (1 second before earliest date)
                current_end_date = earliest_date - timedelta(seconds=1)

                # If no new papers were added in this batch (all skipped due to duplicates),
                # force time to move backward by 1 minute to escape the congested time window
                if papers_in_this_batch == 0:
                    consecutive_empty_batches += 1
                    if show_progress:
                        print(f"⚠️  No new papers in this batch (all duplicates). Consecutive empty: {consecutive_empty_batches}/{max_consecutive_empty}. Forcing time jump backward by 1 minute.")
                    current_end_date = earliest_date - timedelta(minutes=1)

                    # If too many consecutive empty batches, stop crawling
                    if consecutive_empty_batches >= max_consecutive_empty:
                        if show_progress:
                            print(f"\n⛔ Reached {max_consecutive_empty} consecutive empty batches. Stopping crawl to avoid infinite loop.")
                            print("This likely indicates arXiv API is returning a limited set of papers at this timestamp.")
                        break
                else:
                    consecutive_empty_batches = 0  # Reset counter when we get new papers

                # Apply fetch interval delay
                if fetch_interval > 0:
                    if show_progress:
                        print(f"Sleeping {fetch_interval}s...\n")
                    if pbar is not None:
                        pbar.set_postfix_str(f"sleeping {fetch_interval}s...")
                    time.sleep(fetch_interval)

        finally:
            if pbar is not None:
                pbar.close()

        # Process remaining batch
        if batch and batch_callback:
            batch_callback(batch)

        # Print final statistics
        if show_progress:
            print("\n" + "="*70)
            print("Fetch complete")
            print("="*70)
            print(f"Total fetched:       {total_fetched}")
            print(f"Skipped (existing):  {skipped}")
            print(f"New papers:          {len(all_papers)}")
            print("="*70)

        return all_papers

    def fetch_simple(self, max_results: int = 100) -> List[Dict]:
        """
        Simple fetch without incremental support (for testing).

        Args:
            max_results: Maximum number of papers

        Returns:
            List of paper dictionaries
        """
        return self.fetch(
            max_results=max_results,
            existing_ids=set(),
            batch_callback=None,
            show_progress=True
        )
