import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'portfolio.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ALPHA_VANTAGE_API_KEY = 'HWWZLX4BAWS7ID80'