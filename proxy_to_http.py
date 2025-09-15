#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

class ProxyToHTTP:
    def __init__(self, input_file='collected_proxies.json'):
        self.input_file = input_file
        self.test_urls = [
            'http://httpbin.org/ip',
            'https://api.ipify.org?format=json',
            'http://icanhazip.com'
        ]
        
    def load_proxies(self):
        """加载代理数据"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('proxies', [])
        except Exception as e:
            print(f"❌ 加载代理文件失败: {e}")
            return []
    
    def convert_to_http_proxy(self, proxy):
        """尝试将代理转换为HTTP代理格式"""
        host = proxy.get('host')
        port = proxy.get('port')
        proxy_type = proxy.get('type', '').lower()
        
        if not host or not port:
            return None
        
        # 尝试不同的HTTP代理格式
        http_formats = []
        
        # 1. 直接HTTP代理格式
        http_formats.append(f"http://{host}:{port}")
        
        # 2. 如果有认证信息，尝试加上
        if proxy_type == 'ss' and proxy.get('password'):
            # SS代理有时可以直接当HTTP代理用
            password = proxy.get('password')
            method = proxy.get('method', '')
            # 尝试用户名:密码格式
            http_formats.append(f"http://{method}:{password}@{host}:{port}")
            http_formats.append(f"http://user:{password}@{host}:{port}")
        
        # 3. SOCKS5格式（有些代理支持）
        http_formats.append(f"socks5://{host}:{port}")
        
        # 4. 如果是trojan，尝试用密码作为认证
        if proxy_type == 'trojan' and proxy.get('password'):
            password = proxy.get('password')
            http_formats.append(f"http://{password}@{host}:{port}")
        
        return http_formats
    
    def test_http_proxy(self, proxy_url, timeout=10):
        """测试HTTP代理是否可用"""
        try:
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # 随机选择测试URL
            test_url = random.choice(self.test_urls)
            
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            if response.status_code == 200:
                # 尝试获取IP信息
                try:
                    if 'json' in test_url:
                        ip_data = response.json()
                        proxy_ip = ip_data.get('ip', ip_data.get('origin', 'Unknown'))
                    else:
                        proxy_ip = response.text.strip()
                    return True, proxy_ip
                except:
                    return True, "IP获取失败但连接成功"
            else:
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            return False, str(e)
    
    def test_proxy_formats(self, proxy):
        """测试代理的各种HTTP格式"""
        formats = self.convert_to_http_proxy(proxy)
        if not formats:
            return None
        
        host = proxy.get('host')
        port = proxy.get('port')
        proxy_type = proxy.get('type')
        
        print(f"🔍 测试代理: {host}:{port} ({proxy_type})")
        
        for i, proxy_url in enumerate(formats, 1):
            print(f"  [{i}] 尝试格式: {proxy_url}")
            
            success, result = self.test_http_proxy(proxy_url)
            
            if success:
                print(f"  ✅ 成功! 代理IP: {result}")
                return {
                    'original': proxy,
                    'http_proxy': proxy_url,
                    'proxy_ip': result,
                    'host': host,
                    'port': port,
                    'type': proxy_type
                }
            else:
                print(f"  ❌ 失败: {result}")
        
        print(f"  💀 所有格式都失败")
        return None
    
    def convert_all_to_http(self, max_workers=10, max_test=20):
        """转换所有代理为HTTP格式"""
        print("🔄 开始转换代理为HTTP格式...")
        
        proxies = self.load_proxies()
        if not proxies:
            return
        
        print(f"📊 加载了 {len(proxies)} 个代理")
        
        # 限制测试数量
        test_proxies = proxies[:max_test] if len(proxies) > max_test else proxies
        print(f"🧪 测试前 {len(test_proxies)} 个代理...")
        
        working_http_proxies = []
        
        # 单线程测试（避免并发问题）
        for i, proxy in enumerate(test_proxies, 1):
            print(f"\n[{i}/{len(test_proxies)}] " + "="*50)
            
            result = self.test_proxy_formats(proxy)
            if result:
                working_http_proxies.append(result)
                print(f"🎉 找到可用HTTP代理: {result['http_proxy']}")
            
            # 避免请求过快
            time.sleep(random.uniform(2, 4))
        
        print("\n" + "="*80)
        print(f"📈 转换结果:")
        print(f"  测试代理数: {len(test_proxies)}")
        print(f"  可用HTTP代理: {len(working_http_proxies)}")
        
        if working_http_proxies:
            # 保存可用的HTTP代理
            http_proxy_list = []
            for proxy in working_http_proxies:
                http_proxy_list.append({
                    'proxy_url': proxy['http_proxy'],
                    'proxy_ip': proxy['proxy_ip'],
                    'host': proxy['host'],
                    'port': proxy['port'],
                    'original_type': proxy['type']
                })
            
            # 保存为爬虫可用格式
            result = {
                'update_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'count': len(http_proxy_list),
                'http_proxies': http_proxy_list
            }
            
            with open('http_proxies.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"💾 HTTP代理列表已保存到 http_proxies.json")
            
            # 生成简单的代理URL列表
            proxy_urls = [p['proxy_url'] for p in http_proxy_list]
            with open('proxy_urls.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(proxy_urls))
            
            print(f"📄 代理URL列表已保存到 proxy_urls.txt")
            
            # 显示使用示例
            print("\n🚀 爬虫使用示例:")
            print("```python")
            print("import requests")
            print("import random")
            print("")
            print("# 加载代理列表")
            print("with open('http_proxies.json', 'r') as f:")
            print("    data = json.load(f)")
            print("    proxy_list = [p['proxy_url'] for p in data['http_proxies']]")
            print("")
            print("# 随机选择代理")
            print("proxy = random.choice(proxy_list)")
            print("proxies = {'http': proxy, 'https': proxy}")
            print("")
            print("# 发起请求")
            print("response = requests.get('https://www.baidu.com', proxies=proxies)")
            print("```")
        else:
            print("😞 没有找到可用的HTTP代理")

if __name__ == "__main__":
    converter = ProxyToHTTP()
    converter.convert_all_to_http(max_test=10)  # 测试前10个代理
