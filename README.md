# arXiv Fetcher

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)

[English](README_EN.md) | 简体中文

arXiv AI/LLM 论文智能检索系统 - 自动获取、存储和搜索人工智能领域的最新学术论文。通过arxiv官方python api进行论文数据的获取，通过chromadb存储摘要和标题的向量数据，通过chromadb query接口进行相似度的检索。从而从零开始实现基于相似度的论文检索功能。

## 目录

- [功能特性](#功能特性)
- [数据下载](#数据下载)
- [快速开始](#快速开始)
- [服务管理](#服务管理)
- [API使用示例](#api-使用示例)
- [Builder CLI工具](#builder-cli-工具)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [系统架构](#系统架构)
- [目录结构](#目录结构)
- [技术栈](#技术栈)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [更新日志](#更新日志)

## 功能特性

- **CSV持久化层** - 爬取和嵌入分离，支持断点续传和数据备份
- **全覆盖AI论文检索** - 覆盖10个AI相关类别，无关键词过滤
- **分阶段执行** - build/update模式支持fetch和embed独立执行
- **增量式论文爬取** - 自动去重，只爬取新论文到CSV
- **向量数据库存储** - 使用 ChromaDB 和 bge-m3 嵌入模型（1024维）
- **智能语义搜索** - 双重相似度评分（标题 + 摘要）提高搜索准确度
- **RESTful API** - 完整的 Swagger/OpenAPI 交互式文档
- **灵活的数据管理** - Shell脚本和CLI工具支持多种操作模式

## 数据下载

本项目提供已预处理的214,100篇AI论文数据，可直接下载使用，无需重新爬取。（数据量大概是21w，实际可能有略微差异。）

### 数据集信息
- **论文数量**: 214,100篇
- **时间范围**: 2024年1月 - 2026年1月
- **覆盖领域**: cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, cs.RO, cs.MA, cs.IR, cs.HC, stat.ML（10个AI相关类别）
- **文件大小**: 309 MB (CSV格式)
- **字段**: ID、标题、摘要、作者、发布日期、URL

### 下载地址
- **ModelScope**: [arxiv-ai-papers](https://modelscope.cn/datasets/ausertdream/arxiv-ai-papers)

### 使用下载的数据

下载数据后，将CSV文件放置到 `data/init_data.csv`，然后执行：

```bash
# 从CSV构建向量数据库
python scripts/run_builder.py build --mode embed
```

详细说明见 [DATASET.md](DATASET.md)

## 快速开始

### 1. 安装依赖

```bash
conda activate <your_env>  # 替换为你的conda环境名
cd /path/to/arxiv_fetcher   # 替换为你的项目路径
pip install -r requirements.txt
```

### 2. 配置

编辑 `config/default.yaml` 根据需要调整配置（通常使用默认值即可）。

关键配置项：
- `database.path` - ChromaDB存储路径
- `storage.csv_path` - CSV文件存储路径
- `embedding.device` - GPU 设备（如 cuda:3）
- `arxiv.max_results` - 最大爬取数量
- `api.port` - API 服务端口

### 3. 初始构建数据库

**方式一：一步完成**（推荐）
```bash
# 完整流程：爬取 → CSV → 嵌入 → ChromaDB
python scripts/run_builder.py build --mode all --max-results 1000
# 或使用Shell脚本
./shell/arxiv_service.sh build all
```

**方式二：分步执行**（适合调试或大规模数据）
```bash
# 步骤1：爬取所有论文到CSV（可能需要数小时）
python scripts/run_builder.py build --mode fetch --max-results -1

# 步骤2：从CSV嵌入到ChromaDB（GPU加速，较快）
python scripts/run_builder.py build --mode embed
```

### 4. 启动 API 服务

```bash
./shell/arxiv_service.sh start
```

### 5. 访问 Swagger 文档

打开浏览器访问：http://localhost:5001/docs

在 Swagger UI 中可以直接测试所有 API 端点。

## 服务管理

使用统一的 Shell 脚本管理服务和数据：

### API 服务管理

```bash
# 启动服务
./shell/arxiv_service.sh start

# 停止服务
./shell/arxiv_service.sh stop

# 重启服务（默认命令）
./shell/arxiv_service.sh restart
./shell/arxiv_service.sh  # 等同于 restart

# 查看状态
./shell/arxiv_service.sh status

# 健康检查
./shell/arxiv_service.sh health

# 实时查看日志
./shell/arxiv_service.sh logs
```

### 数据管理

```bash
# 初始构建（完整流程）
./shell/arxiv_service.sh build all

# 初始构建（分步执行）
./shell/arxiv_service.sh build fetch 1000    # 爬取1000篇到CSV
./shell/arxiv_service.sh build embed         # 从CSV嵌入

# 增量更新（完整流程）
./shell/arxiv_service.sh update all

# 增量更新（分步执行）
./shell/arxiv_service.sh update fetch 100    # 爬取100篇新论文
./shell/arxiv_service.sh update embed        # 嵌入最新的CSV

# 列出所有daily CSV文件
./shell/arxiv_service.sh list
```

## API 使用示例

### 搜索论文

```bash
curl -X POST http://localhost:5001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "large language models for code generation",
    "top_k": 5
  }'
```

响应示例：
```json
{
  "results": [
    {
      "paper_id": "2601.00756v1",
      "title": "论文标题",
      "authors": ["作者1", "作者2"],
      "published": "2026-01-02",
      "url": "http://arxiv.org/abs/2601.00756v1",
      "score": 1.6945,
      "title_similarity": 0.8683,
      "abstract_similarity": 0.8262
    }
  ],
  "query": "large language models for code generation",
  "top_k": 5,
  "total_results": 5
}
```

### 增量更新数据库

```bash
curl -X POST http://localhost:5001/api/v1/incremental_update \
  -H "Content-Type: application/json" \
  -d '{
    "max_results": 100,
    "batch_size": 50
  }'
```

### 查看数据库统计

```bash
curl http://localhost:5001/api/v1/stats
```

### 健康检查

```bash
curl http://localhost:5001/api/v1/health
```

## Builder CLI 工具

命令行工具用于数据库管理：

### Build 命令（初始构建）

```bash
# 完整流程（爬取 + 嵌入）
python scripts/run_builder.py build --mode all --max-results -1

# 只爬取到CSV
python scripts/run_builder.py build --mode fetch --max-results 1000

# 只从CSV嵌入
python scripts/run_builder.py build --mode embed
python scripts/run_builder.py build --mode embed --csv /data2/.../init_data.csv
```

### Update 命令（增量更新）

```bash
# 完整流程（推荐 - 自动跳过已存在论文）
python scripts/run_builder.py update --max-results 100

# 只爬取新论文到CSV
python scripts/run_builder.py update --mode fetch --max-results 50

# 只从CSV嵌入
python scripts/run_builder.py update --mode embed
python scripts/run_builder.py update --mode embed --csv daily/20260109_143025.csv
```

### 其他命令

```bash
# 列出所有daily CSV文件
python scripts/run_builder.py list-csv

# 查看统计信息
python scripts/run_builder.py stats

# 从 JSON 文件添加论文
python scripts/run_builder.py add --json papers.json

# 清空数据库（慎用！）
python scripts/run_builder.py clear
```

## 配置说明

主要配置项（`config/default.yaml`）：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `database.path` | ChromaDB存储路径 | `./data/chromadb_data` |
| `database.collection_name` | 集合名称 | `ArxivPapers` |
| `storage.csv_path` | CSV文件根目录 | `./data/papers` |
| `storage.init_filename` | 初始CSV文件名 | `init_data.csv` |
| `storage.daily_dir` | 增量CSV目录 | `daily` |
| `embedding.model_path` | 嵌入模型路径 | bge-m3 路径 |
| `embedding.device` | GPU 设备 | `cuda:3` |
| `embedding.batch_size` | 批处理大小 | `32` |
| `arxiv.time_filter.enabled` | 启用时间过滤 | `true` |
| `arxiv.time_filter.mode` | 过滤模式 | `years` |
| `arxiv.time_filter.value` | 过滤值 | `2`（最近2年）|
| `arxiv.max_results` | 最大爬取数量 | `-1`（使用 `-1` 表示不限制）|
| `arxiv.batch_size` | 爬取批次大小 | `50` |
| `arxiv.fetch_interval` | 批次间隔（秒） | `3.0`（支持小数，0 表示禁用）|
| `arxiv.batch_threshold_days` | 批量搜索停止阈值（天） | `1.0` |
| `arxiv.retry_max_attempts` | HTTP 429 最大重试次数 | `3` |
| `arxiv.retry_base_sleep` | 重试基础等待时间（秒） | `5.0`（指数退避）|
| `search.default_top_k` | 默认返回结果数 | `10` |
| `search.title_weight` | 标题权重 | `1.0` |
| `search.abstract_weight` | 摘要权重 | `1.0` |
| `api.host` | API 主机 | `0.0.0.0` |
| `api.port` | API 端口 | `5001` |

### 配置优先级

系统支持两级配置优先级（从高到低）：

1. **API 请求参数 / 命令行参数**（最高优先级）
2. **config/default.yaml 配置文件**（默认值）

**示例**：
```bash
# 不传参数 → 使用 config 里的 9000
python scripts/run_builder.py update
curl -X POST http://localhost:5001/api/v1/incremental_update -d '{}'

# 传入参数 → 覆盖 config
python scripts/run_builder.py update --max-results 100
curl -X POST http://localhost:5001/api/v1/incremental_update -d '{"max_results": 100}'
```

**注意**：`None` 值表示使用 config 默认值，`0` 是有效值不会被覆盖。

### 批次大小说明

系统有两个不同的 batch_size，作用于不同阶段：

| 配置项 | 作用阶段 | 默认值 | 说明 |
|--------|---------|--------|------|
| `arxiv.batch_size` | 爬取阶段 | 50 | 每爬 50 篇论文就存储一次（断点续传粒度） |
| `embedding.batch_size` | 嵌入阶段 | 32 | GPU 每次处理 32 个文档（优化 GPU 内存使用） |

**数据流**：
```
爬取 50 篇论文 → 转换成 100 个文档（title + abstract）
  → 分 4 批发送 GPU（32+32+32+4）→ 存入 ChromaDB
```

**为什么不对齐**：
- `arxiv.batch_size=50` - 优化网络请求频率和存储频率
- `embedding.batch_size=32` - 优化 GPU 内存使用和计算效率

### 批量搜索机制

系统使用时间迭代的批量搜索机制，避免一次性请求大量论文导致超时或内存问题。

**工作原理**：

1. **时间范围查询**：每批搜索使用 arXiv API 的 `submittedDate` 范围过滤
   - 初始范围：从 start_date（如 2年前）到当前时间
   - 每批最多获取 `batch_size` 篇论文（默认 50）

2. **时间迭代**：记录每批最早论文的时间，下一批从该时间往前搜
   ```
   批次1: [2024-01-07 TO 2026-01-06] → 获取50篇，最早时间: 2026-01-05
   批次2: [2024-01-07 TO 2026-01-05] → 获取50篇，最早时间: 2026-01-03
   批次3: [2024-01-07 TO 2026-01-03] → 获取50篇，最早时间: 2026-01-01
   ...继续直到达到停止条件
   ```

3. **智能停止条件**：
   - **达到目标数量**：`len(新论文) >= max_results`（有限模式）
   - **接近起始日期**：最早时间在 `start_date + 1天` 内
   - **无更多论文**：当前批次返回 0 篇论文

4. **稀疏时间段处理**：如果某批返回论文数 < batch_size，但时间还远离 start_date，继续搜索

**配置参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `arxiv.batch_size` | 50 | 每批搜索的论文数量 |
| `arxiv.batch_threshold_days` | 1.0 | 停止阈值（天），最早时间接近 start_date 多少天内停止 |
| `arxiv.fetch_interval` | 3.0 | 批次间隔（秒），避免对 arXiv 服务器压力过大 |

**优势**：

- ✅ **避免超时**：每批只请求 50 篇，API 请求快速可靠
- ✅ **内存友好**：不会一次性加载 50000 篇论文到内存
- ✅ **错误隔离**：单批失败不影响其他批次
- ✅ **实时进度**：每批完成后立即显示进度和统计信息
- ✅ **断点续传**：配合增量更新机制，已爬取的论文自动跳过

**示例输出**：

```
======================================================================
Fetching arXiv papers (BATCH MODE)
======================================================================
Categories: cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, cs.RO, cs.MA, cs.IR, cs.HC, stat.ML
Date range: 2024-01-07 to 2026-01-06
Max results: 100
Batch size: 50
Fetch interval: 3.0s (delay between batches)
Existing papers to skip: 6701
======================================================================

Batch 1: 50 papers fetched, earliest: 2026-01-05 15:30 (2.1s)
Sleeping 3.0s...

Batch 2: 50 papers fetched, earliest: 2026-01-03 09:15 (1.8s)
Sleeping 3.0s...

Batch 3: 25 papers fetched, earliest: 2026-01-01 12:00 (1.2s)
Reached max_results limit (100). Stopping.

======================================================================
Fetch complete
======================================================================
Total fetched:       125
Skipped (existing):  25
New papers:          100
======================================================================
```

## 常见问题

### 1. 如何更新论文数据库？

系统默认使用增量更新，自动跳过已存在的论文。

**方式一**：使用 API（推荐用于自动化）
```bash
curl -X POST http://localhost:5001/api/v1/incremental_update \
  -H "Content-Type: application/json" \
  -d '{"max_results": 100}'
```

**方式二**：使用 CLI
```bash
python scripts/run_builder.py update --max-results 100
```

**爬取所有论文**（不限制数量）：
```bash
# 使用 -1 表示不限制数量，爬取所有符合条件的论文
python scripts/run_builder.py update --max-results -1

# 或通过 API
curl -X POST http://localhost:5001/api/v1/incremental_update \
  -H "Content-Type: application/json" \
  -d '{"max_results": -1}'
```

**进度显示**：

- **正常模式**（有限制数量）：显示进度条
  ```
  Fetching papers: 45%|████████       | 450/1000 [01:30<01:50, 5.0 paper/s]
  fetched=600, filtered=500, new=450, skipped=50
  ```

- **Unlimited 模式**（-1 不限制）：显示动态计数器
  ```
  Fetching (unlimited): 150 papers | 2.5 paper/s | 00:01:00
  fetched=500, new=150, skipped=350
  ```

  - `150 papers` - 已添加的新论文数
  - `2.5 paper/s` - 实时处理速度
  - `00:01:00` - 已运行时间
  - `fetched=500` - 从 arXiv 获取的总数
  - `skipped=350` - 跳过的数量（已存在或未通过过滤）

**为什么 Unlimited 模式不显示"总数"？**

arXiv API 返回的总数（如 100,000）不准确，因为还有多重过滤：
```
API 总数 100,000（所有 cs.AI/cs.CL/cs.LG）
  ↓ 时间过滤（最近 2 年）→ 约 30,000
  ↓ 关键词过滤（AI/LLM）→ 约 10,000
  ↓ 去重（跳过已有）→ 约 150 篇新论文
```
如果显示 "150/100,000 (0.15%)"，会让用户误以为还要很久，实际上可能马上完成。

**定时任务示例**（每天凌晨2点更新）：
```bash
# 添加到 crontab
0 2 * * * cd /path/to/arxiv_fetcher && /path/to/conda/envs/<your_env>/bin/python scripts/run_builder.py update --max-results 100
```

### 2. 健康检查失败怎么办？

查看日志排查问题：
```bash
# 查看最新日志
tail -f logs/api.log

# 查看错误日志
tail -f logs/api.err

# 查看服务状态（包含日志摘要）
./shell/arxiv_service.sh status
```

常见问题：
- GPU 不可用：检查 `nvidia-smi` 确认 GPU 3 可用
- 端口被占用：修改 `config/default.yaml` 中的 `api.port`
- 模型加载失败：检查 `embedding.model_path` 是否正确

### 3. 如何重建数据库？

```bash
# 清空数据库
python scripts/run_builder.py clear

# 重新构建
python scripts/run_builder.py update --max-results 9000
```

### 4. 如何调整搜索结果的相关性？

编辑 `config/default.yaml`：

```yaml
search:
  title_weight: 1.5      # 增加标题权重
  abstract_weight: 1.0   # 摘要权重保持不变
```

更大的权重意味着该部分在相似度计算中更重要。

### 5. 如何控制爬取速度？

通过 `fetch_interval` 设置批次间隔，避免对 arXiv 服务器造成过大压力：

```yaml
# config/default.yaml
arxiv:
  batch_size: 50
  fetch_interval: 1.0  # 每个批次后暂停 1 秒
```

**支持小数**：
- `0.5` - 每批次后暂停 0.5 秒
- `1.5` - 每批次后暂停 1.5 秒
- `2.0` - 每批次后暂停 2 秒
- `0` - 不暂停（最快速度，不推荐）

**推荐设置**：
- 快速爬取：`0.5s`（25 秒/批）
- 正常速度：`1.0s`（50 秒/批）
- 礼貌模式：`2.0s`（100 秒/批）

**估算时间**：
```
总时间 = (论文数量 / batch_size) × fetch_interval

例如：10000 篇论文，batch_size=50，fetch_interval=1.0
总时间 = (10000 / 50) × 1.0 = 200 秒 ≈ 3.3 分钟
```

### 6. 服务无法启动？

检查 conda 环境：
```bash
# 确认环境存在
conda env list

# 如果环境名不是 myAgent，编辑 shell/arxiv_service.sh
# 修改 CONDA_ENV 变量
```

### 7. 如何切换嵌入模型？

**重要提示**：嵌入维度没有硬编码，系统会自动检测模型维度。当前使用 bge-m3 (1024维)。

**情况1：相同维度的模型**（如都是1024维）

可以直接修改config，但建议重建数据库以保证搜索准确度：

```yaml
# config/default.yaml
embedding:
  model_path: /path/to/new-1024d-model
  device: cuda:3
```

```bash
# 重建数据库（推荐）
python scripts/run_builder.py clear
python scripts/run_builder.py build --mode embed
```

**情况2：不同维度的模型**（如1024→768）

**必须清空旧数据并重建**，因为ChromaDB collection维度已固定：

```bash
# 1. 清空旧数据
python scripts/run_builder.py clear

# 2. 修改config
vim config/default.yaml  # 改model_path

# 3. 重新构建（会自动检测新维度）
python scripts/run_builder.py build --mode all
```

**情况3：保留旧数据测试新模型**（推荐）

使用不同的collection名称，新旧数据互不影响：

```yaml
# config/default.yaml
database:
  collection_name: ArxivPapers_NewModel  # 修改collection名

embedding:
  model_path: /path/to/new-model
```

然后正常build即可，系统会创建新collection。

**维度自动检测**：

系统启动时会自动显示模型维度：
```
Loading embedding model: /path/to/model
Device: cuda:3
✓ Embedding model loaded (dimension: 1024)
```

如果维度不匹配旧collection，查询时会报错。

## 系统架构

```
┌─────────────────────────────────────┐
│   CLI/Bash (run_builder.py + sh)   │
│   - build fetch/embed               │
│   - update fetch/embed              │
└──────────────┬──────────────────────┘
               ↓
┌──────────────────────────────────────┐
│         Builder (builder.py)         │
│  - build_fetch() → CSV               │
│  - build_embed() → ChromaDB          │
│  - update_fetch() → CSV              │
│  - update_embed() → ChromaDB         │
└──────┬───────────────┬───────────────┘
       ↓               ↓
┌─────────────┐  ┌──────────────┐
│  Fetcher    │  │  CSVManager  │
│  (爬取)     │  │  (CSV读写)   │
└─────────────┘  └──────────────┘
                       ↓
                 ┌──────────────┐
                 │ ChromaDB     │
                 │ (向量存储)   │
                 └──────────────┘
                       ↓
                 ┌──────────────┐
                 │ API Server   │
                 │ (Flask)      │
                 └──────────────┘
```

### 核心组件

- **Fetcher** - arXiv 论文获取器
  - 类别：cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, cs.RO, cs.MA, cs.IR, cs.HC, stat.ML（10个类别）
  - 无关键词过滤，全覆盖AI相关论文
  - 时间过滤：支持天/周/月/年
  - 自动去重：基于paper ID

- **CSVManager** - CSV持久化管理器
  - init_data.csv：初始构建数据
  - daily/时间戳.csv：增量更新数据
  - UTF-8 BOM编码，支持中文

- **Builder** - 数据库构建器
  - 分阶段执行：fetch（爬取）和 embed（嵌入）
  - build模式：全量构建
  - update模式：增量更新
  - 双重嵌入（标题 + 摘要）

- **Searcher** - 语义搜索引擎
  - 双重相似度评分
  - 加权综合排序

- **API** - RESTful 接口
  - Swagger/OpenAPI 文档
  - 6 个主要端点

### 数据流

**Build模式（初始构建）**：
```
arXiv API → Fetcher (10类别) → init_data.csv →
  Embedding → ChromaDB (向量数据库)
```

**Update模式（增量更新）**：
```
arXiv API → Fetcher (去重) → daily/时间戳.csv →
  Embedding → ChromaDB (增量添加)
```

**搜索流程**：
```
用户查询 → API → Searcher → ChromaDB →
  双重评分 → 排序结果 → 返回客户端
```

## 目录结构

```
arxiv_fetcher/
├── config/              # 配置文件
│   └── default.yaml     # 主配置文件
├── shell/               # Shell 脚本
│   └── arxiv_service.sh # 服务和数据管理脚本
├── logs/                # 日志文件（运行时生成）
├── src/                 # 源代码
│   ├── config/          # 配置管理（OmegaConf）
│   ├── core/            # 核心业务逻辑
│   │   ├── fetcher.py   # arXiv爬虫
│   │   ├── builder.py   # 数据库构建器
│   │   └── searcher.py  # 语义搜索引擎
│   ├── storage/         # CSV持久化
│   │   └── csv_manager.py
│   ├── database/        # 数据库管理
│   │   └── chromadb_manager.py
│   └── api/             # API 接口
├── scripts/             # 运行脚本
│   ├── run_builder.py   # CLI工具
│   └── run_api.py       # API服务
└── tests/               # 测试文件
```

## 数据存储结构

```
/path/to/data/
├── chromadb_data/       # ChromaDB向量数据库
└── papers/              # CSV文件存储
    ├── init_data.csv    # 初始构建数据
    └── daily/           # 增量更新数据
        ├── 20260109_163622.csv
        ├── 20260110_020000.csv
        └── ...
```

## 技术栈

- **向量数据库**：ChromaDB 1.4.0
- **嵌入模型**：bge-m3（1024 维，支持中英文）
- **API 框架**：Flask 3.1.2 + Flask-RESTX 1.3.0
- **配置管理**：OmegaConf 2.3.0
- **爬虫**：arxiv 2.1.3 (Python 库)
- **深度学习**：PyTorch 2.9.1
- **文本嵌入**：sentence-transformers 5.2.0
- **生产服务器**：gunicorn 23.0.0（可选）

## 性能特性

- **GPU 加速**：使用 cuda:3 加速嵌入计算
- **批处理**：默认批次大小 32（嵌入）/ 50（爬取）
- **增量更新**：自动去重，支持断点续传
- **向量归一化**：提高搜索准确度
- **双重评分**：综合考虑标题和摘要相似度

## 许可证

MIT License

