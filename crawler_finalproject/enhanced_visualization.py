import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300

# 设置seaborn样式
sns.set_style("whitegrid")
sns.set_palette("husl")

class EnhancedDataVisualizer:
    """增强版数据可视化器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        self.analysis_dir = os.path.join(data_dir, "analysis")
        self.reports_dir = os.path.join(data_dir, "reports")
        
        # 确保目录存在
        for directory in [self.analysis_dir, self.reports_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # 颜色配置
        self.colors = {
            'primary': '#3498db',
            'secondary': '#e74c3c',
            'success': '#2ecc71',
            'warning': '#f39c12',
            'info': '#9b59b6',
            'dark': '#34495e',
            'light': '#ecf0f1'
        }
        
        # Plotly主题配置
        self.plotly_theme = {
            'layout': {
                'font': {'family': 'Microsoft YaHei, Arial', 'size': 12},
                'plot_bgcolor': 'white',
                'paper_bgcolor': 'white',
                'colorway': ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e']
            }
        }
    
    def load_all_data(self) -> pd.DataFrame:
        """加载所有历史数据"""
        all_data = []
        
        if not os.path.exists(self.raw_dir):
            print("❌ 数据目录不存在，请先运行爬虫")
            return pd.DataFrame()
        
        json_files = [f for f in os.listdir(self.raw_dir) 
                     if f.endswith('.json') and 'zhihu_hot' in f]
        
        if not json_files:
            print("❌ 未找到数据文件，请先运行爬虫")
            return pd.DataFrame()
        
        print(f"📂 发现 {len(json_files)} 个数据文件，正在加载...")
        
        for filename in json_files:
            filepath = os.path.join(self.raw_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_data.extend(data)
                    else:
                        all_data.append(data)
            except Exception as e:
                print(f"⚠️  加载文件失败 {filename}: {e}")
        
        if not all_data:
            print("❌ 数据文件为空")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        print(f"✅ 成功加载 {len(df)} 条记录")
        
        # 数据预处理
        df = self._preprocess_data(df)
        return df
    
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据预处理"""
        # 时间转换
        if 'crawl_time' in df.columns:
            df['crawl_time'] = pd.to_datetime(df['crawl_time'], errors='coerce')
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # 数值转换
        numeric_columns = ['rank', 'answer_count', 'follower_count', 'view_count']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 标签处理
        if 'question_tags' in df.columns:
            df['question_tags'] = df['question_tags'].apply(
                lambda x: x if isinstance(x, list) else []
            )
        
        # 去除异常值
        if 'rank' in df.columns:
            df = df[df['rank'].between(1, 100)]  # 排名应该在1-100之间
        
        return df
    
    def create_comprehensive_dashboard(self, days: int = 7) -> str:
        """创建综合数据仪表板"""
        df = self.load_all_data()
        
        if df.empty:
            print("❌ 没有数据可视化")
            return None
        
        # 过滤数据
        cutoff_date = datetime.now() - timedelta(days=days)
        if 'crawl_time' in df.columns:
            recent_df = df[df['crawl_time'] >= cutoff_date].copy()
        else:
            recent_df = df.copy()
        
        if recent_df.empty:
            print(f"❌ 最近{days}天没有数据")
            return None
        
        print(f"📊 正在生成最近{days}天的综合分析仪表板...")
        
        # 创建子图布局
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                '📈 数据采集趋势', '🔥 热榜排名分布',
                '💬 回答数分布', '👥 关注度分析',
                '🏷️ 热门话题标签', '⏰ 时段活跃度'
            ),
            specs=[
                [{"secondary_y": True}, {"type": "bar"}],
                [{"type": "histogram"}, {"type": "scatter"}],
                [{"type": "bar"}, {"type": "heatmap"}]
            ],
            vertical_spacing=0.08,
            horizontal_spacing=0.08
        )
        
        # 1. 数据采集趋势
        self._add_data_trend_chart(fig, recent_df, row=1, col=1)
        
        # 2. 热榜排名分布
        self._add_rank_distribution_chart(fig, recent_df, row=1, col=2)
        
        # 3. 回答数分布
        self._add_answer_distribution_chart(fig, recent_df, row=2, col=1)
        
        # 4. 关注度分析
        self._add_follower_analysis_chart(fig, recent_df, row=2, col=2)
        
        # 5. 热门话题标签
        self._add_tag_analysis_chart(fig, recent_df, row=3, col=1)
        
        # 6. 时段活跃度
        self._add_time_heatmap(fig, recent_df, row=3, col=2)
        
        # 设置整体布局
        fig.update_layout(
            title={
                'text': f'🔥 知乎热榜数据分析仪表板 (最近{days}天)',
                'x': 0.5,
                'font': {'size': 20, 'color': self.colors['dark']}
            },
            height=1200,
            showlegend=False,
            **self.plotly_theme['layout']
        )
        
        # 保存图表
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_path = os.path.join(self.analysis_dir, f'dashboard_{timestamp}.html')
        
        # 添加统计信息到HTML
        stats_html = self._generate_stats_html(recent_df, days)
        
        pyo.plot(fig, filename=html_path, auto_open=False, include_plotlyjs=True)
        
        # 在HTML文件开头添加统计信息
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        enhanced_content = content.replace(
            '<body>',
            f'<body>{stats_html}'
        )
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_content)
        
        print(f"✅ 综合仪表板已生成: {html_path}")
        return html_path
    
    def _add_data_trend_chart(self, fig, df: pd.DataFrame, row: int, col: int):
        """添加数据趋势图"""
        if 'date' not in df.columns:
            return
        
        # 每日数据统计
        daily_stats = df.groupby('date').agg({
            'question_hash': 'count',
            'rank': 'mean'
        }).reset_index()
        daily_stats.columns = ['date', 'question_count', 'avg_rank']
        
        # 添加数据量趋势
        fig.add_trace(
            go.Scatter(
                x=daily_stats['date'],
                y=daily_stats['question_count'],
                mode='lines+markers',
                name='每日问题数',
                line=dict(color=self.colors['primary'], width=3),
                marker=dict(size=8),
                hovertemplate='日期: %{x}<br>问题数: %{y}<extra></extra>'
            ),
            row=row, col=col, secondary_y=False
        )
        
        # 添加平均排名趋势
        fig.add_trace(
            go.Scatter(
                x=daily_stats['date'],
                y=daily_stats['avg_rank'],
                mode='lines+markers',
                name='平均排名',
                line=dict(color=self.colors['secondary'], width=2, dash='dash'),
                marker=dict(size=6),
                yaxis='y2',
                hovertemplate='日期: %{x}<br>平均排名: %{y:.1f}<extra></extra>'
            ),
            row=row, col=col, secondary_y=True
        )
        
        fig.update_yaxes(title_text="问题数量", row=row, col=col, secondary_y=False)
        fig.update_yaxes(title_text="平均排名", row=row, col=col, secondary_y=True)
    
    def _add_rank_distribution_chart(self, fig, df: pd.DataFrame, row: int, col: int):
        """添加排名分布图"""
        if 'rank' not in df.columns:
            return
        
        # 计算排名分布
        rank_counts = df['rank'].value_counts().sort_index()
        
        # 按排名区间分组
        rank_ranges = ['1-10', '11-20', '21-30', '31-40', '41-50']
        range_counts = []
        
        for i, range_name in enumerate(rank_ranges):
            start = i * 10 + 1
            end = (i + 1) * 10
            count = df[df['rank'].between(start, end)]['rank'].count()
            range_counts.append(count)
        
        fig.add_trace(
            go.Bar(
                x=rank_ranges,
                y=range_counts,
                name='排名分布',
                marker_color=self.colors['warning'],
                hovertemplate='排名范围: %{x}<br>问题数: %{y}<extra></extra>'
            ),
            row=row, col=col
        )
        
        fig.update_yaxes(title_text="问题数量", row=row, col=col)
    
    def _add_answer_distribution_chart(self, fig, df: pd.DataFrame, row: int, col: int):
        """添加回答数分布图"""
        if 'answer_count' not in df.columns or df['answer_count'].isna().all():
            return
        
        answer_counts = df['answer_count'].dropna()
        if answer_counts.empty:
            return
        
        fig.add_trace(
            go.Histogram(
                x=answer_counts,
                nbinsx=20,
                name='回答数分布',
                marker_color=self.colors['success'],
                opacity=0.7,
                hovertemplate='回答数范围: %{x}<br>问题数: %{y}<extra></extra>'
            ),
            row=row, col=col
        )
        
        fig.update_xaxes(title_text="回答数", row=row, col=col)
        fig.update_yaxes(title_text="问题数量", row=row, col=col)
    
    def _add_follower_analysis_chart(self, fig, df: pd.DataFrame, row: int, col: int):
        """添加关注度分析图"""
        if 'follower_count' not in df.columns or 'answer_count' not in df.columns:
            return
        
        # 过滤有效数据
        valid_data = df[['follower_count', 'answer_count', 'rank']].dropna()
        if valid_data.empty:
            return
        
        fig.add_trace(
            go.Scatter(
                x=valid_data['follower_count'],
                y=valid_data['answer_count'],
                mode='markers',
                marker=dict(
                    size=8,
                    color=valid_data['rank'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="排名")
                ),
                name='关注度vs回答数',
                hovertemplate='关注数: %{x}<br>回答数: %{y}<br>排名: %{marker.color}<extra></extra>'
            ),
            row=row, col=col
        )
        
        fig.update_xaxes(title_text="关注人数", row=row, col=col)
        fig.update_yaxes(title_text="回答数", row=row, col=col)
    
    def _add_tag_analysis_chart(self, fig, df: pd.DataFrame, row: int, col: int):
        """添加标签分析图"""
        if 'question_tags' not in df.columns:
            return
        
        # 提取所有标签
        all_tags = []
        for tags in df['question_tags'].dropna():
            if isinstance(tags, list):
                all_tags.extend(tags)
        
        if not all_tags:
            return
        
        # 统计标签频次
        tag_counts = pd.Series(all_tags).value_counts().head(15)
        
        fig.add_trace(
            go.Bar(
                x=tag_counts.values,
                y=tag_counts.index,
                orientation='h',
                name='热门标签',
                marker_color=self.colors['info'],
                hovertemplate='标签: %{y}<br>出现次数: %{x}<extra></extra>'
            ),
            row=row, col=col
        )
        
        fig.update_xaxes(title_text="出现次数", row=row, col=col)
        fig.update_yaxes(title_text="标签", row=row, col=col)
    
    def _add_time_heatmap(self, fig, df: pd.DataFrame, row: int, col: int):
        """添加时段活跃度热力图"""
        if 'crawl_time' not in df.columns:
            return
        
        # 提取时段信息
        df_time = df.copy()
        df_time['hour'] = df_time['crawl_time'].dt.hour
        df_time['day_of_week'] = df_time['crawl_time'].dt.day_name()
        
        # 创建时段统计
        time_stats = df_time.groupby(['day_of_week', 'hour']).size().reset_index(name='count')
        
        # 创建透视表
        heatmap_data = time_stats.pivot(index='day_of_week', columns='hour', values='count')
        heatmap_data = heatmap_data.fillna(0)
        
        # 确保星期顺序正确
        weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_data = heatmap_data.reindex(weekday_order, fill_value=0)
        
        fig.add_trace(
            go.Heatmap(
                z=heatmap_data.values,
                x=list(range(24)),
                y=weekday_order,
                colorscale='YlOrRd',
                name='活跃度',
                hovertemplate='星期: %{y}<br>时间: %{x}:00<br>活跃度: %{z}<extra></extra>'
            ),
            row=row, col=col
        )
        
        fig.update_xaxes(title_text="小时", row=row, col=col)
        fig.update_yaxes(title_text="星期", row=row, col=col)
    
    def _generate_stats_html(self, df: pd.DataFrame, days: int) -> str:
        """生成统计信息HTML"""
        # 基础统计
        total_records = len(df)
        unique_questions = df['question_hash'].nunique() if 'question_hash' in df.columns else len(df)
        
        # 时间范围
        if 'crawl_time' in df.columns:
            start_time = df['crawl_time'].min().strftime('%Y-%m-%d %H:%M')
            end_time = df['crawl_time'].max().strftime('%Y-%m-%d %H:%M')
        else:
            start_time = end_time = 'N/A'
        
        # 回答数统计
        answer_stats = ""
        if 'answer_count' in df.columns and not df['answer_count'].isna().all():
            avg_answers = df['answer_count'].mean()
            max_answers = df['answer_count'].max()
            answer_stats = f"""
            <div class="stat-item">
                <span class="stat-label">📝 平均回答数:</span>
                <span class="stat-value">{avg_answers:.1f}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">🔥 最高回答数:</span>
                <span class="stat-value">{max_answers}</span>
            </div>
            """
        
        return f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; margin-bottom: 20px; border-radius: 10px;">
            <h2 style="margin: 0 0 15px 0; text-align: center;">📊 数据统计概览</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div class="stat-item">
                    <span class="stat-label">📅 分析周期:</span>
                    <span class="stat-value">最近{days}天</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">📊 总记录数:</span>
                    <span class="stat-value">{total_records:,}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">🔗 独特问题:</span>
                    <span class="stat-value">{unique_questions:,}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">⏰ 数据时间:</span>
                    <span class="stat-value">{start_time} ~ {end_time}</span>
                </div>
                {answer_stats}
            </div>
        </div>
        <style>
            .stat-item {{
                background: rgba(255,255,255,0.1);
                padding: 10px;
                border-radius: 5px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .stat-label {{
                font-weight: bold;
            }}
            .stat-value {{
                font-size: 1.2em;
                color: #ffeb3b;
            }}
        </style>
        """
    
    def generate_trend_charts(self, days: int = 7):
        """生成趋势图表"""
        df = self.load_all_data()
        
        if df.empty:
            print("没有数据可用于生成图表")
            return
        
        # 过滤数据
        cutoff_date = datetime.now() - timedelta(days=days)
        if 'crawl_time' in df.columns:
            recent_df = df[df['crawl_time'] >= cutoff_date]
        else:
            recent_df = df
        
        # 设置图表样式
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'知乎热榜数据分析 - 最近{days}天', fontsize=20, fontweight='bold', y=0.95)
        
        # 1. 数据采集趋势
        if 'date' in recent_df.columns:
            daily_counts = recent_df.groupby('date').size()
            axes[0, 0].plot(daily_counts.index, daily_counts.values, 
                          marker='o', linewidth=3, markersize=8, color=self.colors['primary'])
            axes[0, 0].fill_between(daily_counts.index, daily_counts.values, alpha=0.3, color=self.colors['primary'])
            axes[0, 0].set_title('📈 每日数据采集趋势', fontsize=14, fontweight='bold')
            axes[0, 0].set_xlabel('日期')
            axes[0, 0].set_ylabel('问题数量')
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 2. 排名分布
        if 'rank' in recent_df.columns:
            rank_ranges = ['1-10', '11-20', '21-30', '31-40', '41-50']
            range_counts = []
            
            for i in range(5):
                start = i * 10 + 1
                end = (i + 1) * 10
                count = recent_df[recent_df['rank'].between(start, end)]['rank'].count()
                range_counts.append(count)
            
            bars = axes[0, 1].bar(rank_ranges, range_counts, color=self.colors['warning'], alpha=0.8)
            axes[0, 1].set_title('🔥 热榜排名分布', fontsize=14, fontweight='bold')
            axes[0, 1].set_xlabel('排名区间')
            axes[0, 1].set_ylabel('问题数量')
            
            # 添加数值标签
            for bar, count in zip(bars, range_counts):
                axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                               str(count), ha='center', va='bottom', fontweight='bold')
        
        # 3. 回答数分布
        if 'answer_count' in recent_df.columns and not recent_df['answer_count'].isna().all():
            answer_counts = recent_df['answer_count'].dropna()
            if not answer_counts.empty:
                axes[0, 2].hist(answer_counts, bins=20, color=self.colors['success'], alpha=0.7, edgecolor='black')
                axes[0, 2].axvline(answer_counts.mean(), color='red', linestyle='--', linewidth=2, 
                                 label=f'均值: {answer_counts.mean():.1f}')
                axes[0, 2].set_title('💬 回答数分布', fontsize=14, fontweight='bold')
                axes[0, 2].set_xlabel('回答数')
                axes[0, 2].set_ylabel('频次')
                axes[0, 2].legend()
        
        # 4. 热门标签
        if 'question_tags' in recent_df.columns:
            all_tags = []
            for tags in recent_df['question_tags'].dropna():
                if isinstance(tags, list):
                    all_tags.extend(tags)
            
            if all_tags:
                tag_counts = pd.Series(all_tags).value_counts().head(10)
                bars = axes[1, 0].barh(range(len(tag_counts)), tag_counts.values, color=self.colors['info'])
                axes[1, 0].set_yticks(range(len(tag_counts)))
                axes[1, 0].set_yticklabels(tag_counts.index)
                axes[1, 0].set_title('🏷️ 热门话题标签 (TOP 10)', fontsize=14, fontweight='bold')
                axes[1, 0].set_xlabel('出现次数')
                
                # 添加数值标签
                for i, (bar, count) in enumerate(zip(bars, tag_counts.values)):
                    axes[1, 0].text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                                   str(count), ha='left', va='center', fontweight='bold')
        
        # 5. 时段活跃度
        if 'crawl_time' in recent_df.columns:
            df_hour = recent_df.copy()
            df_hour['hour'] = df_hour['crawl_time'].dt.hour
            hourly_counts = df_hour.groupby('hour').size()
            
            bars = axes[1, 1].bar(hourly_counts.index, hourly_counts.values, 
                                color=self.colors['secondary'], alpha=0.8)
            axes[1, 1].set_title('⏰ 24小时活跃度分布', fontsize=14, fontweight='bold')
            axes[1, 1].set_xlabel('小时')
            axes[1, 1].set_ylabel('活跃度')
            axes[1, 1].set_xticks(range(0, 24, 4))
        
        # 6. 数据质量指标
        total_records = len(recent_df)
        unique_questions = recent_df['question_hash'].nunique() if 'question_hash' in recent_df.columns else len(recent_df)
        completion_rate = (recent_df['answer_count'].notna().sum() / len(recent_df) * 100) if 'answer_count' in recent_df.columns else 0
        
        metrics = ['总记录数', '独特问题', '数据完整率(%)']
        values = [total_records, unique_questions, completion_rate]
        colors_list = [self.colors['primary'], self.colors['success'], self.colors['warning']]
        
        bars = axes[1, 2].bar(metrics, values, color=colors_list, alpha=0.8)
        axes[1, 2].set_title('📊 数据质量指标', fontsize=14, fontweight='bold')
        axes[1, 2].set_ylabel('数值')
        
        # 添加数值标签
        for bar, value in zip(bars, values):
            axes[1, 2].text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values) * 0.01,
                           f'{value:.1f}' if isinstance(value, float) else str(value),
                           ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.92)
        
        # 保存图表
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.analysis_dir, f'trend_analysis_{timestamp}.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.show()
        
        print(f"图表已保存到: {filename}")
        return filename