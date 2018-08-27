from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    # 每页显示的数据条数为2条
    page_size = 2
    # 允许用户指定每页显示多少数据
    page_size_query_param = 'page_size'
    # 指定每页最多显示的数据量为20条
    max_page_size = 20
