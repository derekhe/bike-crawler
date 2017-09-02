import datetime
import json
import os
import os.path
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests


class Crawler:
    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.csv_path = "./db/" + datetime.datetime.now().strftime("%Y%m%d")
        os.makedirs(self.csv_path, exist_ok=True)
        self.csv_name = self.csv_path + "/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.db_name = "./temp.db"
        self.lock = threading.Lock()
        self.total = 0
        self.done = 0
        self.bikes_count = 0

    def get_nearby_bikes(self, args):
        try:
            url = "http://www.dancheditu.com/api/bikes?lat=%s&lng=%s&cityid=%s&token=%s" % (args[0], args[1], args[2], args[3])

            headers = {
                'charset': "utf-8",
                'platform': "4",
                'content-type': "application/x-www-form-urlencoded",
                'user-agent': "MicroMessenger/6.5.4.1000 NetType/WIFI Language/zh_CN",
                'host': "mwx.mobike.com",
                'connection': "Keep-Alive",
                'accept-encoding': "gzip",
                'cache-control': "no-cache"
            }

            self.request(headers, args, url)
        except Exception as ex:
            print(ex)

    def request(self, headers, args, url):
        response = requests.request(
            "GET", url, headers=headers,
            timeout=30, verify=False
        )

        with self.lock:
            with sqlite3.connect(self.db_name) as c:
                try:
                    decoded = json.loads(response.text)['msg']
                    self.done += 1
                    for x in decoded:
                        self.bikes_count += 1
                        if x['brand'] == 'ofo':
                            c.execute("INSERT OR IGNORE INTO ofo VALUES (%d,'%s',%f,%f)" % (
                                int(time.time()) * 1000, x['id'], x['lat'], x['lng']))
                        else:
                            c.execute("INSERT OR IGNORE INTO mobike VALUES (%d,'%s',%f,%f)" % (
                                int(time.time()) * 1000, x['id'], x['lat'], x['lng']))

                    timespent = datetime.datetime.now() - self.start_time
                    percent = self.done / self.total
                    total = timespent / percent
                    print("位置 %s, 单车数量 %s, 进度 %0.2f%%, 速度 %0.2f个/分钟, 总时间 %s, 剩余时间 %s" % (
                        args, self.bikes_count, percent * 100, self.done / timespent.total_seconds() * 60, total, total - timespent))
                except Exception as ex:
                    print(ex)

    def start(self, config):
        if os.path.isfile(self.db_name):
            os.remove(self.db_name)

        try:
            with sqlite3.connect(self.db_name) as c:
                c.execute(self.generate_create_table_sql('ofo'))
                c.execute(self.generate_create_table_sql('mobike'))
        except Exception as ex:
            print(ex)
            pass

        executor = ThreadPoolExecutor(max_workers=config['workers'])
        print("Start")

        self.total = 0
        lat_range = np.arange(config['top_lat'], config['bottom_lat'], -config['offset'])
        for lat in lat_range:
            lng_range = np.arange(config['left_lng'], config['right_lng'], config['offset'])
            for lon in lng_range:
                self.total += 1
                executor.submit(self.get_nearby_bikes, (lat, lon, config['cityid'], config['token']))

        executor.shutdown()
        self.group_data()

    def generate_create_table_sql(self, brand):
        return '''CREATE TABLE {0}
                (
                    "Time" DATETIME,
                    "bikeId" VARCHAR(12),
                    lat DOUBLE,
                    lon DOUBLE,
                    CONSTRAINT "{0}_bikeId_lat_lon_pk"
                        PRIMARY KEY (bikeId, lat, lon)
                );'''.format(brand)

    def group_data(self):
        print("正在导出数据")
        conn = sqlite3.connect(self.db_name)

        self.export_to_csv(conn, "mobike")
        self.export_to_csv(conn, "ofo")

    def export_to_csv(self, conn, brand):
        df = pd.read_sql_query("SELECT * FROM %s" % brand, conn, parse_dates=True)
        df['Time'] = pd.to_datetime(df['Time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Chongqing')
        df.to_csv(self.csv_name + "-" + brand + ".csv", header=False, index=False)


# 配置
# 经纬度请用百度拾取工具拾取，http://api.map.baidu.com/lbsapi/getpoint/
config = {
    # 左边经度
    "left_lng": 103.9213455517,
    # 上边维度
    "top_lat": 30.7828453209,
    # 右边经度
    "right_lng": 104.2178123382,
    # 右边维度
    "bottom_lat": 30.4781772402,
    # 平移量，用于遍历整个区域的最小间隔，请自行调整，必要时可以参考www.dancheditu.com
    # 参数过小则抓取太过于密集，导致重复数据过多
    # 参数过大则抓取太过于稀疏，会漏掉一些数据
    "offset": 0.002,
    # 城市id，请参考http://www.dancheditu.com/的FAQ
    "cityid": 75,
    # 线程数，请合理利用资源，线程数请不要过大，过大服务器会返回错误
    "workers": 100,
    # token，请加微信bcdata付费获取，demo只能提供单车的真实位置，但是id号是随机的
    "token": "demo"
}

Crawler().start(config)
print("完成")
