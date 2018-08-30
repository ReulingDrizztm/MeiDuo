#!/usr/bin/env python
# 到环境变量中查找python
# 文件要想运行，需要指定解释器
# 设置settings.py为环境变量
import sys

sys.path.insert(0, '../')

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings")

import django

django.setup()

# 编写代码：查询所有的商品，生成静态页面

from goods.models import SKU
from celery_tasks.html.tasks import generate_static_sku_detail_html

if __name__ == '__main__':
    skus = SKU.objects.all()
    for sku in skus:
        generate_static_sku_detail_html(sku.id)
