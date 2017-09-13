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
from configparser import ConfigParser

from coordTransform_utils import bd09_to_gcj02, bd09_to_wgs84


class Crawler:
    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.csv_path = "./db/" + datetime.datetime.now().strftime("%Y%m%d")
        os.makedirs(self.csv_path, exist_ok=True)
        self.csv_name = self.csv_path + "/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.db_name = "file:database?mode=memory&cache=shared"
        self.lock = threading.Lock()
        self.total = 0
        self.done = 0
        self.bikes_count = 0
        cfg = ConfigParser()
        cfg.read('config.ini', encoding='utf-8')
        self.config = cfg

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

    def coord_transform(self, lng, lat):
        coord = self.config.get("DEFAULT", "coord")
        if coord == "bd-09":
            return lng, lat
        if coord == "gcj02":
            return bd09_to_gcj02(lng, lat)
        if coord == "WGS84":
            return bd09_to_wgs84(lng, lat)

    def request(self, headers, args, url):
        response = requests.request(
            "GET", url, headers=headers,
            timeout=self.config.getint("DEFAULT", "timeout"), verify=False
        )

        if response.status_code!=200:
            print("出错咯！", response.text)

            if "无效的token" in response.text:
                os._exit(-1)
            return

        with self.lock:
            with self.connect_db() as c:
                try:
                    decoded = json.loads(response.text)['msg']
                    self.done += 1
                    for x in decoded:
                        self.bikes_count += 1
                        x_lng, x_lat = self.coord_transform(x['lng'], x['lat'])

                        if x['brand'] == 'ofo':
                            c.execute("INSERT OR IGNORE INTO ofo VALUES (%d,'%s',%f,%f)" % (
                                int(time.time()) * 1000, x['id'], x_lat, x_lng))
                        else:
                            c.execute("INSERT OR IGNORE INTO mobike VALUES (%d,'%s',%f,%f)" % (
                                int(time.time()) * 1000, x['id'], x_lat, x_lng))

                    timespent = datetime.datetime.now() - self.start_time
                    percent = self.done / self.total
                    total = timespent / percent
                    print("位置 %s, 未去重单车数量 %s, 进度 %0.2f%%, 速度 %0.2f个/分钟, 总时间 %s, 剩余时间 %s" % (
                        args, self.bikes_count, percent * 100, self.done / timespent.total_seconds() * 60, total, total - timespent))
                except Exception as ex:
                    print(ex)

    def connect_db(self):
        return sqlite3.connect(self.db_name, uri=True)

    def start(self):
        while True:
            self.__init__()

            try:
                with self.connect_db() as c:
                    c.execute(self.generate_create_table_sql('ofo'))
                    c.execute(self.generate_create_table_sql('mobike'))
            except Exception as ex:
                print(ex)
                pass

            executor = ThreadPoolExecutor(max_workers=self.config.getint('DEFAULT','workers'))
            print("Start")

            self.total = 0
            top_lng, top_lat = self.config.get("DEFAULT","top_left").split(",")
            bottom_lng, bottom_lat = self.config.get("DEFAULT", "bottom_right").split(",")
            lat_range = np.arange(float(top_lat), float(bottom_lat), -self.config.getfloat('DEFAULT','offset'))
            for lat in lat_range:
                lng_range = np.arange(float(top_lng), float(bottom_lng), self.config.getfloat('DEFAULT','offset'))
                for lon in lng_range:
                    self.total += 1
                    executor.submit(self.get_nearby_bikes, (lat, lon, self.config.getint('DEFAULT','cityid'), self.config.get('DEFAULT','token')))

            executor.shutdown()
            self.group_data()

            if not self.config.getboolean("DEFAULT", 'always_run'):
                break

            waittime = self.config.getint("DEFAULT", 'wait_time')
            print("等待%s分钟后继续运行" % waittime)
            time.sleep(waittime * 60)

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
        conn = self.connect_db()

        self.export_to_csv(conn, "mobike")
        self.export_to_csv(conn, "ofo")

    def export_to_csv(self, conn, brand):
        df = pd.read_sql_query("SELECT * FROM %s" % brand, conn, parse_dates=True)
        print(brand, "去重后数量", len(df))
        df['Time'] = pd.to_datetime(df['Time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Chongqing')
        compress = None
        csv_file = self.csv_name + "-" + brand + ".csv"
        if self.config.getboolean("DEFAULT","compress"):
            compress = 'gzip'
            csv_file = self.csv_name + "-" + brand + ".csv.gz"

        df.to_csv(csv_file, header=False, index=False, compression=compress)

Crawler().start()
print("完成")
