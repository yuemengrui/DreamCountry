import logging
import redis


class Config(object):
    SECRET_KEY = 'DREAMERWORLD'

    # 数据库配置信息
    SQLALCHEMY_DATABASE_URI = "mysql://root:123456@127.0.0.1:3306/news_web"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # redis配置信息
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379

    # session存储的配置信息
    SESSION_TYPE = "redis"
    SESSION_USE_SIGENR = True
    SECRET_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    PERMANENT_SESSION_LIFETIME = 86400  # session的有效期，单位秒

    # 默认日志等级
    LOG_LEVEL = logging.DEBUG


class DevelopmentConfig(Config):
    """开发模式下的配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产模式下的配置"""
    LOG_LEVEL = logging.WARNING


config_dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}
