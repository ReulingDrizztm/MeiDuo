from datetime import datetime
from django_redis import get_redis_connection
from rest_framework import serializers
from .models import OrderGoods, OrderInfo
from goods.models import SKU
from django.db import transaction
import time


class OrderSaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderInfo
        fields = ['order_id', 'address', 'pay_method']
        read_only_fields = ['order_id']
        extra_kwargs = {
            'address': {
                'write_only': True,
                'required': True
            },
            'pay_method': {
                'write_only': True,
                'required': True
            }
        }

    def create(self, validated_data):
        user = self.context['request'].user
        with transaction.atomic():
            # 开启事务
            sid = transaction.savepoint()
            # 创建OrderInfo对象
            # order = OrderInfo()
            # order.order_id = datetime.now().strftime('%Y%m%d%H%M%S') + '%09d' % user.id
            # order.user = user
            # order.address = validated_data.get('address')
            # order.total_count = 0
            # order.total_amount = 0
            # order.freight = 10
            # order.pay_method = validated_data.get('pay_method')
            # order.status = user
            # if validated_data.get('pay_method') == 1:
            #     # 当支付方式为货到付款时,订单状态为代发货
            #     order.status = 2
            # else:
            #     # 当支付方式为其他付款方式时,订单状态为待付款
            #     order.status = 1
            #
            # order.save()
            order = OrderInfo.objects.create(
                order_id=datetime.now().strftime('%Y%m%d%H%M%S') + '%09d' % user.id,
                user=user,
                address=validated_data.get('address'),
                total_count=0,
                total_amount=0,
                freight=10,
                pay_method=validated_data.get('pay_method'),
                status=2 if validated_data.get('pay_method') == 1 else 1
            )

            # 查询redis中多有选中的商品
            redis_cli = get_redis_connection('carts')
            # 查询商品及数量
            cart_hash = redis_cli.hgetall('cart%d' % user.id)
            cart_dict = {int(k): int(v) for k, v in cart_hash.items()}
            # 查询选中的商品
            cart_set = redis_cli.smembers('cart_selected%d' % user.id)
            cart_selected = [int(sku_id) for sku_id in cart_set]

            # 3.遍历
            # skus = SKU.objects.filter(pk__in=cart_selected)
            total_count = 0
            total_amount = 0
            for sku_id in cart_selected:
                # 3.1判断库存是否足够,库存不够则抛异常
                # count = cart_dict.get(sku.id)
                while True:
                    sku = SKU.objects.get(pk=sku_id)
                    count = cart_dict.get(sku.id)
                    if sku.stock < count:
                        # 当数据出现异常的时候,回滚到初始状态
                        transaction.savepoint_rollback(sid)
                        raise serializers.ValidationError('库存不足')
                    time.sleep(5)
                    # 3.2修改商品的库存, 销量
                    # sku.stock -= count
                    # sku.sales += count
                    # sku.save()
                    stock_old = sku.stock
                    sales_old = sku.sales
                    stock_new = stock_old - count
                    sales_new = sales_old + count
                    ret = SKU.objects.filter(pk=sku.id, stock=stock_old).update(stock=stock_new, sales=sales_new)
                    print(ret)
                    # 语句会返回受影响的行数,为1或者0
                    if ret == 0:
                        continue
                    # 3.3修改SPU的总销量
                    goods = sku.goods
                    goods.sales += count
                    goods.save()

                    # 3.4创建OrderGoods对象
                    # order_goods = OrderGoods()
                    # order_goods.order = order
                    # order_goods.sku = sku
                    # order_goods.count = count
                    # order_goods.price = sku.price
                    # order_goods.save()
                    order_goods = OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.price
                    )

                    # 3.5计算总金额,总数量
                    total_count += count
                    total_amount += count * sku.price

                    break

            # 4.修改总金额,总数量
            order.total_count = total_count
            order.total_amount = total_amount
            order.save()
            # 当数据成功操作后,提交事务
            transaction.savepoint_commit(sid)

        # 5. 删除redis中选中的商品数据
        pl = redis_cli.pipeline()
        pl.hdel('cart%d' % user.id, *cart_selected)
        pl.srem('cart_selected%d' % user.id, *cart_selected)
        pl.execute()

        return order
