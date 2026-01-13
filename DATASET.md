# arXiv AI Papers 数据集说明 / Dataset Documentation

[English](#english) | [中文](#中文)

---

## 中文

### 数据集概述

本数据集包含214,100篇来自arXiv的AI/机器学习相关论文的元数据，时间跨度为2024年1月至2026年1月。

### 基本信息

| 项目 | 说明 |
|------|------|
| **论文数量** | 214,100篇 |
| **时间范围** | 2024-01-07 至 2026-01-08 |
| **文件大小** | 309 MB (CSV格式) |
| **文件格式** | CSV (UTF-8 BOM编码) |
| **更新频率** | 可定期增量更新 |

### 覆盖的arXiv类别

本数据集涵盖10个AI相关的arXiv类别：

| 类别代码 | 领域名称 | 说明 |
|----------|---------|------|
| cs.AI | 人工智能 | Artificial Intelligence |
| cs.LG | 机器学习 | Machine Learning |
| cs.CL | 计算语言学 | Computation and Language (NLP) |
| cs.CV | 计算机视觉 | Computer Vision and Pattern Recognition |
| cs.NE | 神经网络 | Neural and Evolutionary Computing |
| cs.RO | 机器人 | Robotics |
| cs.MA | 多智能体系统 | Multiagent Systems |
| cs.IR | 信息检索 | Information Retrieval |
| cs.HC | 人机交互 | Human-Computer Interaction |
| stat.ML | 统计机器学习 | Machine Learning (Statistics) |

### 数据字段

CSV文件包含以下字段：

| 字段名 | 数据类型 | 说明 | 示例 |
|--------|---------|------|------|
| `id` | String | arXiv论文唯一标识符 | `2601.05251v1` |
| `title` | String | 论文标题 | `Mesh4D: 4D Mesh Reconstruction...` |
| `abstract` | String | 论文摘要（已移除换行） | `We propose Mesh4D, a feed-forward...` |
| `authors` | String | 作者列表（分号分隔） | `Author1;Author2;Author3` |
| `published` | String | 发布日期 (YYYY-MM-DD) | `2026-01-08` |
| `url` | String | arXiv论文链接 | `http://arxiv.org/abs/2601.05251v1` |

### 下载地址

#### 下载源

- **ModelScope**

  https://www.modelscope.cn/datasets/ausertdream/arxiv_ai_paper_data

### 使用示例

#### 1. 使用pandas加载

```python
import pandas as pd

# 加载CSV文件
df = pd.read_csv('init_data.csv', encoding='utf-8-sig')

# 查看基本信息
print(f"总论文数: {len(df)}")
print(f"字段: {df.columns.tolist()}")
print(df.head())

# 分析作者列表
df['author_count'] = df['authors'].str.split(';').str.len()
print(f"平均作者数: {df['author_count'].mean():.2f}")

# 按年份统计
df['year'] = pd.to_datetime(df['published']).dt.year
print(df['year'].value_counts().sort_index())
```

#### 2. 数据分析示例

```python
import matplotlib.pyplot as plt

# 论文时间分布
df['date'] = pd.to_datetime(df['published'])
df.groupby(df['date'].dt.to_period('M')).size().plot(kind='bar', figsize=(12, 6))
plt.title('Monthly Paper Distribution')
plt.xlabel('Month')
plt.ylabel('Number of Papers')
plt.show()

# 摘要长度分析
df['abstract_length'] = df['abstract'].str.len()
df['abstract_length'].hist(bins=50, figsize=(10, 6))
plt.title('Abstract Length Distribution')
plt.xlabel('Abstract Length (characters)')
plt.ylabel('Frequency')
plt.show()
```

#### 3. 与本项目集成

下载数据后，使用项目工具构建向量数据库：

```bash
# 1. 将CSV文件放置到项目data目录
mkdir -p data
cp init_data.csv data/

# 2. 从CSV构建向量数据库
python scripts/run_builder.py build --mode embed

# 3. 启动API服务
./shell/arxiv_service.sh start

# 4. 搜索论文
curl -X POST http://localhost:5001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "large language models", "top_k": 5}'
```

### 数据来源

#### 数据来源
- **数据源**: arXiv.org官方API
- **采集方式**: 使用arXiv Python API (arxiv==2.1.3)
- **采集时间**: 2026年1月
- **采集范围**: 10个AI相关类别，最近2年的论文

#### 隐私声明
- ✅ 不包含任何个人隐私信息
- ✅ 所有数据均为公开发表的学术论文元数据
- ✅ 作者名字为公开署名，无隐私问题
- ✅ 符合arXiv使用条款

---

## English

### Dataset Overview

This dataset contains metadata of 214,100 AI/Machine Learning related papers from arXiv, spanning from January 2024 to January 2026.

### Basic Information

| Item | Description |
|------|-------------|
| **Paper Count** | 214,100 papers |
| **Time Range** | 2024-01-07 to 2026-01-08 |
| **File Size** | 309 MB (CSV format) |
| **File Format** | CSV (UTF-8 BOM encoding) |
| **Update Frequency** | Can be incrementally updated |

### Covered arXiv Categories

This dataset covers 10 AI-related arXiv categories:

| Category Code | Field Name | Description |
|---------------|------------|-------------|
| cs.AI | Artificial Intelligence | AI research |
| cs.LG | Machine Learning | ML algorithms and theory |
| cs.CL | Computation and Language | Natural Language Processing |
| cs.CV | Computer Vision | Computer Vision and Pattern Recognition |
| cs.NE | Neural and Evolutionary Computing | Neural networks and evolutionary algorithms |
| cs.RO | Robotics | Robot learning and control |
| cs.MA | Multiagent Systems | Multi-agent reinforcement learning |
| cs.IR | Information Retrieval | Search and recommendation |
| cs.HC | Human-Computer Interaction | HCI and AI interaction |
| stat.ML | Machine Learning (Statistics) | Statistical learning theory |

### Data Fields

The CSV file contains the following fields:

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `id` | String | arXiv paper unique identifier | `2601.05251v1` |
| `title` | String | Paper title | `Mesh4D: 4D Mesh Reconstruction...` |
| `abstract` | String | Paper abstract (newlines removed) | `We propose Mesh4D, a feed-forward...` |
| `authors` | String | Author list (semicolon-separated) | `Author1;Author2;Author3` |
| `published` | String | Publication date (YYYY-MM-DD) | `2026-01-08` |
| `url` | String | arXiv paper link | `http://arxiv.org/abs/2601.05251v1` |

### Download Links

#### Primary Sources

- **ModelScope**
  https://www.modelscope.cn/datasets/ausertdream/arxiv_ai_paper_data


### Usage Examples

#### 1. Load with pandas

```python
import pandas as pd

# Load CSV file
df = pd.read_csv('init_data.csv', encoding='utf-8-sig')

# View basic info
print(f"Total papers: {len(df)}")
print(f"Fields: {df.columns.tolist()}")
print(df.head())

# Analyze author list
df['author_count'] = df['authors'].str.split(';').str.len()
print(f"Average authors: {df['author_count'].mean():.2f}")

# Statistics by year
df['year'] = pd.to_datetime(df['published']).dt.year
print(df['year'].value_counts().sort_index())
```

#### 2. Data Analysis Example

```python
import matplotlib.pyplot as plt

# Paper time distribution
df['date'] = pd.to_datetime(df['published'])
df.groupby(df['date'].dt.to_period('M')).size().plot(kind='bar', figsize=(12, 6))
plt.title('Monthly Paper Distribution')
plt.xlabel('Month')
plt.ylabel('Number of Papers')
plt.show()

# Abstract length analysis
df['abstract_length'] = df['abstract'].str.len()
df['abstract_length'].hist(bins=50, figsize=(10, 6))
plt.title('Abstract Length Distribution')
plt.xlabel('Abstract Length (characters)')
plt.ylabel('Frequency')
plt.show()
```

#### 3. Integration with This Project

After downloading the data, use project tools to build vector database:

```bash
# 1. Place CSV file in project data directory
mkdir -p data
cp init_data.csv data/

# 2. Build vector database from CSV
python scripts/run_builder.py build --mode embed

# 3. Start API service
./shell/arxiv_service.sh start

# 4. Search papers
curl -X POST http://localhost:5001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "large language models", "top_k": 5}'
```

### Data Source

#### Data Source
- **Source**: arXiv.org official API
- **Collection Method**: Using arXiv Python API (arxiv==2.1.3)
- **Collection Time**: January 2026
- **Collection Scope**: 10 AI-related categories, papers from last 2 years

#### Privacy Statement
- ✅ Does not contain any personal privacy information
- ✅ All data are publicly published academic paper metadata
- ✅ Author names are public attributions, no privacy concerns
- ✅ Complies with arXiv Terms of Service