#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据导出和备份工具
支持多种格式导出、数据清理、备份管理
"""

import os
import json
import pandas as pd
import zipfile
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import argparse
import logging


class DataExporter:
    """数据导出工具"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        self.exports_dir = os.path.join(data_dir, "exports")
        self.backup_dir = os.path.join(data_dir, "backup")
        
        # 创建必要目录
        for directory in [self.exports_dir, self.backup_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # 配置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def load_data_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """按日期范围加载数据"""
        all_data = []
        
        if not os.path.exists(self.raw_dir):
            return pd.DataFrame()
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        for filename in os.listdir(self.raw_dir):
            if not filename.endswith('.json') or 'zhihu_hot' not in filename:
                continue
                
            try:
                # 从文件名提取日期
                date_str = filename.split('_')[2][:8]  # zhihu_hot_20240101_123456.json
                file_date = datetime.strptime(date_str, '%Y%m%d')
                
                if start_dt <= file_date <= end_dt:
                    filepath = os.path.join(self.raw_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        all_data.extend(data)
                        
            except Exception as e:
                self.logger.warning(f"跳过文件 {filename}: {e}")
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        
        # 数据类型转换
        if 'crawl_time' in df.columns:
            df['crawl_time'] = pd.to_datetime(df['crawl_time'])
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            
        return df
    
    def export_to_excel(self, df: pd.DataFrame, filename: str) -> str:
        """导出到Excel文件"""
        filepath = os.path.join(self.exports_dir, f"{filename}.xlsx")
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 主数据表
            df.to_excel(writer, sheet_name='热榜数据', index=False)
            
            # 统计表
            if not df.empty:
                stats_data = []
                
                # 基础统计
                stats_data.append(['总记录数', len(df)])
                stats_data.append(['唯一问题数', df['question_hash'].nunique() if 'question_hash' in df.columns else 'N/A'])
                stats_data.append(['数据日期范围', f"{df['date'].min()} 至 {df['date'].max()}" if 'date' in df.columns else 'N/A'])
                
                # 排名统计
                if 'rank' in df.columns:
                    stats_data.append(['平均排名', round(df['rank'].mean(), 2)])
                    stats_data.append(['排名范围', f"{df['rank'].min()}-{df['rank'].max()}"])
                
                # 回答数统计
                if 'answer_count' in df.columns and df['answer_count'].sum() > 0:
                    stats_data.append(['平均回答数', round(df['answer_count'].mean(), 2)])
                    stats_data.append(['最多回答数', df['answer_count'].max()])
                
                stats_df = pd.DataFrame(stats_data, columns=['指标', '值'])
                stats_df.to_excel(writer, sheet_name='统计信息', index=False)
                
                # 热门标签
                if 'question_tags' in df.columns:
                    all_tags = []
                    for tags in df['question_tags'].dropna():
                        if isinstance(tags, list):
                            all_tags.extend(tags)
                    
                    if all_tags:
                        tag_counts = pd.Series(all_tags).value_counts().head(20)
                        tag_df = pd.DataFrame({'标签': tag_counts.index, '出现次数': tag_counts.values})
                        tag_df.to_excel(writer, sheet_name='热门标签', index=False)
        
        self.logger.info(f"数据已导出到Excel: {filepath}")
        return filepath
    
    def export_to_csv(self, df: pd.DataFrame, filename: str) -> str:
        """导出到CSV文件"""
        filepath = os.path.join(self.exports_dir, f"{filename}.csv")
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        self.logger.info(f"数据已导出到CSV: {filepath}")
        return filepath
    
    def export_summary_report(self, df: pd.DataFrame, filename: str) -> str:
        """导出汇总报告"""
        filepath = os.path.join(self.exports_dir, f"{filename}_summary.json")
        
        if df.empty:
            summary = {"error": "没有数据可汇总"}
        else:
            summary = {
                "export_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "data_overview": {
                    "total_records": len(df),
                    "unique_questions": df['question_hash'].nunique() if 'question_hash' in df.columns else None,
                    "date_range": {
                        "start": df['date'].min().strftime('%Y-%m-%d') if 'date' in df.columns else None,
                        "end": df['date'].max().strftime('%Y-%m-%d') if 'date' in df.columns else None
                    }
                }
            }
            
            # 排名分析
            if 'rank' in df.columns:
                summary["rank_analysis"] = {
                    "average_rank": round(df['rank'].mean(), 2),
                    "rank_distribution": df['rank'].value_counts().head(10).to_dict()
                }
            
            # 热度分析
            if 'answer_count' in df.columns and df['answer_count'].sum() > 0:
                summary["answer_analysis"] = {
                    "average_answers": round(df['answer_count'].mean(), 2),
                    "median_answers": df['answer_count'].median(),
                    "max_answers": int(df['answer_count'].max())
                }
            
            # 标签分析
            if 'question_tags' in df.columns:
                all_tags = []
                for tags in df['question_tags'].dropna():
                    if isinstance(tags, list):
                        all_tags.extend(tags)
                
                if all_tags:
                    tag_counts = pd.Series(all_tags).value_counts().head(15)
                    summary["tag_analysis"] = {
                        "total_unique_tags": len(set(all_tags)),
                        "popular_tags": tag_counts.to_dict()
                    }
            
            # 时间趋势
            if 'date' in df.columns:
                daily_counts = df.groupby('date').size()
                summary["time_trends"] = {
                    "daily_counts": {str(date): int(count) for date, count in daily_counts.items()},
                    "average_daily_items": round(daily_counts.mean(), 2)
                }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        
        self.logger.info(f"汇总报告已导出: {filepath}")
        return filepath
    
    def create_data_package(self, start_date: str, end_date: str, formats: List[str] = None) -> str:
        """创建数据包（包含多种格式）"""
        if formats is None:
            formats = ['excel', 'csv', 'json']
        
        df = self.load_data_by_date_range(start_date, end_date)
        
        if df.empty:
            self.logger.warning(f"指定日期范围 {start_date} 到 {end_date} 没有数据")
            return None
        
        package_name = f"zhihu_data_{start_date}_to_{end_date}"
        package_dir = os.path.join(self.exports_dir, package_name)
        os.makedirs(package_dir, exist_ok=True)
        
        exported_files = []
        
        # 导出不同格式
        if 'excel' in formats:
            excel_path = self.export_to_excel(df, os.path.join(package_name, "data"))
            exported_files.append(excel_path)
        
        if 'csv' in formats:
            csv_path = self.export_to_csv(df, os.path.join(package_name, "data"))
            exported_files.append(csv_path)
        
        if 'json' in formats:
            json_path = os.path.join(package_dir, "data.json")
            df.to_json(json_path, orient='records', force_ascii=False, indent=2)
            exported_files.append(json_path)
        
        # 导出汇总报告
        summary_path = self.export_summary_report(df, os.path.join(package_name, "summary"))
        exported_files.append(summary_path)
        
        # 创建ZIP包
        zip_path = os.path.join(self.exports_dir, f"{package_name}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in exported_files:
                if os.path.exists(file_path):
                    arcname = os.path.relpath(file_path, self.exports_dir)
                    zipf.write(file_path, arcname)
        
        # 清理临时目录
        shutil.rmtree(package_dir)
        
        self.logger.info(f"数据包已创建: {zip_path}")
        return zip_path


class BackupManager:
    """备份管理工具"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.backup_dir = os.path.join(data_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def create_full_backup(self) -> str:
        """创建完整备份"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"full_backup_{timestamp}"
        backup_path = os.path.join(self.backup_dir, f"{backup_name}.zip")
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.data_dir):
                # 跳过备份目录本身
                if 'backup' in root:
                    continue
                    
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.data_dir)
                    zipf.write(file_path, arcname)
        
        self.logger.info(f"完整备份已创建: {backup_path}")
        return backup_path
    
    def create_incremental_backup(self, days: int = 1) -> str:
        """创建增量备份（最近N天的数据）"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"incremental_backup_{days}days_{timestamp}"
        backup_path = os.path.join(self.backup_dir, f"{backup_name}.zip")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 备份原始数据
            raw_dir = os.path.join(self.data_dir, "raw")
            if os.path.exists(raw_dir):
                for filename in os.listdir(raw_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(raw_dir, filename)
                        
                        # 检查文件修改时间
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_mtime >= cutoff_date:
                            zipf.write(file_path, f"raw/{filename}")
            
            # 备份分析结果和报告
            for subdir in ["analysis", "reports"]:
                subdir_path = os.path.join(self.data_dir, subdir)
                if os.path.exists(subdir_path):
                    for filename in os.listdir(subdir_path):
                        file_path = os.path.join(subdir_path, filename)
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_mtime >= cutoff_date:
                            zipf.write(file_path, f"{subdir}/{filename}")
        
        self.logger.info(f"增量备份已创建: {backup_path}")
        return backup_path
    
    def cleanup_old_backups(self, keep_days: int = 30):
        """清理旧备份文件"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        cleaned_count = 0
        
        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.zip'):
                file_path = os.path.join(self.backup_dir, filename)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_mtime < cutoff_date:
                    os.remove(file_path)
                    cleaned_count += 1
                    self.logger.info(f"已删除旧备份: {filename}")
        
        self.logger.info(f"清理完成，删除了 {cleaned_count} 个旧备份文件")
    
    def list_backups(self) -> List[Dict]:
        """列出所有备份文件"""
        backups = []
        
        if not os.path.exists(self.backup_dir):
            return backups
        
        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.zip'):
                file_path = os.path.join(self.backup_dir, filename)
                stat = os.stat(file_path)
                
                backups.append({
                    'filename': filename,
                    'size_mb': round(stat.st_size / (1024*1024), 2),
                    'created_time': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'full' if 'full_backup' in filename else 'incremental'
                })
        
        # 按创建时间排序
        backups.sort(key=lambda x: x['created_time'], reverse=True)
        return backups


def main():
    """命令行工具主函数"""
    parser = argparse.ArgumentParser(description="知乎热榜数据导出和备份工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 导出命令
    export_parser = subparsers.add_parser('export', help='数据导出')
    export_parser.add_argument('--start', required=True, help='开始日期 (YYYY-MM-DD)')
    export_parser.add_argument('--end', required=True, help='结束日期 (YYYY-MM-DD)')
    export_parser.add_argument('--format', choices=['excel', 'csv', 'json', 'all'], 
                              default='all', help='导出格式')
    export_parser.add_argument('--output', help='输出文件名（不含扩展名）')
    
    # 备份命令
    backup_parser = subparsers.add_parser('backup', help='数据备份')
    backup_parser.add_argument('--type', choices=['full', 'incremental'], 
                              default='incremental', help='备份类型')
    backup_parser.add_argument('--days', type=int, default=7, 
                              help='增量备份天数（默认7天）')
    
    # 清理命令
    cleanup_parser = subparsers.add_parser('cleanup', help='清理旧备份')
    cleanup_parser.add_argument('--keep-days', type=int, default=30,
                               help='保留天数（默认30天）')
    
    # 列表命令
    list_parser = subparsers.add_parser('list', help='列出备份文件')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'export':
            exporter = DataExporter()
            
            if args.format == 'all':
                # 创建数据包
                package_path = exporter.create_data_package(
                    args.start, args.end, ['excel', 'csv', 'json']
                )
                if package_path:
                    print(f"✓ 数据包已创建: {package_path}")
                else:
                    print("✗ 导出失败，指定日期范围内没有数据")
            else:
                # 单一格式导出
                df = exporter.load_data_by_date_range(args.start, args.end)
                if df.empty:
                    print("✗ 指定日期范围内没有数据")
                    return
                
                filename = args.output or f"zhihu_data_{args.start}_to_{args.end}"
                
                if args.format == 'excel':
                    path = exporter.export_to_excel(df, filename)
                elif args.format == 'csv':
                    path = exporter.export_to_csv(df, filename)
                elif args.format == 'json':
                    path = os.path.join(exporter.exports_dir, f"{filename}.json")
                    df.to_json(path, orient='records', force_ascii=False, indent=2)
                
                print(f"✓ 数据已导出: {path}")
        
        elif args.command == 'backup':
            manager = BackupManager()
            
            if args.type == 'full':
                backup_path = manager.create_full_backup()
            else:
                backup_path = manager.create_incremental_backup(args.days)
            
            print(f"✓ 备份已创建: {backup_path}")
        
        elif args.command == 'cleanup':
            manager = BackupManager()
            manager.cleanup_old_backups(args.keep_days)
            print(f"✓ 已清理超过 {args.keep_days} 天的旧备份")
        
        elif args.command == 'list':
            manager = BackupManager()
            backups = manager.list_backups()
            
            if not backups:
                print("没有找到备份文件")
            else:
                print("\n备份文件列表:")
                print("-" * 80)
                print(f"{'文件名':<30} {'类型':<12} {'大小(MB)':<10} {'创建时间':<20}")
                print("-" * 80)
                
                for backup in backups:
                    print(f"{backup['filename']:<30} {backup['type']:<12} "
                          f"{backup['size_mb']:<10} {backup['created_time']:<20}")
    
    except Exception as e:
        print(f"执行失败: {e}")


if __name__ == "__main__":
    main()