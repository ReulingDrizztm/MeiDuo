import re
from django_redis import get_redis_connection
from rest_framework import serializers
from rest_framework_jwt.settings import api_settings
from celery_tasks.email.tasks import send_verify_email
from goods.models import SKU
from .models import Address
from users.models import User


class UserCreateSerializer(serializers.Serializer):
    """
    创建用户序列化器
    """
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(
        # min_length=5,
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

    # 增加token字段
    token = serializers.CharField(label='登录状态token', read_only=True)

    def validate_username(self, value):
        # if not re.search(r'[a-zA-Z]', value):
        #     raise serializers.ValidationError('用户名必须包含字母')
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
        user.mobile = validated_data.get('mobile')
        user.set_password(validated_data.get('password'))
        user.save()

        # 补充生成记录登录状态的token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        user.token = token

        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """
    用户详细信息序列化器
    """

    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'email', 'email_active')


class EmailSerializer(serializers.ModelSerializer):
    """
    邮箱序列化器
    """

    class Meta:
        model = User
        fields = ('id', 'email')
        extra_kwargs = {
            'email': {
                'required': True
            }
        }

    def update(self, instance, validated_data):
        email = validated_data['email']
        instance.email = validated_data['email']
        instance.save()

        # 生成验证链接
        verify_url = instance.generate_verify_email_url()
        # 发送验证邮件
        send_verify_email.delay(email, verify_url)

        return instance


class UserAddressSerializer(serializers.ModelSerializer):
    """
    用户地址序列化器
    """
    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label='省ID', required=True)
    city_id = serializers.IntegerField(label='市ID', required=True)
    district_id = serializers.IntegerField(label='区ID', required=True)

    class Meta:
        model = Address
        exclude = ('user', 'is_deleted', 'create_time', 'update_time')

    def validate_mobile(self, value):
        """
        验证手机号
        """
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def create(self, validated_data):
        """
        保存
        """
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    """
    地址标题
    """

    class Meta:
        model = Address
        fields = ('title',)


class AddUserBrowsingHistorySerializer(serializers.Serializer):
    sku_id = serializers.IntegerField(min_value=1)

    def validate_sku_id(self, value):
        try:
            SKU.objects.get(pk=value)
        except:
            raise serializers.ValidationError('商品编号无效')
        return value

    def create(self, validated_data):
        # 将来序列化器使用时，保存会调用这个方法
        # 将浏览记录保存到Redis中，使用list类型
        redis_cli = get_redis_connection('history')
        # self.context是一个字典，当视图调用序列化器时，会通过这个字典传递数据
        # 默认传递了request对象
        request = self.context.get('request')

        # 当jwt进行登录验证后，会将登录的用户对象user赋值给request对象:request.user=user
        user = request.user
        key = 'history%d' % user.id
        # 获取商品编号
        sku_id = validated_data.get('sku_id')
        # #先删除当前编号
        # redis_cli.lrem(key,0,sku_id)
        # # 存入redis中，放在最前
        # redis_cli.lpush(key, sku_id)
        # #截取，最多只留5个
        # redis_cli.ltrim(key,0,4)
        # 使用管道进行优化，只与redis交互一次
        pl = redis_cli.pipeline()
        pl.lrem(key, 0, sku_id)
        pl.lpush(key, sku_id)
        pl.ltrim(key, 0, 4)
        pl.execute()

        return validated_data
