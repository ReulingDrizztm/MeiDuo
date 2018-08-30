from rest_framework import serializers, status
from rest_framework.response import Response
from .serializers import CartSerializer, CartSKUSerializer, CartDeleteSerializer, CartSelectAllSerializer
from rest_framework.views import APIView
from utils import meiduopickle
from .constants import CART_COOKIE_EXPIRES
from goods.models import SKU
from django_redis import get_redis_connection


class CartView(APIView):
    def perform_authentication(self, request):
        """
        rest_framework要求进行身份验证,重写方法,不用rest_framework的验证方法
        :param request:
        :return:
        """
        # 取消dispatch()前的身份验证
        pass

    def post(self, request):
        """
        向购物车中添加数据
        :param request: sku_id, count, selected
        :return: sku_id, count, selected
        """
        # 进行反序列化,验证
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取验证后的数据
        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')

        # 保存,验证用户
        try:
            user = request.user
        except:
            user = None

        response = Response(serializer.validated_data)

        if user is None:
            # 读取购物车中的信息
            cart = request.COOKIES.get('cart')
            # 判断购物车中是否有数据
            if cart:
                cart_dict = meiduopickle.loads(cart)
            else:
                cart_dict = {}
            # 判断购物车中是否有此商品
            if sku_id in cart_dict:
                # 如果已经有该商品了,就将数量相加
                count_cart = cart_dict.get(sku_id).get('count')
                cart_dict[sku_id]['count'] = count + count_cart
            else:
                # 如果没有该商品,就保存在cookie中
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': True
                }

            cart_str = meiduopickle.dumps(cart_dict)
            response.set_cookie('cart', cart_str, max_age=CART_COOKIE_EXPIRES)
        else:
            # 用户登录,将数据存入redis
            redis_cli = get_redis_connection('carts')
            redis_cli.hincrby('cart%d' % user.id, sku_id, count)

        return response

    def get(self, request):
        """
        获取购物车中的数据,显示在页面上
        :param request: 无
        :return: id, count, selected, price, name, default_image_url
        """
        # 验证用户是否登录
        try:
            user = request.user
        except:
            user = None

        if user is None:
            # 没有登录,从cookie中读取数据
            cart = request.COOKIES.get('cart')
            if cart:
                cart_dict = meiduopickle.loads(cart)
            else:
                cart_dict = {}

        else:
            # 登录了,从 redis 中读取数据
            redis_cli = get_redis_connection('carts')
            cart_redis = redis_cli.hgetall('cart%d' % user.id)

            cart_dict = {}

            for sku_id in cart_redis:
                cart_dict[int(sku_id)] = {
                    'count': int(cart_redis[sku_id])
                }
            cart_selected = redis_cli.smembers('cart_selected%d' % user.id)
            cart_selected = [int(sku_id) for sku_id in cart_selected]
            for sku_id in cart_dict:
                if sku_id in cart_selected:
                    cart_dict[sku_id]['selected'] = True
                else:
                    cart_dict[sku_id]['selected'] = False

        skus = SKU.objects.filter(id__in=cart_dict.keys())
        for sku in skus:
            sku_dict = cart_dict.get(sku.id)
            sku.count = sku_dict.get('count')
            sku.selected = sku_dict.get('selected')

        serializer = CartSKUSerializer(skus, many=True)

        return Response(serializer.data)

    def put(self, request):
        """
        修改购物车中的数据
        :param request: sku_id, count, selected
        :return: sku_id, count, selected
        """
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')
        selected = serializer.validated_data.get('selected')

        response = Response(serializer.validated_data)

        try:
            user = request.user
        except:
            user = None

        if user is None:
            # 没有登录,从cookie中获取值
            cart = request.COOKIES.get('cart')
            if not cart:
                raise serializers.ValidationError('购物车里什么都没有')

            cart_dict = meiduopickle.loads(cart)

            if sku_id in cart_dict:
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': selected
                }
            cart_str = meiduopickle.dumps(cart_dict)
            response.set_cookie('cart', cart_str, max_age=CART_COOKIE_EXPIRES)

        else:
            # 登录了,从redis中获取值
            redis_cli = get_redis_connection('carts')
            redis_cli.hset('cart%d' % user.id, sku_id, count)

            if selected:
                redis_cli.sadd('cart_selected%d' % user.id, sku_id)
            else:
                redis_cli.srem('cart_selected%d' % user.id, sku_id)

        return response

    def delete(self, request):
        """
        删除购物车里的数据
        :param request: sku_id
        :return: 无
        """
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_id = serializer.validated_data.get('sku_id')

        try:
            user = request.user
        except:
            user = None

        response = Response(status=status.HTTP_204_NO_CONTENT)

        if user is None:
            cart = request.COOKIES.get('cart')
            if not cart:
                raise serializers.ValidationError('购物车无数据，不需要删除')
            cart_dict = meiduopickle.loads(cart)
            if sku_id in cart_dict:
                del cart_dict[sku_id]
            cart_str = meiduopickle.dumps(cart_dict)
            response.set_cookie('cart', cart_str, max_age=CART_COOKIE_EXPIRES)
        else:
            pass

        return response


class CartSelectAllView(APIView):
    """
    购物车全选
    """
    def perform_authentication(self, request):
        # 去掉rest_framework自带的身份验证功能
        pass

    def put(self, request):
        """
        购物车里商品的全部选择和全部取消选择
        :param request: selected
        :return: 无
        """
        serializer = CartSelectAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected = serializer.validated_data.get('selected')

        try:
            user = request.user
        except:
            user = None

        response = Response({'message': 'OK'})

        if user is None:
            cart = request.COOKIES.get('cart')
            if not cart:
                raise serializers.ValidationError('暂无购物车数据')
            cart_dict = meiduopickle.loads(cart)
            for sku_id in cart_dict:
                cart_dict[sku_id]['selected'] = selected
            cart_str = meiduopickle.dumps(cart_dict)
            response.set_cookie('cart', cart_str, max_age=CART_COOKIE_EXPIRES)
        else:
            redis_cli = get_redis_connection('carts')
            sku_ids = redis_cli.hkeys('cart%d' % user.id)
            if selected:
                redis_cli.sadd('cart_selected%d' % user.id, *sku_ids)
            else:
                redis_cli.srem('cart_selected%d' % user.id, *sku_ids)

        return response


