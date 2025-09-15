import re
import os
import yaml
import threading
import base64
import requests
import json
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
from tqdm import tqdm
from retry import retry

from pre_check import pre_check

# 存储解析出的代理配置
all_proxies = []
# 存储可用的代理 IP
working_proxies = []

@logger.catch
def get_config():
    with open('./config.yaml',encoding="UTF-8") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    list_tg = data['tgchannel']
    new_list = []
    for url in list_tg:
        a = url.split("/")[-1]
        url = 'https://t.me/s/'+a
        new_list.append(url)
    return new_list

@logger.catch
def get_channel_http(channel_url):
    try:
        with requests.post(channel_url) as resp:
            data = resp.text
        url_list = re.findall("https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]", data)  # 使用正则表达式查找订阅链接并创建列表
        logger.info(channel_url+'\t获取成功')
    except Exception as e:
        logger.warning(channel_url+'\t获取失败')
        logger.error(channel_url+e)
        url_list = []
    finally:
        return url_list

# @logger.catch
# def get_channel_http(channel_url):
#     headers = {
#         'Referer': 'https://t.me/s/wbnet',
#         'sec-ch-ua-mobile': '?0',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
#     }
#     try:
#         with requests.post(channel_url,headers=headers) as resp:
#             data = resp.text
#         url_list = re.findall("https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]", data)  # 使用正则表达式查找订阅链接并创建列表
#         logger.info(channel_url+'\t获取成功')
#     except Exception as e:
#         logger.error('channel_url',e)
#         logger.warning(channel_url+'\t获取失败')
#         url_list = []
#     finally:
#         return url_list

def parse_vmess(vmess_url):
    """解析vmess链接"""
    try:
        vmess_data = vmess_url.replace('vmess://', '')
        decoded = base64.b64decode(vmess_data + '==').decode('utf-8')
        config = json.loads(decoded)
        return {
            'type': 'vmess',
            'host': config.get('add', ''),
            'port': int(config.get('port', 0)),
            'id': config.get('id', ''),
            'aid': config.get('aid', 0),
            'net': config.get('net', 'tcp'),
            'path': config.get('path', ''),
            'host_header': config.get('host', ''),
            'tls': config.get('tls', ''),
            'ps': config.get('ps', '')
        }
    except:
        return None

def parse_ss(ss_url):
    """解析ss链接"""
    try:
        # ss://method:password@host:port#name
        ss_data = ss_url.replace('ss://', '')
        if '#' in ss_data:
            ss_data, name = ss_data.split('#', 1)
        else:
            name = ''

        if '@' in ss_data:
            method_pass, host_port = ss_data.split('@', 1)
            if ':' in host_port:
                host, port = host_port.rsplit(':', 1)
                if ':' in method_pass:
                    method, password = method_pass.split(':', 1)
                else:
                    # Base64编码的method:password
                    decoded = base64.b64decode(method_pass + '==').decode('utf-8')
                    method, password = decoded.split(':', 1)

                return {
                    'type': 'ss',
                    'host': host,
                    'port': int(port),
                    'method': method,
                    'password': password,
                    'name': name
                }
    except:
        return None

def parse_trojan(trojan_url):
    """解析trojan链接"""
    try:
        # trojan://password@host:port#name
        trojan_data = trojan_url.replace('trojan://', '')
        if '#' in trojan_data:
            trojan_data, name = trojan_data.split('#', 1)
        else:
            name = ''

        if '@' in trojan_data:
            password, host_port = trojan_data.split('@', 1)
            if ':' in host_port:
                host, port = host_port.rsplit(':', 1)
                return {
                    'type': 'trojan',
                    'host': host,
                    'port': int(port),
                    'password': password,
                    'name': name
                }
    except:
        return None


@logger.catch
def parse_subscription(url, bar):
    """解析订阅链接获取代理列表"""
    headers = {'User-Agent': 'ClashforWindows/0.18.1'}
    with thread_max_num:
        @retry(tries=2)
        def start_check(url):
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                content = res.text

                # 尝试Base64解码
                try:
                    decoded = base64.b64decode(content + '==').decode('utf-8')
                    content = decoded
                except:
                    pass

                # 解析各种协议的代理
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('vmess://'):
                        proxy = parse_vmess(line)
                        if proxy and proxy.get('host') and proxy.get('port'):
                            all_proxies.append(proxy)
                    elif line.startswith('ss://'):
                        proxy = parse_ss(line)
                        if proxy and proxy.get('host') and proxy.get('port'):
                            all_proxies.append(proxy)
                    elif line.startswith('trojan://'):
                        proxy = parse_trojan(line)
                        if proxy and proxy.get('host') and proxy.get('port'):
                            all_proxies.append(proxy)

        try:
            start_check(url)
        except Exception as e:
            logger.debug(f"解析订阅失败 {url}: {e}")
        bar.update(1)

def test_proxy_connectivity(proxy):
    """测试代理连通性"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((proxy['host'], proxy['port']))
        sock.close()
        return result == 0
    except:
        return False

if __name__=='__main__':
    output_file = pre_check()
    list_tg = get_config()
    logger.info('读取config成功')

    # 循环获取频道订阅链接
    url_list = []
    for channel_url in list_tg:
        temp_list = get_channel_http(channel_url)
        url_list.extend(temp_list)

    logger.info(f'开始解析 {len(url_list)} 个订阅链接')
    thread_max_num = threading.Semaphore(32)  # 32线程
    bar = tqdm(total=len(url_list), desc='解析订阅：')
    thread_list = []

    for url in url_list:
        # 为每个订阅URL创建线程
        t = threading.Thread(target=parse_subscription, args=(url, bar))
        thread_list.append(t)
        t.setDaemon(True)
        t.start()

    for t in thread_list:
        t.join()
    bar.close()

    logger.info(f'解析完成，共获得 {len(all_proxies)} 个代理配置')

    # 去重
    unique_proxies = []
    seen = set()
    for proxy in all_proxies:
        key = f"{proxy.get('host')}:{proxy.get('port')}"
        if key not in seen:
            seen.add(key)
            unique_proxies.append(proxy)

    logger.info(f'去重后剩余 {len(unique_proxies)} 个代理，开始测试连通性...')

    # 多线程测试代理连通性
    max_workers = 20
    target_count = min(50, len(unique_proxies))  # 最多测试50个

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 限制测试数量，避免测试时间过长
        test_proxies = unique_proxies[:100] if len(unique_proxies) > 100 else unique_proxies

        future_to_proxy = {
            executor.submit(test_proxy_connectivity, proxy): proxy
            for proxy in test_proxies
        }

        # 使用进度条显示测试进度
        test_bar = tqdm(total=len(test_proxies), desc='测试连通性：')

        for future in as_completed(future_to_proxy):
            proxy = future_to_proxy[future]
            try:
                if future.result():
                    working_proxies.append(proxy)
                    logger.info(f"✓ 发现可用代理: {proxy['host']}:{proxy['port']} ({proxy['type']})")

                    if len(working_proxies) >= target_count:
                        # 取消剩余的任务
                        for remaining_future in future_to_proxy:
                            if not remaining_future.done():
                                remaining_future.cancel()
                        break
            except Exception as e:
                logger.debug(f"测试代理失败: {e}")
            finally:
                test_bar.update(1)

        test_bar.close()

    logger.info(f'连通性测试完成，找到 {len(working_proxies)} 个可用代理')

    # 保存到JSON文件 - 只保留可用的代理
    result = {
        'update_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'count': len(working_proxies),
        'proxies': working_proxies,
        'source': 'collectSub-tested'
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f'结果已保存到 {output_file}，共 {len(working_proxies)} 个可用代理')
