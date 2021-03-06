#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Author: Youshumin
@Date: 2019-11-29 09:51:03
@LastEditors: YouShumin
@LastEditTime: 2020-04-01 16:55:52
@Description: 
'''
from functools import wraps
from oslo.web import httpclient
from tornado import gen
from configs.setting import CHECK_PERMISSION_URI
import logging

LOG = logging.getLogger(__name__)


@gen.coroutine
def async_check_permission(check_path, check_auth, check_method):
    """
        异步验证权限接口
    """
    req_data = dict(check_auth=check_auth,
                    check_path=check_path,
                    check_method=check_method)
    req = httpclient.AsyncRequest(url=CHECK_PERMISSION_URI,
                                  method="POST",
                                  **req_data)
    yield req.fetch()
    reps_data = req.resp
    raise gen.Return(reps_data)


def check_request_permission():
    """
        验证权限装饰器
    """
    def wraps_fun(func):
        @wraps(func)
        @gen.coroutine
        def wrapper(self, *args, **kwargs):
            check_path = self.request.path
            check_method = self.request.method
            check_auth = self.request.headers.get('authorization', None)
            if not check_auth:
                self.send_fail(msg="没有登陆", code=400, status=400)
                return
            if check_auth and check_method and check_auth:
                check_permission = yield async_check_permission(
                    check_auth=check_auth,
                    check_path=check_path,
                    check_method=check_method)
                LOG.debug(check_permission)
                if check_permission.get("statusCode", None) == 200:
                    func(self, *args, **kwargs)
                    return
            # return func(self, *args, **kwargs)
            self.send_fail(msg="没有权限", code=403, status=403)
            return

        return wrapper

    return wraps_fun


def WebRequestDataLog(func):
    """
        记录请求方法, 请求路径, 请求数据
        方便调试
    """
    @wraps(func)
    @gen.coroutine
    def wrapper(self, *args, **kwargs):
        req_data = self.request_body()
        req_path = self.request.path
        req_method = self.request.method
        LOG.info("req_method: %s,req_path: %s, req_data: %s", req_method,
                 req_path, req_data)
        return func(self, *args, **kwargs)

    return wrapper