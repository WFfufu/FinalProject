# 知乎热榜数据采集与分析系统

## 📋 项目概述

本项目是一个功能完整的知乎热榜数据采集与智能分析系统，实现了自动化数据采集、多维度分析和可视化展示。系统采用模块化设计，具备强大的数据处理能力和丰富的分析功能。

## ✨ 核心特性

- 🔍 **智能数据采集**：自动登录知乎，实时采集热榜数据，支持详细信息提取
- 🛡️ **反爬虫机制**：Cookie管理、请求头伪装、智能延迟等完善的反爬虫策略
- 📊 **多维度分析**：6大分析维度，生成高清图表和详细报告
- 💾 **数据存储管理**：JSON格式存储，智能去重，完整的历史数据管理
- 🌐 **Web可视化**：交互式仪表板，实时数据展示
- ⚙️ **命令行工具**：简单易用的CLI界面，支持多种操作模式
- 📈 **趋势分析**：时间序列分析，热度变化追踪

## 🛠️ 技术栈

- **编程语言**: Python 3.8+
- **爬虫框架**: Selenium + BeautifulSoup
- **数据处理**: Pandas + NumPy
- **可视化**: Matplotlib + Plotly + Seaborn
- **Web框架**: Flask (仪表板)
- **存储格式**: JSON + Pickle (Cookie)
- **配置管理**: YAML

## 📁 项目结构

```
CRAWLER_FINALPROJECT/
├── README.md                           # 项目说明文档
├── requirements.txt                    # Python依赖包列表
├── crawler_config.yaml                 # 爬虫主配置文件
├── run_crawler.py                      # 主运行脚本 🚀
├── zhihu_crawler.py                    # 知乎爬虫核心类
├── zhihu_login_crawler.py              # 登录功能模块
├── enhanced_visualization.py           # 数据可视化模块
├── web_dashboard.py                    # Web仪表板
├── data_export_tool.py                 # 数据导出工具
├── data/                               # 数据存储目录
│   ├── raw/                           # 原始爬取数据 (JSON)
│   │   ├── zhihu_hot_20250602_*.json
│   │   └── ...
│   ├── analysis/                      # 分析图表 (PNG)
│   │   ├── chart1_daily_trend_*.png
│   │   ├── chart4_popular_tags_*.png
│   │   ├── chart5_hourly_activity_*.png
│   │   └── chart6_data_quality_*.png
│   └── reports/                       # 分析报告 (MD)
│       ├── analysis_report_*.md
│       └── ...
├── logs/                              # 日志文件
├── templates/                         # 模板文件
│   └── dashboard.html                 # 仪表板模板
├── zhihu_cookies.pkl                  # 登录状态保存
├── crawl_history.json                 # 爬取历史记录
└── question_hashes.json               # 问题去重缓存
```

## 📊 数据模型

### 热榜数据结构

```json
{
    "rank": 1,                          // 热榜排名
    "question_title": "热榜问题标题",    // 问题标题
    "question_url": "https://...",      // 问题链接
    "question_hash": "abc123...",       // 问题唯一标识
    "answer_count": 541,                // 回答数量
    "question_tags": ["科技", "AI"],    // 问题标签
    "date": "2025-06-02",              // 日期
    "crawl_time": "2025-06-02 15:13:28" // 采集时间
}
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Chrome浏览器
- 8GB+ 内存 (推荐)

### 安装步骤

1. **克隆项目**

```bash
git clone <repository-url>
cd CRAWLER_FINALPROJECT
```

1. **安装依赖**

```bash
pip install -r requirements.txt
```

1. **首次登录设置**

```bash
# 首次使用需要手动登录知乎
python zhihu_login_crawler.py
```

1. **运行爬虫**

```bash
# 基础爬取
python run_crawler.py crawl

# 详细爬取
python run_crawler.py crawl --detailed

# 后台运行
python run_crawler.py crawl --headless
```

## 📋 使用指南

### 命令行操作

```bash
# 🔍 数据采集
python run_crawler.py crawl                    # 基础爬取
python run_crawler.py crawl --detailed         # 详细信息爬取
python run_crawler.py crawl --headless         # 后台模式

# 📊 数据分析
python run_crawler.py analyze --type all --days 7     # 综合分析
python run_crawler.py analyze --type trend --days 30  # 趋势分析
python run_crawler.py analyze --type charts --days 14 # 图表生成

# 🌐 Web界面
python run_crawler.py dashboard                # 启动仪表板
python run_crawler.py export --format csv      # 数据导出
```

### 配置文件说明

`crawler_config.yaml` 主要配置：

```yaml
basic:
  data_dir: "data"              # 数据目录
  max_retries: 3               # 最大重试次数
  delay_range: [2, 5]          # 请求延迟范围

crawler:
  headless: false              # 是否后台运行
  timeout: 30                  # 超时时间
  extract_details: true        # 是否提取详细信息

analysis:
  default_days: 7              # 默认分析天数
  chart_dpi: 300              # 图表分辨率
```

## 📈 数据分析功能

### 六大分析维度

1. **📈 每日数据采集趋势**
   - 数据量变化趋势
   - 峰值检测和标注
   - 趋势线预测
2. **🏆 排名区间分布**
   - 5个排名区间统计
   - 热门程度分类
   - 数据量对比
3. **💬 回答数分布分析**
   - 回答数分布直方图
   - 均值/中位数标注
   - 统计指标展示
4. **🏷️ 热门话题标签**
   - TOP15热门标签
   - 出现频次排行
   - 标签趋势分析
5. **⏰ 24小时活跃度**
   - 全天候活跃度分布
   - 高峰时段标注
   - 时段活跃度对比
6. **📊 数据质量指标**
   - 数据完整性分析
   - 质量评估指标
   - 统计概览信息

### 生成的文件类型

- **高清图表**: 300 DPI PNG格式，支持单独查看和分享
- **分析报告**: Markdown格式，包含详细统计和发现
- **原始数据**: JSON格式，便于二次开发和分析

## 🌐 Web仪表板

启动Web界面查看实时数据：

```bash
python run_crawler.py dashboard
```

功能特性：

- 📊 实时数据展示
- 📈 交互式图表
- 🔍 数据搜索和过滤
- 📁 历史数据浏览
- 📤 数据导出功能

## 🛡️ 反爬虫策略

1. **智能登录管理**
   - Cookie自动保存和加载
   - 登录状态检测
   - 会话保持机制
2. **请求控制**
   - 随机延迟 (2-5秒)
   - 请求头伪装
   - 浏览器指纹模拟
3. **错误处理**
   - 自动重试机制
   - 异常恢复
   - 日志记录和监控

## 🔧 扩展功能

### 已实现

- ✅ 多种数据导出格式 (CSV, Excel, JSON)
- ✅ 智能去重算法
- ✅ 历史数据管理
- ✅ 详细的日志记录
- ✅ 配置文件管理

### 计划中

- 🔄 定时任务调度
- 📧 邮件报告推送
- 🔔 实时监控告警
- 🤖 API接口服务
- 📱 移动端适配

## 📚 输出示例

### 图表文件

```
data/analysis/
├── chart1_daily_trend_20250602_151328.png      # 每日趋势图
├── chart4_popular_tags_20250602_151328.png     # 热门标签图
├── chart5_hourly_activity_20250602_151328.png  # 时段活跃度图
└── chart6_data_quality_20250602_151328.png     # 数据质量图
```

### 分析报告

```markdown
# 知乎热榜数据分析报告

## 📊 数据概览
- 分析周期: 7天
- 总记录数: 266条
- 独特问题: 38个
- 数据完整率: 85.2%

## 🔍 关键发现
1. 高峰活跃时段: 13:00-14:00
2. 热门话题: 欧洲杯、科技、社会
3. 平均回答数: 257.3个
...
```

## ⚠️ 使用注意事项

### 合规性要求

- 🚫 **仅供学习研究使用**，严禁商业用途
- 📋 **遵守知乎服务条款**和robots.txt协议
- 🔒 **保护用户隐私**，不采集个人敏感信息
- ⏰ **合理控制频率**，避免对服务器造成压力

### 技术建议

- 💻 建议在稳定网络环境下运行
- 🕒 避免在知乎高峰期 (晚上8-10点) 大量采集
- 💾 定期清理历史数据，控制存储空间
- 📊 分析大量数据时建议增加内存配置

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建功能分支
3. 提交改动
4. 发起Pull Request

## 📄 许可证

本项目仅供学习和研究使用，请遵守相关法律法规和平台服务条款。

