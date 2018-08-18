import random
from utils.ytx_sdk.sendSMS import CCP
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from django_redis import get_redis_connection


class SMSCodeView(APIView):
    '''
        短信验证码
    '''

    def get(self, request, mobile):
        '''
            创建手机验证码
            :param request: 从请求报文中接收的数据
            :param mobile: 手机号
            :return: 是否创建成功
        '''
        # 获取redis的连接
        redis_cli = get_redis_connection('verify_code')
        # 检查是否在60s内有发送记录
        sms_flag = redis_cli.get('sms_flag_' + mobile)
        if sms_flag:
            raise serializers.ValidationError('请不要频繁获取验证码')
        # 生成短信验证码
        sms_code = str(random.randint(100000, 999999))
        # 保存短信验证码与发送记录
        # 设置带有效期的数据,单位为秒
        # 存验证码,过期 时间为300秒
        # redis_cli.setex('sms_code_' + mobile, 300, sms_code)
        # 存发送标记,过期时间为60秒
        # redis_cli.setex('sms_flag_' + mobile, 60, 1)
        # 发送短信
        # CCP.sendTemplateSMS(mobile, sms_code, 5, 1)

        # 优化redis交互,减少通信的次数,管道pipeline
        redis_pl = redis_cli.pipeline()
        redis_cli.setex('sms_code_' + mobile, 300, sms_code)
        redis_cli.setex('sms_flag_' + mobile, 60, 1)
        redis_pl.execute()
        print(sms_code)

        return Response({'message': 'OK'})
