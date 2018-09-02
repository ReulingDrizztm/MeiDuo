from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_redis import get_redis_connection
from carts.serializers import CartSKUSerializer

from goods.models import SKU
from orders.serializers import OrderSaveSerializer


class OrderSettlementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 连接redis数据库
        redis_cli = get_redis_connection('carts')
        # 获取商品的编号与数量
        cart_dict = redis_cli.hgetall('cart%d' % request.user.id)
        cart_dict2 = {}
        for k, v in cart_dict.items():
            cart_dict2[int(k)] = int(v)
        # 获取选中的商品
        cart_selected = redis_cli.smembers('cart_selected%d' % request.user.id)
        # 查询商品对象
        skus = SKU.objects.filter(pk__in=cart_selected)
        for sku in skus:
            sku.count = cart_dict2.get(sku.id)
            sku.selected = True

        # 构造响应结果
        serializer = CartSKUSerializer(skus, many=True)

        result = {
            'freight': 10,
            'skus': serializer.data
        }

        # 返回结果
        return Response(result)


class OrderSaveView(CreateAPIView):
    serializer_class = OrderSaveSerializer
    permission_classes = [IsAuthenticated]
