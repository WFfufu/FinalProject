#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知乎热榜爬虫 - 支持登录
可以通过Cookie或手动登录方式访问热榜
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json
import os
from datetime import datetime
import pickle

class ZhihuLoginCrawler:
    """知乎登录爬虫"""
    
    def __init__(self, use_cookies=True):
        self.use_cookies = use_cookies
        self.driver = None
        self.data_dir = "data"
        self.cookie_file = os.path.join(self.data_dir, "zhihu_cookies.pkl")
        
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def setup_driver(self):
        """设置Chrome驱动"""
        options = Options()
        
        # 基本设置
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 禁用GPU相关
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--no-sandbox')
        
        # User-Agent
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("✓ Chrome驱动启动成功")
    
    def save_cookies(self):
        """保存Cookie到文件"""
        cookies = self.driver.get_cookies()
        with open(self.cookie_file, 'wb') as f:
            pickle.dump(cookies, f)
        print(f"✓ Cookie已保存到: {self.cookie_file}")
    
    def load_cookies(self):
        """从文件加载Cookie"""
        if os.path.exists(self.cookie_file):
            with open(self.cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except:
                    pass
            print("✓ Cookie已加载")
            return True
        return False
    
    def manual_login(self):
        """手动登录流程"""
        print("\n" + "="*50)
        print("请手动登录知乎")
        print("="*50)
        print("1. 在打开的浏览器中完成登录")
        print("2. 登录成功后，按Enter继续...")
        print("="*50)
        
        # 访问登录页
        self.driver.get("https://www.zhihu.com/signin")
        
        # 等待用户手动登录
        input("\n请完成登录后按Enter继续...")
        
        # 保存Cookie
        self.save_cookies()
        
        return True
    
    def check_login_status(self):
        """检查登录状态"""
        try:
            # 尝试访问需要登录的页面
            self.driver.get("https://www.zhihu.com/hot")
            time.sleep(3)
            
            # 检查是否被重定向到登录页
            current_url = self.driver.current_url
            if "signin" in current_url:
                print("✗ 未登录，需要登录")
                return False
            else:
                print("✓ 已登录")
                return True
        except:
            return False
    
    def crawl_hot_list(self):
        """爬取热榜数据"""
        print("\n开始爬取热榜数据...")
        
        # 确保在热榜页面
        if "hot" not in self.driver.current_url:
            self.driver.get("https://www.zhihu.com/hot")
            time.sleep(3)
        
        hot_items = []
        
        try:
            # 等待热榜加载
            wait = WebDriverWait(self.driver, 20)
            
            # 尝试多种选择器查找热榜项目
            selectors = [
                "div.HotItem",
                "section.HotItem",
                "[class*='HotItem']",
                "div[data-za-detail-view-id]",
                "a[href*='/question/']"
            ]
            
            elements = []
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"✓ 使用选择器 '{selector}' 找到 {len(elements)} 个元素")
                        break
                except:
                    continue
            
            # 如果还是没找到，尝试通过链接查找
            if not elements:
                print("尝试通过链接查找...")
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                question_links = [link for link in all_links if "/question/" in link.get_attribute("href") or ""]
                
                if question_links:
                    print(f"✓ 找到 {len(question_links)} 个问题链接")
                    
                    for idx, link in enumerate(question_links[:50], 1):
                        try:
                            # 获取父元素作为热榜项
                            parent = link.find_element(By.XPATH, "./ancestor::*[position()<=4]")
                            
                            item = {
                                'rank': idx,
                                'title': link.text or parent.text[:100],
                                'url': link.get_attribute('href'),
                                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            
                            if item['title']:
                                hot_items.append(item)
                                print(f"✓ 提取第 {idx} 条: {item['title'][:50]}...")
                        except:
                            continue
            else:
                # 解析找到的元素
                for idx, element in enumerate(elements[:50], 1):
                    try:
                        item = self._parse_hot_item(element, idx)
                        if item and item.get('title'):
                            hot_items.append(item)
                            print(f"✓ 解析第 {idx} 条: {item['title'][:50]}...")
                    except Exception as e:
                        print(f"✗ 解析第 {idx} 条时出错: {str(e)}")
                        
        except Exception as e:
            print(f"✗ 爬取过程出错: {str(e)}")
            
        return hot_items
    
    def _parse_hot_item(self, element, rank):
        """解析热榜项"""
        item = {
            'rank': rank,
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            # 查找标题
            title_elem = element.find_element(By.CSS_SELECTOR, "h2, [class*='title'], a")
            if title_elem:
                item['title'] = title_elem.text.strip()
            
            # 查找链接
            link_elem = element.find_element(By.CSS_SELECTOR, "a[href]")
            if link_elem:
                item['url'] = link_elem.get_attribute('href')
            
            # 查找热度
            try:
                heat_elem = element.find_element(By.CSS_SELECTOR, "[class*='metrics'], [class*='hot']")
                if heat_elem:
                    item['heat_value'] = heat_elem.text.strip()
            except:
                pass
                
        except:
            pass
            
        return item if 'title' in item else None
    
    def save_data(self, data):
        """保存数据"""
        if not data:
            print("没有数据可保存")
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"zhihu_hot_{timestamp}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"\n✓ 数据已保存到: {filepath}")
    
    def run(self):
        """运行爬虫"""
        try:
            # 启动浏览器
            self.setup_driver()
            
            # 先访问主页（设置域）
            self.driver.get("https://www.zhihu.com")
            time.sleep(2)
            
            # 尝试加载Cookie
            if self.use_cookies and self.load_cookies():
                # 刷新页面使Cookie生效
                self.driver.refresh()
                time.sleep(3)
                
                # 检查登录状态
                if self.check_login_status():
                    # 已登录，直接爬取
                    hot_items = self.crawl_hot_list()
                else:
                    # Cookie失效，需要重新登录
                    print("Cookie已失效，需要重新登录")
                    if self.manual_login():
                        hot_items = self.crawl_hot_list()
                    else:
                        print("登录失败")
                        return
            else:
                # 没有Cookie或不使用Cookie，手动登录
                if self.manual_login():
                    hot_items = self.crawl_hot_list()
                else:
                    print("登录失败")
                    return
            
            # 显示结果
            if hot_items:
                print(f"\n✓ 成功爬取 {len(hot_items)} 条热榜数据")
                print("\n数据预览（前5条）：")
                print("-" * 80)
                for item in hot_items[:5]:
                    print(f"{item['rank']}. {item.get('title', 'N/A')}")
                    print(f"   链接: {item.get('url', 'N/A')}")
                    print(f"   热度: {item.get('heat_value', 'N/A')}")
                    print("-" * 80)
                
                # 保存数据
                self.save_data(hot_items)
            else:
                print("\n✗ 未能爬取到数据")
                
        except Exception as e:
            print(f"\n程序出错: {str(e)}")
        finally:
            input("\n按Enter键关闭浏览器...")
            if self.driver:
                self.driver.quit()


def main():
    """主函数"""
    print("="*50)
    print("知乎热榜爬虫（支持登录）")
    print("="*50)
    
    # 询问是否使用已保存的Cookie
    use_cookies = True
    choice = input("\n是否尝试使用已保存的登录信息？(Y/n): ").strip().lower()
    if choice == 'n':
        use_cookies = False
    
    # 创建爬虫实例
    crawler = ZhihuLoginCrawler(use_cookies=use_cookies)
    
    # 运行爬虫
    crawler.run()


if __name__ == "__main__":
    main()