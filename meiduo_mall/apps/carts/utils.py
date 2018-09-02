from django_redis import get_redis_connection
from utils import meiduopickle


# 获取cookie信息
def merge_cart_cookie2redis(request, response, user_id):
    """
    读取cookie中的购物车数据,保存到redis中
    :param request:用于读取cookie中的数据
    :param response:合并完成后,删除cookie中的数据
    :param user_id:当前登录的用户的id
    :return:response
    """
    # 读取cookie
    cart = request.COOKIES.get('cart')
    if not cart:
        return response
    cart_dict = meiduopickle.loads(cart)

    # 向redis中写入数据
    # 连接redis
    redis_cli = get_redis_connection('carts')

    # 遍历数据
    for sku_id, item in cart_dict.items():
        # 向redis-hash中写入数据
        redis_cli.hset('cart%d' % user_id, sku_id, item.get('count'))
        # 向set中写选中状态,
        if item.get('selected'):
            redis_cli.sadd('cart_selected%d' % user_id, sku_id)
        else:
            redis_cli.srem('cart_selected%d' % user_id, sku_id)

    # 删除cookie中的数据
    response.delete_cookie('cart')

    return response
