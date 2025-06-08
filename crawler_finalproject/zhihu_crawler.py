#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知乎热榜爬虫系统 - 增强版
功能：定时任务、数据分析、去重、扩展字段采集
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import time
import json
import os
import numpy as np
import pickle
import hashlib
import re
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Optional, Tuple
import logging

# 配置matplotlib中文字体
# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300

class EnhancedZhihuCrawler:
    """增强版知乎爬虫 - 支持定时任务、数据分析、去重等功能"""
    
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.cookie_file = os.path.join(data_dir, "zhihu_cookies.pkl")
        self.history_file = os.path.join(data_dir, "crawl_history.json")
        self.duplicate_file = os.path.join(data_dir, "question_hashes.json")
        
        # 创建必要目录
        for subdir in ["raw", "processed", "analysis", "reports"]:
            os.makedirs(os.path.join(data_dir, subdir), exist_ok=True)
        
        # 配置日志
        self._setup_logging()
        
        # 初始化去重数据
        self.question_hashes = self._load_question_hashes()
        
        self.driver = None
        
    def _setup_logging(self):
        """配置日志系统"""
        log_dir = os.path.join(self.data_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, f"crawler_{datetime.now().strftime('%Y%m%d')}.log")),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_question_hashes(self) -> set:
        """加载已知问题的哈希值用于去重"""
        if os.path.exists(self.duplicate_file):
            try:
                with open(self.duplicate_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()
    
    def _save_question_hashes(self):
        """保存问题哈希值"""
        with open(self.duplicate_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.question_hashes), f, ensure_ascii=False, indent=2)
    
    def _generate_question_hash(self, title: str, url: str) -> str:
        """生成问题的唯一标识哈希"""
        # 提取问题ID
        question_id = re.search(r'/question/(\d+)', url)
        if question_id:
            return f"q_{question_id.group(1)}"
        else:
            # 如果没有问题ID，使用标题哈希
            return hashlib.md5(title.encode('utf-8')).hexdigest()
    
    def setup_driver(self):
        """设置Chrome驱动"""
        options = Options()
        
        # 基本反检测设置
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 性能优化
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # 静默模式（定时任务时使用）
        if hasattr(self, 'headless') and self.headless:
            options.add_argument('--headless')
        
        # User-Agent
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.logger.info("Chrome驱动启动成功")
    
    def load_cookies(self) -> bool:
        """加载Cookie"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'rb') as f:
                    cookies = pickle.load(f)
                
                # 访问主页设置域
                self.driver.get("https://www.zhihu.com")
                time.sleep(2)
                
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except:
                        pass
                
                self.logger.info("Cookie加载成功")
                return True
            except Exception as e:
                self.logger.error(f"Cookie加载失败: {e}")
        return False
    
    def check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            self.driver.get("https://www.zhihu.com/hot")
            time.sleep(3)
            
            # 检查是否需要登录
            current_url = self.driver.current_url
            if "signin" in current_url or "login" in current_url:
                return False
            
            # 检查页面是否正常加载
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div, section, a"))
                )
                return True
            except:
                return False
                
        except Exception as e:
            self.logger.error(f"检查登录状态失败: {e}")
            return False
    
    def extract_detailed_info(self, url: str) -> Dict:
        """提取问题详细信息"""
        details = {
            'answer_count': 0,
            'follower_count': 0,
            'view_count': 0,
            'question_tags': [],
            'created_time': None
        }
        
        try:
            # 打开新标签页
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            time.sleep(2)
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 提取回答数
            try:
                answer_elem = self.driver.find_element(By.CSS_SELECTOR, 
                    "[class*='NumberBoard-itemValue'], [class*='List-headerText'], .NumberBoard-value")
                answer_text = answer_elem.text
                answer_match = re.search(r'(\d+)', answer_text)
                if answer_match:
                    details['answer_count'] = int(answer_match.group(1))
            except:
                pass
            
            # 提取关注数
            try:
                follower_elems = self.driver.find_elements(By.CSS_SELECTOR, 
                    "[class*='NumberBoard-itemValue'], .NumberBoard-value")
                for elem in follower_elems:
                    text = elem.text
                    if '关注' in elem.find_element(By.XPATH, "..").text:
                        follower_match = re.search(r'(\d+)', text)
                        if follower_match:
                            details['follower_count'] = int(follower_match.group(1))
                            break
            except:
                pass
            
            # 提取浏览数（通常在问题描述附近）
            try:
                view_elem = self.driver.find_element(By.CSS_SELECTOR, 
                    "[class*='ContentItem-meta'], [class*='QuestionHeader-detail']")
                view_text = view_elem.text
                view_match = re.search(r'(\d+(?:,\d+)*)\s*次浏览', view_text)
                if view_match:
                    details['view_count'] = int(view_match.group(1).replace(',', ''))
            except:
                pass
            
            # 提取标签
            try:
                tag_elems = self.driver.find_elements(By.CSS_SELECTOR, 
                    ".QuestionHeader-tags .Tag, [class*='QuestionTopic'] .Tag")
                for tag_elem in tag_elems:
                    tag_text = tag_elem.text.strip()
                    if tag_text and tag_text not in details['question_tags']:
                        details['question_tags'].append(tag_text)
            except:
                pass
            
            # 关闭当前标签页
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            
        except Exception as e:
            self.logger.error(f"提取详细信息失败 {url}: {e}")
            # 确保切换回主窗口
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
        
        return details
    
    def crawl_hot_list(self, extract_details=True) -> List[Dict]:
        """爬取热榜数据（增强版）"""
        self.logger.info("开始爬取热榜数据")
        
        if "hot" not in self.driver.current_url:
            self.driver.get("https://www.zhihu.com/hot")
            time.sleep(3)
        
        hot_items = []
        new_items_count = 0
        
        try:
            # 等待页面加载
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 多种选择器策略
            selectors = [
                "div.HotItem",
                "section.HotItem", 
                "[class*='HotItem']",
                "div[data-za-detail-view-id]"
            ]
            
            elements = []
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.logger.info(f"使用选择器 '{selector}' 找到 {len(elements)} 个元素")
                        break
                except:
                    continue
            
            # 备用方案：通过链接查找
            if not elements:
                self.logger.info("使用备用方案：通过链接查找")
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                question_links = [link for link in all_links 
                                if link.get_attribute("href") and "/question/" in link.get_attribute("href")]
                
                for idx, link in enumerate(question_links[:50], 1):
                    try:
                        title = link.text.strip()
                        url = link.get_attribute('href')
                        
                        if not title or not url:
                            continue
                        
                        # 去重检查
                        question_hash = self._generate_question_hash(title, url)
                        if question_hash in self.question_hashes:
                            continue
                        
                        # 基础数据
                        item = {
                            'rank': idx,
                            'title': title,
                            'url': url,
                            'question_hash': question_hash,
                            'heat_value': None,
                            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'date': datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        # 提取详细信息
                        if extract_details and idx <= 20:  # 只对前20条提取详细信息
                            self.logger.info(f"正在提取第 {idx} 条详细信息...")
                            details = self.extract_detailed_info(url)
                            item.update(details)
                            time.sleep(1)  # 避免请求过快
                        
                        hot_items.append(item)
                        self.question_hashes.add(question_hash)
                        new_items_count += 1
                        
                        self.logger.info(f"提取第 {idx} 条: {title[:50]}...")
                        
                    except Exception as e:
                        self.logger.error(f"处理第 {idx} 条时出错: {e}")
                        continue
            else:
                # 解析标准热榜元素
                for idx, element in enumerate(elements[:50], 1):
                    try:
                        item = self._parse_hot_item_enhanced(element, idx, extract_details and idx <= 20)
                        if item and item.get('title'):
                            # 去重检查
                            question_hash = item.get('question_hash')
                            if question_hash and question_hash not in self.question_hashes:
                                hot_items.append(item)
                                self.question_hashes.add(question_hash)
                                new_items_count += 1
                                self.logger.info(f"解析第 {idx} 条: {item['title'][:50]}...")
                            
                    except Exception as e:
                        self.logger.error(f"解析第 {idx} 条时出错: {e}")
                        
        except Exception as e:
            self.logger.error(f"爬取过程出错: {e}")
        
        self.logger.info(f"本次爬取完成，新增 {new_items_count} 条数据，总计 {len(hot_items)} 条")
        return hot_items
    
    def _parse_hot_item_enhanced(self, element, rank: int, extract_details: bool = True) -> Optional[Dict]:
        """解析热榜项（增强版）"""
        item = {
            'rank': rank,
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        try:
            # 提取标题和链接
            title_elem = element.find_element(By.CSS_SELECTOR, "h2, [class*='title'], a")
            item['title'] = title_elem.text.strip()
            
            link_elem = element.find_element(By.CSS_SELECTOR, "a[href]")
            item['url'] = link_elem.get_attribute('href')
            
            # 生成问题哈希
            item['question_hash'] = self._generate_question_hash(item['title'], item['url'])
            
            # 提取热度值
            try:
                heat_elem = element.find_element(By.CSS_SELECTOR, 
                    "[class*='metrics'], [class*='hot'], [class*='HotItem-metrics']")
                item['heat_value'] = heat_elem.text.strip()
            except:
                item['heat_value'] = None
            
            # 提取详细信息
            if extract_details and item.get('url'):
                details = self.extract_detailed_info(item['url'])
                item.update(details)
                time.sleep(1)  # 避免请求过快
                
        except Exception as e:
            self.logger.error(f"解析热榜项失败: {e}")
            return None
            
        return item if 'title' in item else None
    
    def save_data(self, data: List[Dict], filename_prefix: str = "zhihu_hot"):
        """保存数据"""
        if not data:
            self.logger.warning("没有数据可保存")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存原始数据
        raw_filename = f"{filename_prefix}_{timestamp}.json"
        raw_filepath = os.path.join(self.data_dir, "raw", raw_filename)
        
        with open(raw_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 保存去重哈希
        self._save_question_hashes()
        
        # 更新爬取历史
        self._update_crawl_history(len(data), raw_filepath)
        
        self.logger.info(f"数据已保存到: {raw_filepath}")
        return raw_filepath
    
    def _update_crawl_history(self, count: int, filepath: str):
        """更新爬取历史记录"""
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                pass
        
        history.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'count': count,
            'filepath': filepath
        })
        
        # 只保留最近100条记录
        history = history[-100:]
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def run_single_crawl(self, extract_details: bool = True, headless: bool = False) -> Optional[str]:
        """执行单次爬取"""
        self.headless = headless
        
        try:
            self.setup_driver()
            
            # 加载Cookie并检查登录状态
            if self.load_cookies():
                self.driver.refresh()
                time.sleep(3)
                
                if not self.check_login_status():
                    self.logger.error("登录状态检查失败，请重新登录")
                    return None
            else:
                self.logger.error("无法加载Cookie，请先手动登录")
                return None
            
            # 执行爬取
            hot_items = self.crawl_hot_list(extract_details)
            
            if hot_items:
                filepath = self.save_data(hot_items)
                return filepath
            else:
                self.logger.warning("未能爬取到数据")
                return None
                
        except Exception as e:
            self.logger.error(f"爬取过程出错: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()


class HotListAnalyzer:
    """热榜数据分析器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        self.analysis_dir = os.path.join(data_dir, "analysis")
        self.reports_dir = os.path.join(data_dir, "reports")
        
        # 确保目录存在
        for directory in [self.analysis_dir, self.reports_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def load_all_data(self) -> pd.DataFrame:
        """加载所有历史数据"""
        all_data = []
        
        if not os.path.exists(self.raw_dir):
            return pd.DataFrame()
        
        for filename in os.listdir(self.raw_dir):
            if filename.endswith('.json') and 'zhihu_hot' in filename:
                filepath = os.path.join(self.raw_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        all_data.extend(data)
                except Exception as e:
                    print(f"加载文件失败 {filename}: {e}")
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        
        # 数据类型转换
        if 'crawl_time' in df.columns:
            df['crawl_time'] = pd.to_datetime(df['crawl_time'])
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        return df
    
    def analyze_hot_trends(self, days: int = 7) -> Dict:
        """分析热度趋势"""
        df = self.load_all_data()
        
        if df.empty:
            return {"error": "没有可分析的数据"}
        
        # 过滤最近N天的数据
        cutoff_date = datetime.now() - timedelta(days=days)
        if 'crawl_time' in df.columns:
            recent_df = df[df['crawl_time'] >= cutoff_date]
        else:
            recent_df = df
        
        analysis = {
            'total_questions': len(recent_df['question_hash'].unique()) if 'question_hash' in recent_df.columns else len(recent_df),
            'total_records': len(recent_df),
            'date_range': {
                'start': recent_df['crawl_time'].min().strftime('%Y-%m-%d') if 'crawl_time' in recent_df.columns else 'N/A',
                'end': recent_df['crawl_time'].max().strftime('%Y-%m-%d') if 'crawl_time' in recent_df.columns else 'N/A'
            }
        }
        
        # 每日问题数量趋势
        if 'date' in recent_df.columns:
            daily_counts = recent_df.groupby('date').size()
            analysis['daily_trends'] = daily_counts.to_dict()
        
        # 热门标签分析
        if 'question_tags' in recent_df.columns:
            all_tags = []
            for tags in recent_df['question_tags'].dropna():
                if isinstance(tags, list):
                    all_tags.extend(tags)
            
            if all_tags:
                tag_counts = pd.Series(all_tags).value_counts().head(10)
                analysis['popular_tags'] = tag_counts.to_dict()
        
        # 回答数分析
        if 'answer_count' in recent_df.columns:
            answer_stats = recent_df['answer_count'].describe()
            analysis['answer_stats'] = {
                'mean': round(answer_stats['mean'], 2),
                'median': answer_stats['50%'],
                'max': answer_stats['max'],
                'min': answer_stats['min']
            }
        
        # 排名稳定性分析（同一问题在不同时间的排名变化）
        if 'question_hash' in recent_df.columns and 'rank' in recent_df.columns:
            rank_stability = recent_df.groupby('question_hash')['rank'].agg(['count', 'mean', 'std']).reset_index()
            rank_stability = rank_stability[rank_stability['count'] > 1]  # 只分析出现多次的问题
            
            if not rank_stability.empty:
                analysis['rank_stability'] = {
                    'stable_questions': len(rank_stability[rank_stability['std'] < 5]),  # 排名变化小于5
                    'volatile_questions': len(rank_stability[rank_stability['std'] >= 10]),  # 排名变化大于10
                    'avg_rank_change': round(rank_stability['std'].mean(), 2)
                }
        
        return analysis
    

    def generate_trend_charts(self, days: int = 7):
        """生成6个独立的分析图表"""
        df = self.load_all_data()
        
        if df.empty:
            print("❌ 没有数据可用于生成图表")
            return None
        
        # 过滤数据
        cutoff_date = datetime.now() - timedelta(days=days)
        if 'crawl_time' in df.columns:
            recent_df = df[df['crawl_time'] >= cutoff_date]
        else:
            recent_df = df
        
        if recent_df.empty:
            print(f"❌ 最近{days}天没有数据")
            return None
        
        print(f"📊 正在生成最近{days}天的6个独立分析图表...")
        
        # 设置matplotlib参数
        plt.rcParams.update({
            'font.sans-serif': ['Microsoft YaHei', 'SimHei', 'Arial', 'DejaVu Sans'],
            'axes.unicode_minus': False,
            'figure.dpi': 100,
            'savefig.dpi': 300,
            'font.size': 14,
            'axes.titlesize': 18,
            'axes.labelsize': 14,
            'xtick.labelsize': 12,
            'ytick.labelsize': 12,
            'legend.fontsize': 12
        })
        
        # 颜色配置
        colors = {
            'primary': '#3498db',
            'secondary': '#e74c3c', 
            'success': '#2ecc71',
            'warning': '#f39c12',
            'info': '#9b59b6',
            'dark': '#34495e'
        }
        
        chart_files = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # =================== 图表1: 每日数据采集趋势 ===================
        plt.figure(figsize=(12, 8))
        if 'date' in recent_df.columns:
            daily_counts = recent_df.groupby('date').size()
            
            plt.plot(daily_counts.index, daily_counts.values, 
                    marker='o', linewidth=4, markersize=12, 
                    color=colors['primary'], markerfacecolor='white', 
                    markeredgewidth=3, markeredgecolor=colors['primary'],
                    label='每日问题数')
            
            plt.fill_between(daily_counts.index, daily_counts.values, 
                            alpha=0.3, color=colors['primary'])
            
            # 添加趋势线
            if len(daily_counts) > 1:
                z = np.polyfit(range(len(daily_counts)), daily_counts.values, 1)
                p = np.poly1d(z)
                plt.plot(daily_counts.index, p(range(len(daily_counts))), 
                        "--", alpha=0.8, color=colors['secondary'], linewidth=3,
                        label='趋势线')
            
            # 标注最高点
            max_idx = daily_counts.idxmax()
            max_val = daily_counts.max()
            plt.annotate(f'峰值\n{max_val}个问题', 
                        xy=(max_idx, max_val),
                        xytext=(max_idx, max_val + max_val*0.1),
                        arrowprops=dict(arrowstyle='->', color=colors['secondary'], lw=2),
                        fontweight='bold', ha='center', fontsize=12,
                        bbox=dict(boxstyle="round,pad=0.5", facecolor='yellow', alpha=0.8))
            
            plt.title(f'每日数据采集趋势 - 最近{days}天', fontweight='bold', fontsize=20, pad=20)
            plt.xlabel('日期', fontweight='bold')
            plt.ylabel('问题数量', fontweight='bold')
            plt.grid(True, alpha=0.3, linestyle='--')
            plt.legend()
            plt.xticks(rotation=45)
        else:
            plt.text(0.5, 0.5, '暂无日期数据', transform=plt.gca().transAxes,
                    ha='center', va='center', fontsize=20, color='gray')
            plt.title(f'每日数据采集趋势 - 最近{days}天', fontweight='bold', fontsize=20, pad=20)
        
        plt.tight_layout()
        chart1_path = os.path.join(self.analysis_dir, f'chart1_daily_trend_{timestamp}.png')
        plt.savefig(chart1_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        chart_files.append(chart1_path)
        print(f"✅ 图表1已保存: {chart1_path}")
        
        # =================== 图表2: 排名区间分布 ===================
        plt.figure(figsize=(12, 8))
        if 'rank' in recent_df.columns:
            rank_ranges = ['1-10名\n(热门)', '11-20名\n(优秀)', '21-30名\n(良好)', '31-40名\n(一般)', '41-50名\n(普通)']
            range_counts = []
            
            for i in range(5):
                start = i * 10 + 1
                end = (i + 1) * 10
                count = recent_df[recent_df['rank'].between(start, end)]['rank'].count()
                range_counts.append(count)
            
            colors_list = [colors['success'], colors['primary'], colors['warning'], 
                        colors['secondary'], colors['info']]
            
            bars = plt.bar(rank_ranges, range_counts, color=colors_list, 
                        alpha=0.8, edgecolor='white', linewidth=3)
            
            # 添加数值标签
            for bar, count in zip(bars, range_counts):
                if count > 0:
                    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                            f'{count}个', ha='center', va='bottom', fontweight='bold', fontsize=14)
            
            plt.title(f'排名区间分布 - 最近{days}天', fontweight='bold', fontsize=20, pad=20)
            plt.xlabel('排名区间', fontweight='bold')
            plt.ylabel('问题数量', fontweight='bold')
            plt.grid(True, alpha=0.3, axis='y')
        else:
            plt.text(0.5, 0.5, '暂无排名数据', transform=plt.gca().transAxes,
                    ha='center', va='center', fontsize=20, color='gray')
            plt.title(f'排名区间分布 - 最近{days}天', fontweight='bold', fontsize=20, pad=20)
        
        plt.tight_layout()
        chart2_path = os.path.join(self.analysis_dir, f'chart2_rank_distribution_{timestamp}.png')
        plt.savefig(chart2_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        chart_files.append(chart2_path)
        print(f"✅ 图表2已保存: {chart2_path}")
        
        # =================== 图表3: 回答数分布分析 ===================
        plt.figure(figsize=(12, 8))
        if 'answer_count' in recent_df.columns and not recent_df['answer_count'].isna().all():
            answer_counts = recent_df['answer_count'].dropna()
            if not answer_counts.empty and answer_counts.sum() > 0:
                # 绘制直方图
                n, bins, patches = plt.hist(answer_counts, bins=30, 
                                        color=colors['success'], alpha=0.7, 
                                        edgecolor='white', linewidth=1)
                
                # 添加统计线
                mean_val = answer_counts.mean()
                median_val = answer_counts.median()
                plt.axvline(mean_val, color=colors['secondary'], linestyle='--', 
                        linewidth=4, label=f'均值: {mean_val:.1f}个回答')
                plt.axvline(median_val, color=colors['warning'], linestyle='--', 
                        linewidth=4, label=f'中位数: {median_val:.1f}个回答')
                
                # 添加统计信息
                stats_text = f'总问题数: {len(answer_counts)}\n最多回答: {answer_counts.max()}个\n最少回答: {answer_counts.min()}个'
                plt.text(0.98, 0.98, stats_text, transform=plt.gca().transAxes,
                        verticalalignment='top', horizontalalignment='right',
                        bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.8),
                        fontsize=12, fontweight='bold')
                
                plt.title(f'回答数分布分析 - 最近{days}天', fontweight='bold', fontsize=20, pad=20)
                plt.xlabel('回答数', fontweight='bold')
                plt.ylabel('问题数量', fontweight='bold')
                plt.legend(loc='upper right')
                plt.grid(True, alpha=0.3)
            else:
                plt.text(0.5, 0.5, '暂无有效回答数据', transform=plt.gca().transAxes,
                        ha='center', va='center', fontsize=20, color='gray')
        else:
            plt.text(0.5, 0.5, '暂无回答数据', transform=plt.gca().transAxes,
                    ha='center', va='center', fontsize=20, color='gray')
            plt.title(f'回答数分布分析 - 最近{days}天', fontweight='bold', fontsize=20, pad=20)
        
        plt.tight_layout()
        chart3_path = os.path.join(self.analysis_dir, f'chart3_answer_distribution_{timestamp}.png')
        plt.savefig(chart3_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        chart_files.append(chart3_path)
        print(f"✅ 图表3已保存: {chart3_path}")
        
        # =================== 图表4: 热门话题标签 ===================
        plt.figure(figsize=(12, 10))
        if 'question_tags' in recent_df.columns:
            all_tags = []
            for tags in recent_df['question_tags'].dropna():
                if isinstance(tags, list):
                    all_tags.extend(tags)
            
            if all_tags:
                tag_counts = pd.Series(all_tags).value_counts().head(15)
                
                # 创建渐变色
                colors_gradient = plt.cm.Set3(np.linspace(0, 1, len(tag_counts)))
                
                bars = plt.barh(range(len(tag_counts)), tag_counts.values, 
                            color=colors_gradient, alpha=0.8, 
                            edgecolor='white', linewidth=2)
                
                plt.yticks(range(len(tag_counts)), tag_counts.index, fontsize=12)
                plt.title(f'热门话题标签排行榜 - 最近{days}天', fontweight='bold', fontsize=20, pad=20)
                plt.xlabel('出现次数', fontweight='bold')
                plt.grid(True, alpha=0.3, axis='x')
                
                # 添加数值标签
                for i, (bar, count) in enumerate(zip(bars, tag_counts.values)):
                    plt.text(bar.get_width() + max(tag_counts.values) * 0.01, 
                            bar.get_y() + bar.get_height()/2,
                            f'{count}次', ha='left', va='center', fontweight='bold', fontsize=11)
                
                # 添加排名标签
                for i, bar in enumerate(bars):
                    plt.text(bar.get_width() * 0.05, bar.get_y() + bar.get_height()/2,
                            f'#{i+1}', ha='left', va='center', fontweight='bold', 
                            fontsize=10, color='white')
            else:
                plt.text(0.5, 0.5, '暂无标签数据', transform=plt.gca().transAxes,
                        ha='center', va='center', fontsize=20, color='gray')
        else:
            plt.text(0.5, 0.5, '暂无标签数据', transform=plt.gca().transAxes,
                    ha='center', va='center', fontsize=20, color='gray')
            plt.title(f'热门话题标签排行榜 - 最近{days}天', fontweight='bold', fontsize=20, pad=20)
        
        plt.tight_layout()
        chart4_path = os.path.join(self.analysis_dir, f'chart4_popular_tags_{timestamp}.png')
        plt.savefig(chart4_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        chart_files.append(chart4_path)
        print(f"✅ 图表4已保存: {chart4_path}")
        
        # =================== 图表5: 24小时活跃度分布 ===================
        plt.figure(figsize=(14, 8))
        if 'crawl_time' in recent_df.columns:
            df_hour = recent_df.copy()
            df_hour['hour'] = df_hour['crawl_time'].dt.hour
            hourly_counts = df_hour.groupby('hour').size()
            
            # 创建24小时完整数据
            full_hours = pd.Series(0, index=range(24))
            full_hours.update(hourly_counts)
            
            # 创建渐变色效果
            colors_hour = []
            max_count = full_hours.max() if full_hours.max() > 0 else 1
            for count in full_hours.values:
                intensity = count / max_count
                colors_hour.append(plt.cm.viridis(intensity))
            
            bars = plt.bar(full_hours.index, full_hours.values, 
                        color=colors_hour, alpha=0.8, 
                        edgecolor='white', linewidth=1.5)
            
            # 标注peak时段
            if not hourly_counts.empty:
                peak_hour = hourly_counts.idxmax()
                peak_count = hourly_counts.max()
                plt.annotate(f'高峰时段\n{peak_hour}:00\n活跃度: {peak_count}', 
                            xy=(peak_hour, peak_count),
                            xytext=(peak_hour+3, peak_count+2),
                            arrowprops=dict(arrowstyle='->', color=colors['secondary'], lw=3),
                            fontweight='bold', ha='center', fontsize=12,
                            bbox=dict(boxstyle="round,pad=0.5", facecolor='yellow', alpha=0.9))
            
            # 时段标注
            time_periods = {
                (0, 6): '深夜时段',
                (6, 12): '上午时段', 
                (12, 18): '下午时段',
                (18, 24): '晚间时段'
            }
            
            for (start, end), period in time_periods.items():
                avg_activity = full_hours[start:end].mean()
                mid_hour = (start + end) // 2
                plt.text(mid_hour, avg_activity + max_count * 0.1, period,
                        ha='center', va='bottom', fontweight='bold', fontsize=10,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.7))
            
            plt.title(f'24小时活跃度分布 - 最近{days}天', fontweight='bold', fontsize=20, pad=20)
            plt.xlabel('小时', fontweight='bold')
            plt.ylabel('活跃度', fontweight='bold')
            plt.xticks(range(0, 24, 2), [f'{h}:00' for h in range(0, 24, 2)])
            plt.grid(True, alpha=0.3, axis='y')
        else:
            plt.text(0.5, 0.5, '暂无时间数据', transform=plt.gca().transAxes,
                    ha='center', va='center', fontsize=20, color='gray')
            plt.title(f'24小时活跃度分布 - 最近{days}天', fontweight='bold', fontsize=20, pad=20)
        
        plt.tight_layout()
        chart5_path = os.path.join(self.analysis_dir, f'chart5_hourly_activity_{timestamp}.png')
        plt.savefig(chart5_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        chart_files.append(chart5_path)
        print(f"✅ 图表5已保存: {chart5_path}")
        
        # =================== 图表6: 数据质量与统计指标 ===================
        plt.figure(figsize=(12, 8))
        
        # 计算指标
        total_records = len(recent_df)
        unique_questions = recent_df['question_hash'].nunique() if 'question_hash' in recent_df.columns else len(recent_df)
        
        # 数据完整率
        completeness_scores = []
        if 'answer_count' in recent_df.columns:
            answer_completeness = (recent_df['answer_count'].notna().sum() / len(recent_df)) * 100
            completeness_scores.append(('回答数完整率', answer_completeness))
        
        if 'question_tags' in recent_df.columns:
            tag_completeness = (recent_df['question_tags'].apply(
                lambda x: len(x) > 0 if isinstance(x, list) else False).sum() / len(recent_df)) * 100
            completeness_scores.append(('标签完整率', tag_completeness))
        
        # 重复率
        duplicate_rate = ((total_records - unique_questions) / total_records * 100) if total_records > 0 else 0
        
        # 绘制圆饼图显示数据质量
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # 左图：数据完整性
        if completeness_scores:
            labels = [item[0] for item in completeness_scores]
            sizes = [item[1] for item in completeness_scores]
            colors_pie = [colors['success'], colors['info']][:len(sizes)]
            
            ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                colors=colors_pie, textprops={'fontsize': 12, 'fontweight': 'bold'})
            ax1.set_title('数据完整性分析', fontweight='bold', fontsize=16, pad=20)
        
        # 右图：关键指标
        metrics = ['总记录数', '独特问题', f'重复率({duplicate_rate:.1f}%)']
        values = [total_records, unique_questions, duplicate_rate]
        colors_metrics = [colors['primary'], colors['success'], colors['warning']]
        
        bars = ax2.bar(metrics, values, color=colors_metrics, 
                    alpha=0.8, edgecolor='white', linewidth=2)
        
        ax2.set_title('关键统计指标', fontweight='bold', fontsize=16, pad=20)
        ax2.set_ylabel('数值', fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # 添加数值标签
        for bar, value, metric in zip(bars, values, metrics):
            if '率' in metric:
                label = f'{value:.1f}%'
            else:
                label = f'{int(value):,}'
            
            ax2.text(bar.get_x() + bar.get_width()/2, 
                    bar.get_height() + max(values) * 0.02,
                    label, ha='center', va='bottom', fontweight='bold', fontsize=12)
        
        plt.suptitle(f'数据质量与统计分析 - 最近{days}天', fontweight='bold', fontsize=20, y=0.95)
        plt.tight_layout()
        chart6_path = os.path.join(self.analysis_dir, f'chart6_data_quality_{timestamp}.png')
        plt.savefig(chart6_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        chart_files.append(chart6_path)
        print(f"✅ 图表6已保存: {chart6_path}")
        
        # 生成汇总信息
        print(f"\n🎉 所有图表生成完成！")
        print(f"📁 保存位置: {self.analysis_dir}")
        print(f"📊 图表列表:")
        for i, chart_file in enumerate(chart_files, 1):
            filename = os.path.basename(chart_file)
            print(f"   {i}. {filename}")
        
        print(f"\n📈 数据概览:")
        print(f"   • 分析周期: {days} 天")
        print(f"   • 总记录数: {total_records:,} 条")
        print(f"   • 独特问题: {unique_questions:,} 个")
        print(f"   • 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return chart_files
    
    def generate_report(self, days: int = 7) -> str:
        """生成分析报告"""
        analysis = self.analyze_hot_trends(days)
        
        if "error" in analysis:
            return analysis["error"]
        
        report_content = f"""
# 知乎热榜数据分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**分析周期**: 最近{days}天

## 📊 数据概览

- **总问题数**: {analysis.get('total_questions', 'N/A')} 个独特问题
- **总记录数**: {analysis.get('total_records', 'N/A')} 条记录
- **数据时间范围**: {analysis.get('date_range', {}).get('start', 'N/A')} 至 {analysis.get('date_range', {}).get('end', 'N/A')}

## 📈 趋势分析

### 每日活跃度
"""
        
        if 'daily_trends' in analysis:
            report_content += "\n| 日期 | 问题数量 |\n|------|----------|\n"
            for date, count in analysis['daily_trends'].items():
                report_content += f"| {date} | {count} |\n"
        
        if 'popular_tags' in analysis:
            report_content += "\n\n### 🏷️ 热门标签\n\n"
            for tag, count in analysis['popular_tags'].items():
                report_content += f"- **{tag}**: {count} 次\n"
        
        if 'answer_stats' in analysis:
            stats = analysis['answer_stats']
            report_content += f"""

### 📝 回答数据统计

- **平均回答数**: {stats['mean']} 个
- **中位数回答数**: {stats['median']} 个  
- **最多回答数**: {stats['max']} 个
- **最少回答数**: {stats['min']} 个
"""
        
        if 'rank_stability' in analysis:
            stability = analysis['rank_stability']
            report_content += f"""

### 📊 排名稳定性分析

- **稳定问题数** (排名变化<5): {stability['stable_questions']} 个
- **波动问题数** (排名变化≥10): {stability['volatile_questions']} 个
- **平均排名变化**: {stability['avg_rank_change']}
"""
        
        # 保存报告
        report_filename = f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = os.path.join(self.reports_dir, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"分析报告已生成: {report_path}")
        return report_path


class ScheduledCrawler:
    """定时任务调度器"""
    
    def __init__(self, data_dir: str = "data"):
        self.crawler = EnhancedZhihuCrawler(data_dir)
        self.analyzer = HotListAnalyzer(data_dir)
        self.scheduler = BlockingScheduler()
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def scheduled_crawl_job(self, extract_details: bool = True):
        """定时爬取任务"""
        self.logger.info("开始执行定时爬取任务")
        
        try:
            filepath = self.crawler.run_single_crawl(extract_details=extract_details, headless=True)
            if filepath:
                self.logger.info(f"定时爬取完成，数据已保存到: {filepath}")
                
                # 每天晚上生成分析报告
                current_hour = datetime.now().hour
                if current_hour == 23:  # 晚上11点生成报告
                    self.logger.info("生成每日分析报告")
                    self.analyzer.generate_report(days=1)
                    
            else:
                self.logger.error("定时爬取失败")
                
        except Exception as e:
            self.logger.error(f"定时任务执行失败: {e}")
    
    def scheduled_analysis_job(self, days: int = 7):
        """定时分析任务"""
        self.logger.info("开始执行定时分析任务")
        
        try:
            # 生成分析报告
            report_path = self.analyzer.generate_report(days=days)
            self.logger.info(f"分析报告已生成: {report_path}")
            
            # 生成图表
            self.analyzer.generate_trend_charts(days=days)
            self.logger.info("趋势图表已生成")
            
        except Exception as e:
            self.logger.error(f"分析任务执行失败: {e}")
    
    def add_crawl_jobs(self):
        """添加爬取任务"""
        # 每2小时爬取一次（基础信息）
        self.scheduler.add_job(
            func=self.scheduled_crawl_job,
            trigger=CronTrigger(minute=0, second=0, hour='*/2'),
            args=[False],  # 不提取详细信息，提高速度
            id='crawl_basic_2h',
            name='每2小时基础爬取',
            misfire_grace_time=300
        )
        
        # 每6小时详细爬取一次（包含详细信息）
        self.scheduler.add_job(
            func=self.scheduled_crawl_job,
            trigger=CronTrigger(minute=30, second=0, hour='*/6'),
            args=[True],  # 提取详细信息
            id='crawl_detailed_6h',
            name='每6小时详细爬取',
            misfire_grace_time=600
        )
        
        self.logger.info("爬取任务已添加")
    
    def add_analysis_jobs(self):
        """添加分析任务"""
        # 每天早上8点生成周报告
        self.scheduler.add_job(
            func=self.scheduled_analysis_job,
            trigger=CronTrigger(hour=8, minute=0, second=0),
            args=[7],  # 7天报告
            id='weekly_analysis',
            name='每日周报告生成',
            misfire_grace_time=3600
        )
        
        # 每周一早上9点生成月报告
        self.scheduler.add_job(
            func=self.scheduled_analysis_job,
            trigger=CronTrigger(day_of_week='mon', hour=9, minute=0, second=0),
            args=[30],  # 30天报告
            id='monthly_analysis',
            name='每周月报告生成',
            misfire_grace_time=3600
        )
        
        self.logger.info("分析任务已添加")
    
    def start_scheduler(self):
        """启动调度器"""
        self.add_crawl_jobs()
        self.add_analysis_jobs()
        
        self.logger.info("定时任务调度器启动")
        self.logger.info("已添加的任务:")
        for job in self.scheduler.get_jobs():
            self.logger.info(f"  - {job.name} (ID: {job.id})")
        
        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            self.logger.info("接收到中断信号，正在关闭调度器...")
            self.scheduler.shutdown()
    
    def run_manual_analysis(self, days: int = 7):
        """手动运行分析"""
        self.logger.info(f"开始手动分析最近{days}天的数据")
        
        # 生成分析报告
        report_path = self.analyzer.generate_report(days=days)
        print(f"\n✓ 分析报告已生成: {report_path}")
        
        # 生成趋势图表
        self.analyzer.generate_trend_charts(days=days)
        print("✓ 趋势图表已生成")
        
        # 显示关键统计信息
        analysis = self.analyzer.analyze_hot_trends(days=days)
        if "error" not in analysis:
            print(f"\n📊 数据统计 (最近{days}天):")
            print(f"  - 总问题数: {analysis.get('total_questions', 'N/A')}")
            print(f"  - 总记录数: {analysis.get('total_records', 'N/A')}")
            
            if 'popular_tags' in analysis:
                print("  - 热门标签:")
                for tag, count in list(analysis['popular_tags'].items())[:5]:
                    print(f"    * {tag}: {count}次")


def main():
    """主函数 - 增强版功能演示"""
    print("="*60)
    print("知乎热榜爬虫系统 - 增强版")
    print("="*60)
    print("功能:")
    print("1. 单次爬取 (基础)")
    print("2. 单次爬取 (详细信息)")
    print("3. 数据分析")
    print("4. 启动定时任务")
    print("5. 生成趋势图表")
    print("6. 退出")
    print("="*60)
    
    crawler = EnhancedZhihuCrawler()
    analyzer = HotListAnalyzer()
    scheduler = ScheduledCrawler()
    
    while True:
        try:
            choice = input("\n请选择功能 (1-6): ").strip()
            
            if choice == '1':
                print("\n开始基础爬取...")
                filepath = crawler.run_single_crawl(extract_details=False)
                if filepath:
                    print(f"✓ 爬取完成，数据已保存到: {filepath}")
                else:
                    print("✗ 爬取失败")
            
            elif choice == '2':
                print("\n开始详细爬取（包含回答数、浏览数等）...")
                filepath = crawler.run_single_crawl(extract_details=True)
                if filepath:
                    print(f"✓ 爬取完成，数据已保存到: {filepath}")
                else:
                    print("✗ 爬取失败")
            
            elif choice == '3':
                days = input("请输入分析天数 (默认7天): ").strip()
                days = int(days) if days.isdigit() else 7
                scheduler.run_manual_analysis(days)
            
            elif choice == '4':
                print("\n启动定时任务调度器...")
                print("任务配置:")
                print("  - 每2小时基础爬取")
                print("  - 每6小时详细爬取") 
                print("  - 每天8点生成周报告")
                print("  - 每周一9点生成月报告")
                print("\n按 Ctrl+C 停止调度器")
                scheduler.start_scheduler()
            
            elif choice == '5':
                days = input("请输入分析天数 (默认7天): ").strip()
                days = int(days) if days.isdigit() else 7
                analyzer.generate_trend_charts(days)
            
            elif choice == '6':
                print("程序退出")
                break
            
            else:
                print("无效选择，请重新输入")
                
        except KeyboardInterrupt:
            print("\n\n程序被中断")
            break
        except Exception as e:
            print(f"发生错误: {e}")


if __name__ == "__main__":
    main()