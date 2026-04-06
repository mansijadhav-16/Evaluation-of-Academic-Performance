import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mansi'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'mansi'
    MYSQL_DB = 'academic_performance'
    WTF_CSRF_ENABLED = True
    EMAIL_USER = 'vikasvishwakarma10294@gmail.com'
    EMAIL_PASS = 'kdok hrve hbya hxly'
