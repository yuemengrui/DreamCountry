import logging
from logging.handlers import RotatingFileHandler
import redis
from flask import Flask
from flask import g
from flask import render_template
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Session
from config import config_dict


# 创建SQLAlchemy对象
db = SQLAlchemy()
redis_store = None


def create_app(config_name):
    # 创建Flask应用程序实例
    app = Flask(__name__)

    # 获取配置类
    config_cls = config_dict[config_name]

    # 加载项目配置信息
    app.config.from_object(config_cls)

    # 项目日志配置
    setup_logging(config_cls.LOG_LEVEL)

    # db对象关联app
    db.init_app(app)

    # 创建redis链接对象
    global redis_store
    redis_store = redis.StrictRedis(host=config_cls.REDIS_HOST, port=config_cls.REDIS_PORT,decode_responses=True)

    # 为Flask项目开启CSRF保护
    CSRFProtect(app)

    # 创建Session对象
    Session(app)

    @app.after_request
    def after_request(response):
        # 1. 在服务器端生成csrf_token并保存起来
        csrf_token = generate_csrf()
        # 2. 告诉浏览器生成的csrf_token
        response.set_cookie("csrf_token", csrf_token)
        return response

    # 注册蓝图
    from info.modules.index import index_blu
    app.register_blueprint(index_blu)

    from info.modules.passport import passport_blu
    app.register_blueprint(passport_blu, url_prefix='/passport')

    from info.modules.news import news_blu
    app.register_blueprint(news_blu, url_prefix='/news')

    from info.modules.profile import profile_blu
    app.register_blueprint(profile_blu, url_prefix='/user')

    from info.modules.admin import admin_blu
    app.register_blueprint(admin_blu, url_prefix='/admin')

    # 添加自定义过滤器
    from info.utils.commons import do_rank_class, do_news_status
    app.add_template_filter(do_rank_class, 'rank_class')
    app.add_template_filter(do_news_status, 'news_status')

    from info.utils.commons import login_user_data
    @app.errorhandler(404)
    @login_user_data
    def handle_page_not_found(e):
        user = g.user
        return render_template("news/404.html", user=user)

    return app


def setup_logging(log_level):
    """日志相关配置"""
    # 设置日志的记录等级
    logging.basicConfig(level=log_level)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)