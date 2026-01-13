#!/usr/bin/env python3
"""Builder CLI tool for managing arXiv paper database."""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.config_loader import load_config
from src.core.builder import ArxivDatabaseBuilder


def cmd_update(builder, args, config):
    """Incremental update from arXiv."""
    print("Running incremental update...")

    # 使用mode参数决定执行哪个阶段
    mode = args.mode if hasattr(args, 'mode') and args.mode else 'all'

    # Use config values as defaults if not provided in CLI
    max_results = args.max_results if args.max_results is not None else config.arxiv.max_results
    batch_size = args.batch_size if args.batch_size is not None else config.arxiv.batch_size

    if mode == 'fetch':
        # 只爬取到CSV
        csv_path = builder.update_fetch(
            max_results=max_results,
            batch_size=batch_size,
            show_progress=True
        )
        print(f"\nUpdate fetch complete!")
        print(f"CSV saved to: {csv_path}")

    elif mode == 'embed':
        # 只从CSV嵌入
        csv_path = args.csv if hasattr(args, 'csv') and args.csv else None
        stats = builder.update_embed(
            csv_path=csv_path,
            show_progress=True
        )
        print("\nUpdate embed complete!")
        print(f"Papers added: {stats.get('papers_added', 0)}")
        print(f"Total papers in database: {stats.get('total_papers', 0)}")

    else:  # mode == 'all' or not specified
        # 完整流程：fetch + embed (与build保持一致，生成CSV)
        csv_path = builder.update_fetch(
            max_results=max_results,
            batch_size=batch_size,
            show_progress=True
        )

        # 如果没有新论文,跳过embed步骤
        if not csv_path:
            print("\nUpdate complete!")
            print("No new papers found.")
            stats = builder.get_stats()
            print(f"Total papers in database: {stats['total_papers']}")
        else:
            stats = builder.update_embed(
                csv_path=csv_path,
                show_progress=True
            )
            print("\nUpdate complete!")
            print(f"Papers added: {stats.get('papers_added', 0)}")
            print(f"Total papers in database: {stats['total_papers']}")


def cmd_build(builder, args, config):
    """Build database from scratch."""
    print("Building database from scratch...")

    # 使用mode参数决定执行哪个阶段
    mode = args.mode if hasattr(args, 'mode') and args.mode else 'all'

    # Use config values as defaults if not provided in CLI
    max_results = args.max_results if args.max_results is not None else config.arxiv.max_results
    batch_size = args.batch_size if args.batch_size is not None else config.arxiv.batch_size
    resume = not args.no_resume if hasattr(args, 'no_resume') else True  # 默认启用断点续爬

    if mode == 'fetch':
        # 只爬取到CSV
        csv_path = builder.build_fetch(
            max_results=max_results,
            batch_size=batch_size,
            show_progress=True,
            resume=resume  # 传递resume参数
        )
        print(f"\nBuild fetch complete!")
        print(f"CSV saved to: {csv_path}")

    elif mode == 'embed':
        # 只从CSV嵌入
        csv_path = args.csv if hasattr(args, 'csv') and args.csv else None
        stats = builder.build_embed(
            csv_path=csv_path,
            show_progress=True
        )
        print("\nBuild embed complete!")
        print(f"Papers added: {stats.get('papers_added', 0)}")
        print(f"Total papers in database: {stats.get('total_papers', 0)}")

    else:  # mode == 'all'
        # 完整流程：fetch + embed
        csv_path = builder.build_fetch(
            max_results=max_results,
            batch_size=batch_size,
            show_progress=True,
            resume=resume  # 传递resume参数
        )
        stats = builder.build_embed(
            csv_path=csv_path,
            show_progress=True
        )
        print("\nBuild complete!")
        print(f"Total papers in database: {stats.get('total_papers', 0)}")


def cmd_list_csv(builder, args):
    """List all daily CSV files."""
    csv_files = builder.csv_manager.list_daily_csvs()

    if not csv_files:
        print("No daily CSV files found.")
        return

    print("\nDaily CSV Files:")
    print("="*80)

    for csv_file in csv_files:
        try:
            info = builder.csv_manager.get_csv_info(csv_file)
            print(f"{info['filename']:30} | {info['paper_count']:5} papers | {info['size_mb']:6.2f} MB")
        except Exception as e:
            print(f"{csv_file}: Error - {e}")

    print("="*80)
    print(f"Total: {len(csv_files)} files")


def cmd_stats(builder, args):
    """Show database statistics."""
    stats = builder.get_stats()
    print("\nDatabase Statistics:")
    print("="*50)
    print(f"Total papers:     {stats['total_papers']}")
    print(f"Total documents:  {stats['total_documents']}")
    print(f"Collection:       {stats['collection_name']}")
    print(f"Database path:    {stats['database_path']}")
    print("="*50)


def cmd_clear(builder, args):
    """Clear the database."""
    confirm = input("WARNING: This will delete all papers. Continue? [y/N]: ")
    if confirm.lower() == 'y':
        builder.clear_database()
        print("Database cleared.")
    else:
        print("Operation cancelled.")


def cmd_add(builder, args):
    """Add papers from JSON file."""
    if not args.json:
        print("Error: --json parameter required")
        return 1

    print(f"Adding papers from {args.json}...")
    stats = builder.add_papers_from_json(args.json)
    print(f"\nAdded {stats['papers_added']} papers")
    print(f"Total papers in database: {stats['total_papers']}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='arXiv Database Builder CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build from scratch (complete workflow)
  python run_builder.py build --mode all --max-results -1

  # Build fetch only (stage 1)
  python run_builder.py build --mode fetch --max-results 1000

  # Build embed only (stage 2)
  python run_builder.py build --mode embed

  # Incremental update (complete workflow)
  python run_builder.py update --max-results 100

  # Update fetch only (stage 1)
  python run_builder.py update --mode fetch --max-results 50

  # Update embed only (stage 2)
  python run_builder.py update --mode embed
  python run_builder.py update --mode embed --csv daily/20260109_143025.csv

  # List daily CSV files
  python run_builder.py list-csv

  # Show statistics
  python run_builder.py stats

  # Clear database (WARNING: deletes all data)
  python run_builder.py clear

  # Add papers from JSON
  python run_builder.py add --json papers.json
        """
    )

    parser.add_argument('--config', default='config/default.yaml', help='Config file path')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Build command
    build_parser = subparsers.add_parser('build', help='Build database from scratch')
    build_parser.add_argument('--mode', choices=['fetch', 'embed', 'all'], default='all',
                             help='Build mode: fetch (爬取到CSV), embed (从CSV嵌入), all (完整流程)')
    build_parser.add_argument('--max-results', type=int, default=None, help='Max papers to fetch (default -1: unlimited)')
    build_parser.add_argument('--batch-size', type=int, default=None, help='Batch size (default from config)')
    build_parser.add_argument('--csv', type=str, default=None, help='CSV file path for embed mode (optional)')
    build_parser.add_argument('--no-resume', action='store_true', help='禁用断点续爬，重新开始爬取')

    # Update command
    update_parser = subparsers.add_parser('update', help='Incremental update from arXiv')
    update_parser.add_argument('--mode', choices=['fetch', 'embed', 'all'], default='all',
                              help='Update mode: fetch (爬取到CSV), embed (从CSV嵌入), all (完整流程)')
    update_parser.add_argument('--max-results', type=int, default=None, help='Max papers to fetch (default from config)')
    update_parser.add_argument('--batch-size', type=int, default=None, help='Batch size (default from config)')
    update_parser.add_argument('--csv', type=str, default=None, help='CSV file path for embed mode (optional)')

    # List CSV command
    subparsers.add_parser('list-csv', help='List all daily CSV files')

    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')

    # Clear command
    subparsers.add_parser('clear', help='Clear database (WARNING: deletes all data)')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add papers from JSON file')
    add_parser.add_argument('--json', required=True, help='Path to JSON file')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        # Load config
        config = load_config(args.config)

        # Initialize builder
        print("Initializing builder...")
        builder = ArxivDatabaseBuilder(config)

        # Execute command
        commands = {
            'build': lambda b, a: cmd_build(b, a, config),
            'update': lambda b, a: cmd_update(b, a, config),
            'list-csv': cmd_list_csv,
            'stats': cmd_stats,
            'clear': cmd_clear,
            'add': cmd_add
        }

        return commands[args.command](builder, args) or 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
