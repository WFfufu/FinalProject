#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知乎热榜爬虫系统启动脚本
支持命令行参数，便于部署和自动化
"""

import argparse
import sys
import os
import yaml
from datetime import datetime

# 添加项目根目录到路径
#sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 从主模块导入类（假设保存为zhihu_crawler.py）
try:
    from zhihu_crawler import EnhancedZhihuCrawler, HotListAnalyzer, ScheduledCrawler
except ImportError:
    print("错误：无法导入爬虫模块，请确保zhihu_crawler.py在同一目录下")
    sys.exit(1)


def load_config(config_file="crawler_config.yaml"):
    """加载配置文件"""
    if not os.path.exists(config_file):
        print(f"警告：配置文件 {config_file} 不存在，使用默认配置")
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"错误：加载配置文件失败 - {e}")
        return {}


def run_single_crawl(args, config):
    """执行单次爬取"""
    data_dir = config.get('basic', {}).get('data_dir', 'data')
    crawler = EnhancedZhihuCrawler(data_dir)
    
    print(f"开始{'详细' if args.detailed else '基础'}爬取...")
    
    filepath = crawler.run_single_crawl(
        extract_details=args.detailed,
        headless=args.headless
    )
    
    if filepath:
        print(f"✓ 爬取完成，数据已保存到: {filepath}")
        
        # 如果启用了分析，自动生成报告
        if args.auto_analysis:
            analyzer = HotListAnalyzer(data_dir)
            analyzer.generate_report(days=1)
            print("✓ 分析报告已自动生成")
    else:
        print("✗ 爬取失败")
        sys.exit(1)


def run_analysis(args, config):
    """执行数据分析"""
    data_dir = config.get('basic', {}).get('data_dir', 'data')
    analyzer = HotListAnalyzer(data_dir)
    
    print(f"开始分析最近{args.days}天的数据...")
    
    # 生成报告
    report_path = analyzer.generate_report(days=args.days)
    print(f"✓ 分析报告已生成: {report_path}")
    
    # 生成图表
    if args.charts:
        analyzer.generate_trend_charts(days=args.days)
        print("✓ 趋势图表已生成")


def run_scheduler(args, config):
    """启动定时任务"""
    data_dir = config.get('basic', {}).get('data_dir', 'data')
    scheduler = ScheduledCrawler(data_dir)
    
    print("启动定时任务调度器...")
    
    if args.config_jobs:
        # 从配置文件读取任务设置
        # 这里可以扩展配置文件驱动的任务设置
        pass
    
    scheduler.start_scheduler()


def check_environment():
    """检查运行环境"""
    print("检查运行环境...")
    
    # 检查Chrome浏览器
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        
        driver = webdriver.Chrome(options=options)
        driver.quit()
        print("✓ Chrome浏览器检查通过")
    except Exception as e:
        print(f"✗ Chrome浏览器检查失败: {e}")
        print("请确保已安装Chrome浏览器和ChromeDriver")
        return False
    
    # 检查必要的目录
    required_dirs = ['data', 'data/raw', 'data/analysis', 'data/reports', 'data/logs']
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)
    print("✓ 目录结构检查通过")
    
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="知乎热榜爬虫系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python run_crawler.py crawl                    # 基础爬取
  python run_crawler.py crawl --detailed         # 详细爬取
  python run_crawler.py crawl --headless         # 无头模式爬取
  python run_crawler.py analyze --days 7         # 分析最近7天数据
  python run_crawler.py analyze --days 30 --charts  # 分析并生成图表
  python run_crawler.py schedule                 # 启动定时任务
  python run_crawler.py check                    # 检查环境
        """
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 爬取命令
    crawl_parser = subparsers.add_parser('crawl', help='执行爬取任务')
    crawl_parser.add_argument('--detailed', action='store_true', 
                             help='提取详细信息（回答数、浏览数等）')
    crawl_parser.add_argument('--headless', action='store_true',
                             help='无头模式运行（适合服务器部署）')
    crawl_parser.add_argument('--auto-analysis', action='store_true',
                             help='爬取完成后自动生成分析报告')
    
    # 分析命令
    analysis_parser = subparsers.add_parser('analyze', help='执行数据分析')
    analysis_parser.add_argument('--days', type=int, default=7,
                                help='分析天数（默认7天）')
    analysis_parser.add_argument('--charts', action='store_true',
                                help='生成趋势图表')
    
    # 定时任务命令
    schedule_parser = subparsers.add_parser('schedule', help='启动定时任务')
    schedule_parser.add_argument('--config-jobs', action='store_true',
                                help='使用配置文件中的任务设置')
    
    # 环境检查命令
    check_parser = subparsers.add_parser('check', help='检查运行环境')
    
    # 全局参数
    parser.add_argument('--config', default='crawler_config.yaml',
                       help='配置文件路径（默认：crawler_config.yaml）')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出模式')
    
    args = parser.parse_args()
    
    # 如果没有提供命令，显示帮助
    if not args.command:
        parser.print_help()
        return
    
    # 加载配置
    config = load_config(args.config)
    
    # 设置日志级别
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 执行命令
    try:
        if args.command == 'check':
            if check_environment():
                print("✓ 环境检查通过，可以正常运行爬虫")
            else:
                print("✗ 环境检查失败，请解决上述问题后重试")
                sys.exit(1)
        
        elif args.command == 'crawl':
            if not check_environment():
                sys.exit(1)
            run_single_crawl(args, config)
        
        elif args.command == 'analyze':
            run_analysis(args, config)
        
        elif args.command == 'schedule':
            if not check_environment():
                sys.exit(1)
            run_scheduler(args, config)
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行出错: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()