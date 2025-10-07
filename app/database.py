import mysql.connector
from mysql.connector import Error
from app import config

def open_con():
    try:
        con = mysql.connector.connect(
            host=config.DB_HOST,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASS
        )
        if con.is_connected():
            cur = con.cursor(dictionary=True)
            return con, cur
    except Error as e:
        return 'Error', e.msg
    
def open_arms_con():
    try:
        con = mysql.connector.connect(
            host=config.ARMS_DB_HOST,
            database=config.ARMS_DB_NAME,
            user=config.ARMS_DB_USER,
            password=config.ARMS_DB_PASS
        )
        if con.is_connected():
            cur = con.cursor(dictionary=True)
            return con, cur
    except Error as e:
        return 'Error', e.msg