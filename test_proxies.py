#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import random
from urllib.parse import urlparse

class ProxyTester:
    def __init__(self, proxy_file='collected_proxies.json'):
        self.proxy_file = proxy_file
        self.test_urls = [
            'http://httpbin.org/ip',
            'http://ip-api.com/json',
            'https://api.ipify.org?format=json',
            'http://icanhazip.com'
        ]
        self.baidu_url = 'https://www.baidu.com'
        
    def load_proxies(self):
        """加载代理列表"""
        try:
            with open(self.proxy_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('proxies', [])
        except Exception as e:
            print(f"❌ 加载代理文件失败: {e}")
            return []
    
    def format_proxy_url(self, proxy):
        """格式化代理URL"""
        if proxy['type'] == 'ss':
            # SS代理需要特殊处理，这里简化为HTTP代理格式
            return f"http://{proxy['host']}:{proxy['port']}"
        elif proxy['type'] == 'vmess':
            # VMess代理也简化为HTTP代理格式
            return f"http://{proxy['host']}:{proxy['port']}"
        elif proxy['type'] == 'trojan':
            # Trojan代理简化为HTTP代理格式
            return f"http://{proxy['host']}:{proxy['port']}"
        else:
            return f"http://{proxy['host']}:{proxy['port']}"
    
    def test_proxy_basic(self, proxy, timeout=10):
        """基础代理连通性测试"""
        proxy_url = self.format_proxy_url(proxy)
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        try:
            # 测试获取IP
            response = requests.get(
                self.test_urls[0], 
                proxies=proxies, 
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            if response.status_code == 200:
                try:
                    ip_data = response.json()
                    proxy_ip = ip_data.get('origin', 'Unknown')
                    return True, proxy_ip
                except:
                    proxy_ip = response.text.strip()
                    return True, proxy_ip
            else:
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            return False, str(e)
    
    def test_baidu_access(self, proxy, timeout=15):
        """测试访问百度"""
        proxy_url = self.format_proxy_url(proxy)
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        try:
            response = requests.get(
                self.baidu_url,
                proxies=proxies,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                allow_redirects=True
            )
            
            if response.status_code == 200:
                if '百度' in response.text or 'baidu' in response.text.lower():
                    return True, "百度访问成功"
                else:
                    return False, "响应内容不是百度页面"
            else:
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            return False, str(e)
    
    def get_real_ip(self):
        """获取本机真实IP"""
        try:
            response = requests.get(self.test_urls[0], timeout=10)
            if response.status_code == 200:
                ip_data = response.json()
                return ip_data.get('origin', 'Unknown')
        except:
            pass
        return "Unknown"
    
    def test_all_proxies(self, max_test=10):
        """测试所有代理"""
        proxies = self.load_proxies()
        if not proxies:
            print("❌ 没有找到代理数据")
            return
        
        print(f"📊 加载了 {len(proxies)} 个代理")
        print(f"🔍 本机IP: {self.get_real_ip()}")
        print("=" * 80)
        
        # 限制测试数量
        test_proxies = proxies[:max_test] if len(proxies) > max_test else proxies
        print(f"🧪 开始测试前 {len(test_proxies)} 个代理...\n")
        
        working_count = 0
        baidu_count = 0
        
        for i, proxy in enumerate(test_proxies, 1):
            print(f"[{i}/{len(test_proxies)}] 测试代理: {proxy['host']}:{proxy['port']} ({proxy['type']})")
            
            # 基础连通性测试
            is_working, result = self.test_proxy_basic(proxy)
            
            if is_working:
                working_count += 1
                print(f"  ✅ 连通性: 成功 - 代理IP: {result}")
                
                # 测试百度访问
                baidu_ok, baidu_result = self.test_baidu_access(proxy)
                if baidu_ok:
                    baidu_count += 1
                    print(f"  ✅ 百度访问: {baidu_result}")
                else:
                    print(f"  ❌ 百度访问: {baidu_result}")
            else:
                print(f"  ❌ 连通性: 失败 - {result}")
            
            print()
            
            # 避免请求过快
            time.sleep(random.uniform(1, 3))
        
        print("=" * 80)
        print(f"📈 测试结果统计:")
        print(f"  总测试数: {len(test_proxies)}")
        print(f"  连通成功: {working_count} ({working_count/len(test_proxies)*100:.1f}%)")
        print(f"  百度可访问: {baidu_count} ({baidu_count/len(test_proxies)*100:.1f}%)")

if __name__ == "__main__":
    tester = ProxyTester()
    
    print("🚀 代理测试工具")
    print("=" * 50)
    
    # 测试前10个代理
    tester.test_all_proxies(max_test=10)
