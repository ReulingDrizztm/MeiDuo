import os

from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from alipay import AliPay
from orders.models import OrderInfo
from django.conf import settings

from payments.models import Payment


def get_alipay():
    alipay = AliPay(
        appid=settings.ALIPAY_APPID,
        app_notify_url=None,  # 默认回调url
        app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/payments/keys/app_private_key.pem'),
        alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/payments/keys/alipay_public_key.pem'),
        sign_type="RSA2",
        debug=settings.ALIPAY_DEBUG
    )

    return alipay


class AlipayUrlView(APIView):
    """
    提交订单
    """
    def get(self, request, order_id):
        try:
            order = OrderInfo.objects.get(pk=order_id)
        except:
            raise serializers.ValidationError('订单编号无效')
        total_amout = order.total_amount
        alipay = get_alipay()
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_amout),  # 总金额,转字符串
            subject="美多商城支付" + order_id,
            return_url=settings.RETURN_URL
        )

        alipay_url = settings.ALIPAY_URL + order_string

        return Response({'alipay_url': alipay_url})


class PaymentStatusView(APIView):
    """
    支付结果,保存支付宝生成的订单编号
    """

    def put(self, request):
        """
        获取支付宝返回的参数
        :return: trade_id
        """
        data = request.query_params.dict()
        signature = data.pop("sign")

        order_id = data.get('out_trade_no')
        trade_id = data.get('trade_no')

        # 请求支付宝进行验证
        alipay = get_alipay()
        success = alipay.verify(data, signature)
        if success:
            # 如果验证成功,则保存订单编号对应的支付宝交易编号
            Payment.objects.create(
                order_id=order_id,
                trade_id=trade_id
            )
            # 响应
            return Response({'trade_id': trade_id})
        else:
            raise serializers.ValidationError('支付失败')
