from . import config
from celery import Celery
import os

# 为celery使用django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings")

# 创建对象
app = Celery('meiduo')

# 加载配置
app.config_from_object(config)

# 自动注册celery任务
app.autodiscover_tasks([
    'celery_tasks.sms'
])
