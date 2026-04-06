import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mansi'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'yourmysqlpassword'
    MYSQL_DB = 'academic_performance'
    WTF_CSRF_ENABLED = True
    EMAIL_USER = 'yourgmailaddress@gmail.com'
    EMAIL_PASS = 'your gmail account app password'
