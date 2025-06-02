#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知乎热榜Web可视化界面
使用Flask提供数据查看和分析功能
"""

from flask import Flask, render_template, jsonify, request, send_file
import json
import os
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objs as go
import plotly.utils
from typing import Dict, List


app = Flask(__name__)

class WebDashboard:
    """Web控制面板"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        self.analysis_dir = os.path.join(data_dir, "analysis")
        self.reports_dir = os.path.join(data_dir, "reports")
    
    def load_all_data(self) -> pd.DataFrame:
        """加载所有数据"""
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
    
    def get_dashboard_stats(self, days: int = 7) -> Dict:
        """获取控制面板统计数据"""
        df = self.load_all_data()
        
        if df.empty:
            return {"error": "没有数据"}
        
        # 过滤最近N天的数据
        cutoff_date = datetime.now() - timedelta(days=days)
        if 'crawl_time' in df.columns:
            recent_df = df[df['crawl_time'] >= cutoff_date]
        else:
            recent_df = df
        
        stats = {
            "total_questions": len(recent_df['question_hash'].unique()) if 'question_hash' in recent_df.columns else len(recent_df),
            "total_records": len(recent_df),
            "latest_crawl": recent_df['crawl_time'].max().strftime('%Y-%m-%d %H:%M:%S') if 'crawl_time' in recent_df.columns else 'N/A',
            "date_range": f"{recent_df['date'].min().strftime('%Y-%m-%d')} 至 {recent_df['date'].max().strftime('%Y-%m-%d')}" if 'date' in recent_df.columns else 'N/A'
        }
        
        # 每日统计
        if 'date' in recent_df.columns:
            daily_counts = recent_df.groupby('date').size()
            stats["daily_average"] = round(daily_counts.mean(), 1)
            stats["daily_counts"] = {str(date): int(count) for date, count in daily_counts.items()}
        
        # 热门标签
        if 'question_tags' in recent_df.columns:
            all_tags = []
            for tags in recent_df['question_tags'].dropna():
                if isinstance(tags, list):
                    all_tags.extend(tags)
            
            if all_tags:
                tag_counts = pd.Series(all_tags).value_counts().head(10)
                stats["popular_tags"] = tag_counts.to_dict()
        
        # 回答数统计
        if 'answer_count' in recent_df.columns and recent_df['answer_count'].sum() > 0:
            answer_stats = recent_df['answer_count'].describe()
            stats["answer_stats"] = {
                "mean": round(answer_stats['mean'], 1),
                "median": answer_stats['50%'],
                "max": int(answer_stats['max'])
            }
        
        return stats
    
    def get_recent_hot_items(self, limit: int = 20) -> List[Dict]:
        """获取最近的热榜项目"""
        df = self.load_all_data()
        
        if df.empty:
            return []
        
        # 获取最新一次爬取的数据
        if 'crawl_time' in df.columns:
            latest_time = df['crawl_time'].max()
            latest_df = df[df['crawl_time'] == latest_time]
        else:
            latest_df = df.tail(50)  # 取最后50条
        
        # 按排名排序
        if 'rank' in latest_df.columns:
            latest_df = latest_df.sort_values('rank')
        
        items = []
        for _, row in latest_df.head(limit).iterrows():
            item = {
                "rank": row.get('rank', 'N/A'),
                "title": row.get('title', 'N/A'),
                "url": row.get('url', '#'),
                "heat_value": row.get('heat_value', 'N/A'),
                "answer_count": row.get('answer_count', 'N/A'),
                "question_tags": row.get('question_tags', []) if isinstance(row.get('question_tags'), list) else [],
                "crawl_time": row.get('crawl_time', '').strftime('%H:%M:%S') if pd.notna(row.get('crawl_time')) else 'N/A'
            }
            items.append(item)
        
        return items
    
    def create_trend_chart(self, days: int = 7) -> str:
        """创建趋势图表（Plotly）"""
        df = self.load_all_data()
        
        if df.empty or 'date' not in df.columns:
            return json.dumps({"data": [], "layout": {"title": "没有数据"}})
        
        # 过滤数据
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_df = df[df['date'] >= cutoff_date.date()] if 'date' in df.columns else df
        
        # 每日统计
        daily_counts = recent_df.groupby('date').size().reset_index()
        daily_counts.columns = ['date', 'count']
        
        # 创建图表
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_counts['date'],
            y=daily_counts['count'],
            mode='lines+markers',
            name='每日问题数',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title=f'最近{days}天热榜数据趋势',
            xaxis_title='日期',
            yaxis_title='问题数量',
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=12),
            height=400
        )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    def create_rank_distribution_chart(self) -> str:
        """创建排名分布图表"""
        df = self.load_all_data()
        
        if df.empty or 'rank' not in df.columns:
            return json.dumps({"data": [], "layout": {"title": "没有排名数据"}})
        
        # 排名分布统计
        rank_counts = df['rank'].value_counts().head(20).sort_index()
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=rank_counts.index,
            y=rank_counts.values,
            name='排名分布',
            marker_color='#ff7f0e'
        ))
        
        fig.update_layout(
            title='排名分布统计（Top 20）',
            xaxis_title='排名',
            yaxis_title='出现次数',
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=400
        )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    def create_tag_chart(self) -> str:
        """创建标签分布图表"""
        df = self.load_all_data()
        
        if df.empty or 'question_tags' not in df.columns:
            return json.dumps({"data": [], "layout": {"title": "没有标签数据"}})
        
        # 统计标签
        all_tags = []
        for tags in df['question_tags'].dropna():
            if isinstance(tags, list):
                all_tags.extend(tags)
        
        if not all_tags:
            return json.dumps({"data": [], "layout": {"title": "没有标签数据"}})
        
        tag_counts = pd.Series(all_tags).value_counts().head(15)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=tag_counts.values,
            y=tag_counts.index,
            orientation='h',
            name='标签热度',
            marker_color='#2ca02c'
        ))
        
        fig.update_layout(
            title='热门标签统计（Top 15）',
            xaxis_title='出现次数',
            yaxis_title='标签',
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=500
        )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


# 全局实例
dashboard = WebDashboard()

@app.route('/')
def index():
    """主页"""
    return render_template('dashboard.html')

@app.route('/api/stats')
def api_stats():
    """获取统计数据API"""
    days = request.args.get('days', 7, type=int)
    stats = dashboard.get_dashboard_stats(days)
    return jsonify(stats)

@app.route('/api/recent-items')
def api_recent_items():
    """获取最新热榜项目API"""
    limit = request.args.get('limit', 20, type=int)
    items = dashboard.get_recent_hot_items(limit)
    return jsonify(items)

@app.route('/api/chart/trend')
def api_trend_chart():
    """趋势图表API"""
    days = request.args.get('days', 7, type=int)
    chart_json = dashboard.create_trend_chart(days)
    return chart_json

@app.route('/api/chart/rank-distribution')
def api_rank_distribution():
    """排名分布图表API"""
    chart_json = dashboard.create_rank_distribution_chart()
    return chart_json

@app.route('/api/chart/tags')
def api_tag_chart():
    """标签分布图表API"""
    chart_json = dashboard.create_tag_chart()
    return chart_json

@app.route('/api/data/export')
def api_data_export():
    """数据导出API"""
    # 这里可以集成之前的数据导出功能
    return jsonify({"message": "数据导出功能待实现"})


if __name__ == '__main__':
    # 创建模板目录和文件
    template_dir = 'templates'
    os.makedirs(template_dir, exist_ok=True)
    
    # 创建HTML模板
    html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>知乎热榜数据看板</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; }
        .header { background: #fff; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header h1 { color: #333; font-size: 28px; }
        .header p { color: #666; margin-top: 5px; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #fff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .stat-card h3 { color: #333; font-size: 14px; margin-bottom: 10px; text-transform: uppercase; }
        .stat-card .value { color: #007bff; font-size: 32px; font-weight: bold; }
        .charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .chart-card { background: #fff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .chart-card.full-width { grid-column: 1 / -1; }
        .recent-items { background: #fff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .item { padding: 15px; border-bottom: 1px solid #eee; }
        .item:last-child { border-bottom: none; }
        .item-rank { display: inline-block; background: #007bff; color: #fff; width: 30px; height: 30px; border-radius: 50%; text-align: center; line-height: 30px; font-weight: bold; margin-right: 15px; }
        .item-title { font-size: 16px; color: #333; text-decoration: none; }
        .item-title:hover { color: #007bff; }
        .item-meta { color: #666; font-size: 12px; margin-top: 5px; }
        .tag { background: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-right: 5px; }
        .loading { text-align: center; padding: 50px; color: #666; }
        @media (max-width: 768px) {
            .charts-grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: 1fr 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🔥 知乎热榜数据看板</h1>
            <p>实时监控热榜趋势，数据驱动洞察</p>
        </div>
    </div>

    <div class="container">
        <!-- 统计卡片 -->
        <div class="stats-grid" id="stats-grid">
            <div class="loading">正在加载统计数据...</div>
        </div>

        <!-- 图表网格 -->
        <div class="charts-grid">
            <div class="chart-card">
                <h3>📈 数据趋势</h3>
                <div id="trend-chart" style="height: 350px;"></div>
            </div>
            <div class="chart-card">
                <h3>📊 排名分布</h3>
                <div id="rank-chart" style="height: 350px;"></div>
            </div>
            <div class="chart-card full-width">
                <h3>🏷️ 热门标签</h3>
                <div id="tag-chart" style="height: 400px;"></div>
            </div>
        </div>

        <!-- 最新热榜 -->
        <div class="recent-items">
            <h3>🔥 最新热榜</h3>
            <div id="recent-items">
                <div class="loading">正在加载最新数据...</div>
            </div>
        </div>
    </div>

    <script>
        // 加载统计数据
        async function loadStats() {
            try {
                const response = await fetch('/api/stats?days=7');
                const stats = await response.json();
                
                if (stats.error) {
                    document.getElementById('stats-grid').innerHTML = '<div class="loading">暂无数据</div>';
                    return;
                }

                const statsHtml = `
                    <div class="stat-card">
                        <h3>总问题数</h3>
                        <div class="value">${stats.total_questions}</div>
                    </div>
                    <div class="stat-card">
                        <h3>总记录数</h3>
                        <div class="value">${stats.total_records}</div>
                    </div>
                    <div class="stat-card">
                        <h3>日均问题</h3>
                        <div class="value">${stats.daily_average || 'N/A'}</div>
                    </div>
                    <div class="stat-card">
                        <h3>最新爬取</h3>
                        <div class="value" style="font-size: 14px;">${stats.latest_crawl}</div>
                    </div>
                `;
                
                document.getElementById('stats-grid').innerHTML = statsHtml;
            } catch (error) {
                console.error('加载统计数据失败:', error);
            }
        }

        // 加载最新热榜
        async function loadRecentItems() {
            try {
                const response = await fetch('/api/recent-items?limit=20');
                const items = await response.json();
                
                if (items.length === 0) {
                    document.getElementById('recent-items').innerHTML = '<div class="loading">暂无数据</div>';
                    return;
                }

                const itemsHtml = items.map(item => `
                    <div class="item">
                        <span class="item-rank">${item.rank}</span>
                        <a href="${item.url}" target="_blank" class="item-title">${item.title}</a>
                        <div class="item-meta">
                            ${item.heat_value !== 'N/A' ? `热度: ${item.heat_value}` : ''}
                            ${item.answer_count !== 'N/A' ? ` | 回答: ${item.answer_count}` : ''}
                            ${item.crawl_time !== 'N/A' ? ` | 时间: ${item.crawl_time}` : ''}
                            <div style="margin-top: 5px;">
                                ${item.question_tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                            </div>
                        </div>
                    </div>
                `).join('');
                
                document.getElementById('recent-items').innerHTML = itemsHtml;
            } catch (error) {
                console.error('加载最新热榜失败:', error);
            }
        }

        // 加载图表
        async function loadCharts() {
            try {
                // 趋势图
                const trendResponse = await fetch('/api/chart/trend?days=7');
                const trendData = await trendResponse.json();
                Plotly.newPlot('trend-chart', trendData.data, trendData.layout, {responsive: true});

                // 排名分布图
                const rankResponse = await fetch('/api/chart/rank-distribution');
                const rankData = await rankResponse.json();
                Plotly.newPlot('rank-chart', rankData.data, rankData.layout, {responsive: true});

                // 标签图
                const tagResponse = await fetch('/api/chart/tags');
                const tagData = await tagResponse.json();
                Plotly.newPlot('tag-chart', tagData.data, tagData.layout, {responsive: true});
            } catch (error) {
                console.error('加载图表失败:', error);
            }
        }

        // 页面加载完成后执行
        document.addEventListener('DOMContentLoaded', function() {
            loadStats();
            loadRecentItems();
            loadCharts();
            
            // 每5分钟自动刷新数据
            setInterval(() => {
                loadStats();
                loadRecentItems();
            }, 5 * 60 * 1000);
        });
    </script>
</body>
</html>'''
    
    with open(os.path.join(template_dir, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print("知乎热榜Web可视化界面启动中...")
    print("访问地址: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服务")
    
    app.run(debug=True, host='0.0.0.0', port=5000)