# 知乎热榜数据采集与存储系统

## 项目概述

本项目是一个针对知乎热榜的多源数据采集与存储系统，旨在自动化采集知乎热榜信息，并进行结构化存储与分析展示。系统采用模块化设计，具备良好的可配置性和可扩展性。

## 功能特性

- 🔍 **多维度数据采集**：抓取知乎热榜的标题、热度值、排名、分类、链接等信息
- 🛡️ **反爬虫应对**：实现请求头伪装、访问频率控制、代理池等机制
- 💾 **结构化存储**：支持多种存储方式（MySQL/MongoDB/JSON）
- 📊 **数据分析展示**：提供数据统计分析和可视化展示功能
- ⚙️ **模块化设计**：采用配置文件驱动，便于扩展和维护
- 🔄 **定时任务**：支持定时自动采集，跟踪热榜变化趋势

## 技术栈

- **编程语言**: Python 3.8+
- **爬虫框架**: Scrapy / BeautifulSoup + Requests
- **数据存储**: MySQL / MongoDB / Redis
- **任务调度**: APScheduler / Celery
- **数据分析**: Pandas / NumPy
- **可视化**: Matplotlib / Plotly / ECharts
- **Web框架**: Flask / FastAPI (可选)

## 项目结构

```
zhihu-hot-crawler/
├── README.md                 # 项目说明文档
├── requirements.txt          # 依赖包列表
├── config/                   # 配置文件目录
│   ├── config.yaml          # 主配置文件
│   ├── database.yaml        # 数据库配置
│   └── crawler.yaml         # 爬虫配置
├── src/                     # 源代码目录
│   ├── crawler/            # 爬虫模块
│   │   ├── __init__.py
│   │   ├── spider.py       # 爬虫主类
│   │   ├── parser.py       # 数据解析器
│   │   └── middleware.py   # 中间件（反爬虫）
│   ├── storage/            # 存储模块
│   │   ├── __init__.py
│   │   ├── mysql_storage.py
│   │   ├── mongo_storage.py
│   │   └── models.py       # 数据模型
│   ├── analysis/           # 分析模块
│   │   ├── __init__.py
│   │   ├── statistics.py   # 统计分析
│   │   └── visualize.py    # 数据可视化
│   ├── scheduler/          # 调度模块
│   │   ├── __init__.py
│   │   └── tasks.py        # 定时任务
│   └── utils/              # 工具模块
│       ├── __init__.py
│       ├── logger.py       # 日志工具
│       └── proxy_pool.py   # 代理池
├── data/                    # 数据目录
│   ├── raw/                # 原始数据
│   ├── processed/          # 处理后数据
│   └── exports/            # 导出数据
├── logs/                    # 日志目录
├── tests/                   # 测试目录
│   ├── test_crawler.py
│   ├── test_storage.py
│   └── test_analysis.py
├── docs/                    # 文档目录
│   ├── API.md              # API文档
│   └── deployment.md       # 部署文档
└── scripts/                 # 脚本目录
    ├── setup.sh            # 环境配置脚本
    └── run.sh              # 运行脚本
```

## 数据结构

### 热榜数据模型

json

```json
{
    "rank": 1,                    // 排名
    "title": "热榜标题",          // 标题
    "heat_value": "2223万热度",   // 热度值
    "category": "时事",           // 分类
    "url": "https://...",        // 链接
    "question_id": "123456",      // 问题ID
    "answer_count": 541,          // 回答数
    "view_count": 180000,         // 浏览数
    "excerpt": "问题描述...",     // 摘要
    "created_time": "2024-01-01", // 创建时间
    "crawl_time": "2024-01-01"    // 采集时间
}
```

## 快速开始

### 环境要求

- Python 3.8+
- MySQL 5.7+ 或 MongoDB 4.0+ (可选)
- Redis 5.0+ (可选，用于代理池)

### 安装步骤

1. **克隆项目**

bash

```bash
git clone https://github.com/yourusername/zhihu-hot-crawler.git
cd zhihu-hot-crawler
```

1. **创建虚拟环境**

bash

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

1. **安装依赖**

bash

```bash
pip install -r requirements.txt
```

1. **配置数据库**

bash

```bash
# 修改 config/database.yaml 中的数据库连接信息
# 运行数据库初始化脚本
python scripts/init_db.py
```

1. **运行爬虫**

bash

```bash
# 单次运行
python src/main.py

# 定时运行
python src/scheduler/run_scheduler.py
```

## 使用指南

### 基础使用

python

```python
from src.crawler import ZhihuHotCrawler
from src.storage import MySQLStorage

# 初始化爬虫和存储
crawler = ZhihuHotCrawler()
storage = MySQLStorage()

# 执行爬取
data = crawler.crawl()

# 存储数据
storage.save_batch(data)
```

### 配置说明

`config/crawler.yaml` 示例：

yaml

```yaml
crawler:
  target_url: "https://www.zhihu.com/hot"
  user_agent: "Mozilla/5.0..."
  timeout: 30
  retry_times: 3
  delay_range: [1, 3]  # 请求延迟范围（秒）
  
proxy:
  enabled: false
  pool_size: 10
  
storage:
  type: "mysql"  # mysql/mongodb/json
  batch_size: 100
```

### 数据分析示例

python

```python
from src.analysis import HotAnalyzer

analyzer = HotAnalyzer()

# 获取热度趋势
trends = analyzer.get_heat_trends(days=7)

# 生成报告
analyzer.generate_report(output="data/exports/weekly_report.html")
```

## 反爬虫策略

1. **请求头伪装**：随机User-Agent、Referer等
2. **访问频率控制**：随机延迟、限制并发
3. **代理池**：支持代理IP轮换
4. **Cookie管理**：模拟登录状态维护
5. **验证码处理**：集成验证码识别服务

## 扩展功能

-  支持更多热榜类型（科技热榜、视频热榜等）
-  实时推送功能（邮件/微信通知）
-  Web管理界面
-  API接口服务
-  情感分析功能
-  多平台对比分析

## 注意事项

1. **合规性**：请遵守知乎的robots.txt协议和服务条款
2. **频率限制**：避免过于频繁的请求，建议间隔3-5秒
3. **数据使用**：仅供学习研究使用，不得用于商业用途
4. **隐私保护**：不采集用户个人隐私信息