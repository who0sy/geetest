import base64
import time
from io import BytesIO
import PIL.Image as image

import numpy as np
from PIL import Image, PngImagePlugin, ImageChops
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium_spider import SeleniumSpider


class Crack(object):

    def __init__(self, url, chromedriver_path, timeout=100, seconds=1,
                 full_image="full_captcha.png",
                 unfull_image="unfull_captcha.png"):
        self.url = url
        self.timeout = timeout
        self.browser = SeleniumSpider(path=chromedriver_path, max_window=True)
        self.wait_browser = WebDriverWait(self.browser, timeout=self.timeout)

        self.query_input_id = "checkContent_index"
        self.query_input_button = "checkBtn"

        self.full_image = full_image
        self.unfull_image = unfull_image

        self.seconds = seconds

        self.table = []
        for i in range(256):
            if i < 50:
                self.table.append(0)
            else:
                self.table.append(1)

    def get_images(self):
        """
        获取验证码图片
        :return: 图片的location信息(Base64)
        """
        time.sleep(1)

        # 遍历页面是否匹配有geetest_canvas_slice
        self.browser.web_driver_wait_ruishu(10, "class", 'geetest_canvas_slice')

        # 执行背景图抓取js命令
        fullgb = self.browser.execute_js('document.getElementsByClassName("geetest_canvas_bg geetest_'
                                         'absolute")[0].toDataURL("image/png")')["value"]
        # 执行缺口图抓取js命令
        bg = self.browser.execute_js('document.getElementsByClassName("geetest_canvas_fullbg geetest_fade'
                                     ' geetest_absolute")[0].toDataURL("image/png")')["value"]
        return bg, fullgb

    def get_decode_image(self, filename, location_list):
        """
        解码base64数据
        """
        _, img = location_list.split(",")
        img = base64.decodebytes(img.encode())
        new_im: PngImagePlugin.PngImageFile = image.open(BytesIO(img))

        # new_im.convert("RGB")
        # new_im.save(filename)

        return new_im

    def compute_gap(self, img1, img2):
        """计算缺口偏移, 结果-7"""
        # 将图片修改为RGB模式
        img1 = img1.convert("RGB")
        img2 = img2.convert("RGB")

        # 计算差值
        diff = ImageChops.difference(img1, img2)

        # 灰度图
        diff = diff.convert("L")

        # 二值化
        diff = diff.point(self.table, '1')

        # 缺口在滑块右侧，设定遍历初始横坐标left为43
        left = 43

        # 这里做了优化为减少误差 纵坐标的像素点大于5时才认为是找到
        # 防止缺口有凸起时有误差
        for w in range(left, diff.size[0]):
            lis = []
            for h in range(diff.size[1]):
                if diff.load()[w, h] == 1:
                    lis.append(w)
                if len(lis) > 5:
                    return w

    def move_to_gap(self, track):
        """移动滑块到缺口处"""
        slider = self.wait_browser.until(EC.presence_of_element_located((By.CLASS_NAME, 'geetest_slider_button')))
        ActionChains(self.browser).click_and_hold(slider).perform()

        while track:
            x = track.pop(0)
            ActionChains(self.browser).move_by_offset(xoffset=x, yoffset=0).perform()
            time.sleep(0.02)

        ActionChains(self.browser).release().perform()

    def crack(self, keyword):
        self.open_browser_and_query(keyword)  # 打开浏览器并且输入查询关键字

        bg_location_base64, fullbg_location_64 = self.get_images()  # 得到背景图及带缺口的验证码图片的base64 信息

        # 根据位置对图片进行合并还原
        bg_img = self.get_decode_image(self.unfull_image, bg_location_base64)
        fullbg_img = self.get_decode_image(self.full_image, fullbg_location_64)

        # 计算缺口偏移
        gap = self.compute_gap(fullbg_img, bg_img)
        print("缺口位置", gap)

        # 获取移动轨迹
        track = self.get_track(gap - 7, self.seconds, self.ease_out_quart)
        print("滑动轨迹", track)

        # 模拟人的行为，拖动滑块，完成验证
        self.move_to_gap(track)

    def open_browser_and_query(self, keyword):
        """
        打开浏览器，并输入查询内容，出现滑块验证码
        :param keyword:
        :return:
        """
        self.browser.get(self.url)

        query_input = self.wait_browser.until(
            EC.presence_of_element_located((By.ID, self.query_input_id)))  # 查询关键字的input标签对象
        query_input.send_keys(keyword)

        query_button = self.wait_browser.until(
            EC.presence_of_element_located((By.ID, self.query_input_button)))  # 查看关键字的按钮
        query_button.click()

    def get_track(self, distance, seconds, ease_func):
        """
        根据轨迹离散分布生成  # 参考文档  https://www.jianshu.com/p/3f968958af5a
        :param distance: 缺口位置-7
        :param seconds: 时间
        :param ease_func: 生成函数
        :return:
        """
        distance += 20  # 加20是保证在滑动时先超过缺口位置然后在慢慢还原到正确位置
        tracks = [0]
        offsets = [0]

        for t in np.arange(0.0, seconds, 0.1):
            ease = ease_func
            offset = round(ease(t / seconds) * distance)
            tracks.append(offset - offsets[-1])
            offsets.append(offset)

        tracks.extend([-3, -2, -3, -2, -2, -2, -2, -1, -0, -1, -1, -1])  # 正好抵消掉前面的加20
        return tracks

    def ease_out_quart(self, x):
        # 四次缓和 - 从零速度加速再减速
        return 1 - pow(1 - x, 4)

    def move_to_gap(self, track):
        """移动滑块到缺口处"""

        # 获取滑块对象
        slider = self.wait_browser.until(EC.presence_of_element_located((By.CLASS_NAME, 'geetest_slider_button')))

        ActionChains(self.browser).click_and_hold(slider).perform()

        while track:
            x = track.pop(0)
            ActionChains(self.browser).move_by_offset(xoffset=x, yoffset=0).perform()
            time.sleep(0.02)

        ActionChains(self.browser).release().perform()


if __name__ == '__main__':
    crack = Crack(
        url="https://www.cods.org.cn/",
        chromedriver_path="/Users/whoosy/Desktop/chromedriver",
        timeout=100
    )
    crack.crack("滑县交通运输局")
