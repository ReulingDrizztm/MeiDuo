from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users import serializers
from .models import User
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from .serializers import UserCreateSerializer, EmailSerializer


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


class EmailView(UpdateAPIView):
    """
    保存用户邮箱
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EmailSerializer

    def get_object(self, *args, **kwargs):
        return self.request.user


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
