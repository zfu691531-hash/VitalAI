# -*- coding: utf-8 -*-
"""
通用表格逻辑组合式函数
========================
封装表格页面通用的分页、搜索、筛选状态管理：
- pagination: { page, pageSize, total }
- searchKeyword: 搜索关键词
- filters: 筛选条件对象
- loading: 加载状态
- fetchData(): 请求列表数据
- handleSearch(): 搜索
- handlePageChange(): 翻页
- handleSizeChange(): 切换每页条数
减少各列表页面的重复代码。
"""
