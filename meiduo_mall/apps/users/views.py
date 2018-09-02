from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.views import ObtainJSONWebToken
from goods.models import SKU
from goods.serializers import SKUSerializer
from .models import User
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from .serializers import UserCreateSerializer, EmailSerializer, AddUserBrowsingHistorySerializer
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from carts.utils import merge_cart_cookie2redis
from . import constants
from . import serializers
from .serializers import UserAddressSerializer


# 统计使用当前用户名的数量
class UsernameCountView(APIView):
    '''
    当前用户名的用户数量统计
    '''

    def get(self, request, username):
        '''
        获取当前用户名的用户数量
        :param request: 从请求报文中获取的信息
        :param username: 用户名
        :return: 用户名和数量
        '''
        count = User.objects.filter(username=username).count()
        print(count)
        return Response({
            'username': username,
            'count': count
        })


# 统计手机号数量
class MobileCountView(APIView):
    '''
    使用当前手机号的用户的数量
    '''

    def get(self, request, mobile):
        '''
        获取使用当前手机号的用户的数量
        :param request: 从请求报文中获取的数据
        :param mobile: 手机号
        :return: 手机号的使用数量
        '''
        count = User.objects.filter(mobile=mobile).count()

        return Response({
            'mobile': mobile,
            'count': count
        })


# 注册
class UserView(CreateAPIView):
    '''
    用户注册
    '''
    serializer_class = UserCreateSerializer


# 用户中心
class UserDetailView(RetrieveAPIView):
    """
    用户详情
    """
    serializer_class = serializers.UserDetailSerializer
    # 指定权限认证,要求登录之后才能访问
    permission_classes = [IsAuthenticated]

    # 当前不需要根据pk查询对象,而是获取登录的用户对象,所以使用get_object方法,这是GenericAPIView视图类的方法,默认根据PK查询对象,如果不想根据主键查询,可以重写该方法
    def get_object(self):
        # 当JWT完成登录验证后,会将对象保存到request对象中
        return self.request.user


# 发送邮件
class EmailView(UpdateAPIView):
    """
    保存用户邮箱
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EmailSerializer

    def get_object(self, *args, **kwargs):
        return self.request.user


# 邮箱验证
class VerifyEmailView(APIView):
    """
    邮箱验证
    """

    def get(self, request):
        # 获取token
        token = request.query_params.get('token')
        if not token:
            return Response({'message': '缺少token'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证token
        user = User.check_verify_email_token(token)
        if user is None:
            return Response({'message': '链接信息无效'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user.email_active = True
            user.save()
            return Response({'message': 'OK'})


# 收货地址
class AddressViewSet(CreateModelMixin, UpdateModelMixin, GenericViewSet):
    """
    用户地址新增与修改
    """
    serializer_class = serializers.UserAddressSerializer
    permissions = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)

    # GET /addresses/
    def list(self, request, *args, **kwargs):
        """
        用户地址列表数据
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
            'addresses': serializer.data,
        })

    # POST /addresses/
    def create(self, request, *args, **kwargs):
        """
        保存用户地址数据
        """
        # 检查用户地址数据数目不能超过上限
        count = request.user.addresses.count()
        if count >= constants.USER_ADDRESS_COUNTS_LIMIT:
            return Response({'message': '保存地址数据已达到上限'}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    # delete /addresses/<pk>/
    def destroy(self, request, *args, **kwargs):
        """
        处理删除
        """
        address = self.get_object()

        # 进行逻辑删除
        address.is_deleted = True
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    # put /addresses/pk/status/
    @action(methods=['put'], detail=True)
    def status(self, request, pk=None):
        """
        设置默认地址
        """
        address = self.get_object()
        request.user.default_address = address
        request.user.save()
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)

    # put /addresses/pk/title/
    # 需要请求体参数 title
    @action(methods=['put'], detail=True)
    def title(self, request, pk=None):
        """
        修改标题
        """
        address = self.get_object()
        serializer = serializers.AddressTitleSerializer(instance=address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# 浏览记录
class UserBrowsingHistoryView(CreateAPIView):
    serializer_class = AddUserBrowsingHistorySerializer
    # 登录判断
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 查询Redis，读取最近浏览记录
        redis_cli = get_redis_connection('history')
        # 获取当前用户所有浏览记录，返回列表[1,2,3,4]
        sku_ids = redis_cli.lrange('history%d' % request.user.id, 0, -1)
        # 查询商品对象
        skus = []
        for sku_id in sku_ids:
            skus.append(SKU.objects.get(pk=sku_id))
        # 输出json
        sku_serializer = SKUSerializer(skus, many=True)
        return Response(sku_serializer.data)


# 登录时合并cookie中的购物车数据到redis中
class UserWebTokenView(ObtainJSONWebToken):
    """
    登录时合并cookie到redis中
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # 如果登录失败,直接返回响应结果
        if 'user_id' not in response.data:
            return response

        # 登录成功,进行数据合并
        user_id = response.data.get('user_id')
        response = merge_cart_cookie2redis(request, response, user_id)

        return response
