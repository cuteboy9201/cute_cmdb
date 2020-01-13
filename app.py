#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Author: Youshumin
@Date: 2019-08-21 11:13:46
@LastEditors  : YouShumin
@LastEditTime : 2020-01-03 03:09:12
'''
import logging
import logging.config
import os
import sys

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from configs.setting import (ALLOW_HOST, COOKIE_SECRET, HOST, LOGFILE,
                             MQ_SERVER_EXCHANGE, MQ_SERVER_QUEUE,
                             MQ_SERVER_ROUTING_KEY, MQ_URL, PORT, PROJECT_NAME)
from oslo.db.module import mysqlHanlder
from oslo.task.rabbitmq import TornadoAdapter
from task.receive_handler import ReceiveHandle
from tornado import gen
from tornado.log import enable_pretty_logging
from tornado.options import define, options

debug = os.environ.get("RUN_ENV")

LOG = logging.getLogger(__name__)


class LogHandler(object):
    """设置tornado 日志信息 当设置RUN_ENV为prod的时候进行文件输出,否则控制台
       python3 会有问题... 不是大问题, 不在细化研究...使用supervisor管理python
    """
    def __init__(self):
        if debug == "prod":
            define("log_file_prefix", default=LOGFILE)
            define(
                "log_rotate_mode",
                default="time",
            )
            define("log_rotate_when", default="D")
            define("log_rotate_interval", default=1)
            define("log_file_num_backups", default=60)
            define("log_to_stderr", default=False)
        super(LogHandler, self).__init__()


p_version = sys.version_info.major
if p_version == 2:
    LogHandler()


class RouteHandler(object):
    """注册路由"""
    def __init__(self):
        """
        需要配置这里实现注册路由... 
            自动注册路由的方式可以继承 application实现
            我这边是想实现像flask蓝本一样实现注册...所以暂时设置为这样
        """
        from handlers import adminuser
        from handlers import property
        from handlers import userright
        from oslo.web.route import route
        self.route = route
        super(RouteHandler, self).__init__()


class DB(object):
    """初始化数据库"""
    def __init__(self):
        self.db = mysqlHanlder()

    def db_init(self):
        """初始化rbac数据库"""
        from configs.setting import DB_HOST, BD_ECHO, DB_NAME
        self.db.init(dbname=DB_NAME, dburl=DB_HOST, dbecho=BD_ECHO)


class Application(tornado.web.Application, RouteHandler):
    """初始化application"""
    def __init__(self):
        configs = dict(
            # emplate_path=os.path.join(PATH_APP_ROOT, "templates"),
            debug=options.debug,
            cookie_secret=COOKIE_SECRET,
            autoescape=None,
        )
        DB().db_init()
        RouteHandler.__init__(self)
        tornado.web.Application.__init__(self, self.route.get_urls(),
                                         **configs)


class WebApp():
    """应用启动唯一入口"""
    def __init__(self):
        """
            初始化启动信息
                运行环境 debug
                运行ip host
                启动端口 port
        """
        if debug != "prod":
            define("debug", default=True, help="enable debug mode")
            define("allow_host", default=[], help="allow host")
        else:
            define("debug", default=False, help="enable debug mode")
            define("allow_host", default=ALLOW_HOST, help="allow host")
        define("host", default=HOST, help="run on this host", type=str)
        define("port", default=PORT, help="run on this port", type=int)
        self.io_loop = tornado.ioloop.IOLoop.instance()
        LOG.info(options.allow_host)

    @gen.coroutine
    def mq_handler(self, *args, **kwargs):
        ReceiveHandle(args)

    def initmq(self):
        mq = TornadoAdapter(MQ_URL)
        mq.receive(MQ_SERVER_EXCHANGE, MQ_SERVER_ROUTING_KEY, MQ_SERVER_QUEUE,
                   self.mq_handler)

    def run(self):
        enable_pretty_logging()

        self.initmq()

        http_server = tornado.httpserver.HTTPServer(Application(),
                                                    xheaders=True)
        if options.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            http_server.listen(options.port, address=options.host)
            LOG.info("start app [%s] for %s:%s", PROJECT_NAME, options.host,
                     options.port)
        else:
            http_server.listen(options.port, address=options.host)
            LOG.info("start app [%s] for %s:%s", PROJECT_NAME, options.host,
                     options.port)
        try:
            self.io_loop.start()
        except KeyboardInterrupt:
            self.io_loop.stop()

    def stop(self):
        self.io_loop.stop()


def web_app():
    return WebApp()
