from rest_framework.views import APIView
from rest_framework.response import Response
from .models import User
from rest_framework.generics import CreateAPIView
from .serializers import UserCreateSerializer


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
