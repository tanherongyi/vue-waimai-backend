import os
# 定义项目根目录
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = 'this is my vue-waimai-backend ym si siht'
    JSON_AS_ASCII = False
    QINIU_ACCESS_KEY = 'yFZl4V8ZlCg8j4-EDV_KLfx1JEi8mMTcvfQnGfBo'
    QINIU_SECRET_KEY = 'wooC5JykXfoKIEhYdxQYsNV1FjZ2EFttes_NR83l'
    ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif']
    TENCENT_MAP_KEY = 'VADBZ-UEALJ-7DVFA-KSCCY-5XTE2-2OFOV'

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    pass

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}