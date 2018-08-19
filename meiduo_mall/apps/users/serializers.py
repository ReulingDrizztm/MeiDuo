import re

from django_redis import get_redis_connection
from rest_framework import serializers

from users.models import User


class UserCreateSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(
        min_length=5,
        max_length=20,
        error_messages={
            'min_length': '用户名不能少于5个字符',
            'max_length': '用户名不能多于20个字符'
        }
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=20,
        error_messages={
            'min_length': '密码不能少于8个字符',
            'max_length': '密码不能多于20个字符'
        }
    )
    mobile = serializers.CharField()
    password_qr = serializers.CharField(write_only=True)
    sms_code = serializers.CharField(write_only=True)
    allow = serializers.CharField(write_only=True)

    def validate_username(self, value):
        # 验证用户名是否存在
        count = User.objects.filter(username=value).count()
        if count > 0:
            raise serializers.ValidationError('用户名已存在')

        return value

    def validate_mobile(self, value):
        # 验证手机号码是否存在
        count = User.objects.filter(mobile=value).count()
        if count > 0:
            raise serializers.ValidationError('该手机号码已经注册')

        return value

    def validate_sms_code(self, value):
        if not re.match(r'^\d{6}$', value):
            raise serializers.ValidationError('短信验证码格式错误')
        return value

    def validate_allow(self, value):
        # 验证是否勾选用户协议
        if not value:
            raise serializers.ValidationError('请先勾选同意"美多商城用户使用协议"')
        return value

    def validate(self, attrs):
        # 验证两次密码是否一致
        password = attrs.get('password')
        password_qr = attrs.get('password_qr')
        if password != password_qr:
            raise serializers.ValidationError('两次输入的密码不一致')

        # 验证手机验证码是否正确
        redis_cli = get_redis_connection('verify_code')
        key = 'sms_code_' + attrs.get('mobile')
        sms_code_redis = redis_cli.get(key)
        sms_code_request = attrs.get('sms_code')

        # 判断短信验证码是否存在
        if not sms_code_redis:
            raise serializers.ValidationError('验证码已过期,请重新获取')

        # 强制短信验证码失效
        redis_cli.delete(key)

        # 判断短信验证码是否正确
        if sms_code_redis.decode() != sms_code_request:
            raise serializers.ValidationError('短信验证码错误')

        return attrs

    def create(self, validated_data):
        user = User()
        user.username = validated_data.get('username')
        user.moblie = validated_data.get('mobile')
        user.set_password(validated_data.get('password'))
        user.save()

        return user
