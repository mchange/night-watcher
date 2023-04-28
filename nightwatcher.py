#! /usr/bin/python
# -*- coding:utf-8 _*-

import json
import os
import time
import requests
import sys
import datetime
# 导入pandas模块
import pandas as pd


'''
环境： python 2.7

# 安装依赖
pip install requests

pip install pandas 

pip install numpy 

#############添加自动任务###############
# 编辑工作表
crontab -e

# 每3分钟执行一次
*/3 * * * * python /home/nightwatcher/nightwatcher.py 10.x.x.xs >> /home/nightwatcher/nightwatcher.log

# 查看定时任务
crontab -l
'''

reload(sys)
sys.setdefaultencoding('utf-8')

#配置文件
CONFIG_FILE = '/home/nightwatcher/nightwatcher.json'

CONFIG_JSON = ''

# 监控应用的IP
CHECK_IP = ''

# 此时间范围内不做检测,24小时制
IGNORE_START=0
IGNORE_END=5

# N分钟没变化就预警
DEFAULT_TIME_THRESHOLD = 10 * 60 

# 超过5次异常就预警
DEFAULT_EXCEPTION_THRESHOLD = 5


def load_config():
    # 打开一个文件用于读取文本数据
    with open(CONFIG_FILE, "r") as f:
        # 从文件中读取JSON字符串
        s2 = f.read()
        # 使用json.loads函数将JSON字符串转换为Python对象
        global CONFIG_JSON
        CONFIG_JSON = json.loads(s2)

def save_config():
    # 打开一个文件用于写入文本数据
    with open(CONFIG_FILE, "w") as f:
        # 使用json.dumps函数将元组转换为JSON字符串
        global CONFIG_JSON
        s = json.dumps(CONFIG_JSON)
        # 将JSON字符串写入文件中
        f.write(s.encode("utf-8"))

def check():
    change4ok = CONFIG_JSON.get('change4ok')
    for app in change4ok:
        app_name = app.get('name')
        app_desc = app.get('desc')
        last_check_size_time = app.get("check_size_time", 0) # 时间点
        last_check_size = app.get("check_size", 0)
        log_path = app.get('log')
        check_threshold = app.get('threshold', DEFAULT_TIME_THRESHOLD)

        if not os.path.exists(log_path):
            print(u'%s 不存在' % log_path)
            continue

        now_time = time.time()
        now_size = os.path.getsize(log_path)


        # 两次检查文件大小未变，而且已经超过了报警的临界值，那边就发出警报
        if (last_check_size == now_size) and not time_in_range(IGNORE_START, IGNORE_END):
            # 超出允许时间则预警
            if (now_time-last_check_size_time) >= check_threshold:
                print(u'应用超时%f秒', (now_time-last_check_size_time))
                msg = u"【日志监控】\n应用名:%s\n描述:%s\nIP:%s \n已经近%d分钟没有日志了,请注意!\n%s" % (app_name, app_desc, CHECK_IP, (now_time-last_check_size_time)/60, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                dingmessage(msg)
                app['check_size_time'] = now_time
        else:
            # 文件有变化则更新数据
            app['check_size'] = now_size
            app['check_size_time'] = now_time
        
        # 检查异常次数是否超出范围
        last_check_exception_count = app.get('check_exception_count', 0)
        last_check_exception_time = app.get("check_exception_time", 0)
        now_exception_count = getException(log_path)

        if now_exception_count == last_check_exception_count:
            # 异常个数不变则更新时间
            app['check_exception_time'] = now_time
        else:
            # 如果异常增加了，且不在忽略的时间段内，看看是否在超出了规定时间段内新增异常的次数
            if not time_in_range(IGNORE_START, IGNORE_END) and (now_exception_count-last_check_exception_count) >= DEFAULT_EXCEPTION_THRESHOLD and (now_time-last_check_exception_time) >= check_threshold:
                print(u'应用异常超%f个', (now_exception_count-last_check_exception_count))
                msg = u"【日志监控-异常】\n应用名:%s\n描述:%s\nIP:%s \n近%d分钟已经新增了%d个异常了,请注意!\n%s" % (app_name, app_desc, CHECK_IP, (now_time - last_check_exception_time)/60, (now_exception_count - last_check_exception_count), datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                dingmessage(msg)
                # 预警完成，更新参数，开启下一轮监控
                app['check_exception_time'] = now_time
                app['check_exception_count'] = now_exception_count

# 获取文件中的异常次数
def getException(log_path):
    # 读取文件并创建DataFrame
    df = pd.read_csv(log_path, sep="\0", header=None, names=["word"])
    # 查找文件中包含"Caused by"的行
    mask = df["word"].str.contains("Caused by")
    return len(df[mask])

# 定义一个函数，判断给定的时间是否在开始和结束时间之间
def time_in_range(start, end):
    plus = 0
    if start > end:
        # 跨天了
        plus = 1
    
    # 获取当前时间
    now = datetime.datetime.now()
    # 获取当前日期
    today = now.date()
    # 获取明天日期
    tomorrow = today + datetime.timedelta(days=plus)
    # 构造开始时间和结束时间
    # start_time = datetime.datetime.combine(today, datetime.time(23, 0, 0))
    # end_time = datetime.datetime.combine(tomorrow, datetime.time(8, 0, 0))
    start_time = datetime.datetime.combine(today, datetime.time(start, 0, 0))
    end_time = datetime.datetime.combine(tomorrow, datetime.time(end, 0, 0))

    # 判断当前时间是否在范围内
    return start_time <= now <= end_time

    
def dingmessage(msg):
    # 请求的URL，WebHook地址
    webhook = "https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxxxxxx你的真实tokenxxxxxxxxxxxxxx"
    #构建请求头部
    header = {
        "Content-Type": "application/json",
        "Charset": "UTF-8"
    }
    #构建请求数据
    message ={

        "msgtype": "text",
        "text": {
            "content": msg
        },
        "at": {
            "isAtAll": True
        }

    }
    #对请求的数据进行json封装
    message_json = json.dumps(message)
    #发送请求
    info = requests.post(url=webhook,data=message_json,headers=header)
    #打印返回的结果
    print(info.text)
        
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("*" * 50)
        print("python nightwatcher.py [ip] ")
        print("例如： python nightwatcher.py 10.9.12.11")
        print("*" * 50)
        sys.exit(-1)

    CHECK_IP = sys.argv[1]
    print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    load_config()
    check()
    save_config()
