import sys
import os
import datetime
from loguru import logger

# 直接使用当前目录存储代理数据
output_file = 'collected_proxies.json'

@logger.catch
def pre_check():
    # 简化初始化，不再创建复杂的文件夹结构
    logger.info('初始化完成')
    return output_file


        
# pre_check()
  



