共享单车地图爬虫
====================

该爬虫为[单车地图](http://dancheditu.com)的Python演示代码，具备以下功能：
* 支持ofo和摩拜
* 多线程爬取
* 自动去重
* 按照ofo和摩拜输出对应的csv文件，存放在db/【日期】/【日期】-【时间】-【品牌】.csv文件内

运行环境：
* Python3

运行前请联系微信bcdata获取token，内置的token为演示用，单车位置是真实的，ID是随机的。

运行：
```
pip3 install -r requirements.txt
python3 crawler.py
```