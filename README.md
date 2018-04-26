共享单车地图爬虫
====================


# 感谢您的支持
# 此处的python代码可以用于学习用途，但已经无法使用
# 请不要重复问这些问题，已经无法使用！已经无法使用！已经无法使用！已经无法使用！
# 对于研究用途需要数据的，可以加微信bcdata了解

该爬虫为[单车地图](http://www.dancheditu.com)的Python演示代码，具备以下功能：
* 支持ofo和摩拜
* 多线程爬取
* 自动去重
* 坐标系转换
* 按照ofo和摩拜输出对应的csv文件，存放在db/【日期】/【日期】-【时间】-【品牌】.csv文件内
* gzip压缩存储

# 运行环境
* Python3
* Linux/Mac/Windows

运行前请联系微信bcdata获取token，内置的token为演示用，单车位置是真实的，ID是随机的。

请根据你的需要修改配置文件config.ini，请查看内置说明。

## Linux/Mac
* 下载[最新代码](https://github.com/derekhe/bike-crawler/archive/master.zip)并解压
* 修改config.ini确保坐标和区域等参数正确
* 运行：
```
pip3 install -r requirements.txt
python3 crawler.py
```

## Windows
* 下载[最新代码](https://github.com/derekhe/bike-crawler/archive/master.zip)并解压
* 修改config.ini确保坐标和区域等参数正确
* 运行run.bat

# 输出格式

输出格式：CSV

每行格式：时间戳，单车编号，经度，纬度

常见问题，请见[单车地图](http://www.dancheditu.com)
