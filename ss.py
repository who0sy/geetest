import io
import time
from pyquery import PyQuery as pq
from io import  BytesIO
import logging
from PIL import Image
import random, base64, re
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
import  time


class CrackGeetest():

    def __init__(self, url, proxy, word, searchId, bowtonID):

        self.url = url
        self.word = word
        self.proxy = proxy
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--proxy-server=%s' % self.proxy)
        # self.browser = webdriver.Chrome(chrome_options=chrome_options, executable_path='D:\\chromedriver')
        self.browser = webdriver.Chrome(chrome_options=chrome_options)
        self.wait = WebDriverWait(self.browser, 80)
        self.browser.set_page_load_timeout(40)
        self.searchId = searchId # 搜索框的ID，用于定位
        self.bowtonID = bowtonID # 点击按钮的ID，用于定位
        self.threshold = 60  # 验证码图片对比中RGB的差值，可调
        self.left = 50  # 验证码图片的对比中的起始坐标，即拖动模块的右边线位置
        self.deviation = 7  # 误差值，这个值是多次测试得出的经验值
        self.page_count = []

    def open(self):
        """
        # 打开浏览器,并输入查询内容
        """
        self.browser.maximize_window()
        self.browser.get(self.url)
        if '无法访问此网站' in self.browser.page_source or '未连接到互联网' in self.browser.page_source or '该网页无法正常运作' in self.browser.page_source:
            self.browser.quit()
        keyword = self.wait.until(EC.presence_of_element_located((By.ID, self.searchId)))
        bowton = self.wait.until(EC.presence_of_element_located((By.ID, self.bowtonID)))
        try:
            keyword.send_keys(self.word)
        except:
            keyword.send_keys(self.word)
        try:
            bowton.send_keys(Keys.ENTER)
        except:
            bowton.send_keys(Keys.ENTER)

    def get_slider(self):
        """
        获取滑块
        :return: 滑块对象
        """
        slider = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'geetest_slider_button')))
        return slider

    def get_image(self):
        """
        从网页的网站截图中，截取验证码图片
        :return: 验证码图片对象
        """
        times = random.uniform(3, 5)
        times = round(times, 2)
        time.sleep(times)
        bg_js = 'return document.getElementsByClassName("geetest_canvas_bg geetest_absolute")[0].toDataURL("image/png");'
        fullbg_js = 'return document.getElementsByClassName("geetest_canvas_fullbg geetest_fade geetest_absolute")[0].toDataURL("image/png");'
        # slice 执行 JS 代码并拿到图片 base64 数据
        bg_info = self.browser.execute_script(bg_js)  # 执行js文件得到带图片信息的图片数据
        bg_base64 = bg_info.split(',')[1]  # 拿到base64编码的图片信息
        bg_bytes = base64.b64decode(bg_base64)  # 转为bytes类型
        bg_image = Image.open(BytesIO(bg_bytes)) # image读取图片信息
        fullbg_info = self.browser.execute_script(fullbg_js)  # 执行js文件得到带图片信息的图片数据
        fullbg_base64 = fullbg_info.split(',')[1]  # 拿到base64编码的图片信息
        fullbg_bytes = base64.b64decode(fullbg_base64)  # 转为bytes类型
        fullbg_image = Image.open(BytesIO(fullbg_bytes)) # image读取图片信息
        return bg_image,fullbg_image

    def get_distance(self,image1,image2):
        """
        拿到滑动验证码需要移动的距离
        :param image1: 没有缺口的图片对象
        :param image2: 带缺口的图片对象
        :return: 需要移动的距离
        """
        i = 0
        for i in range(self.left, image1.size[0]):
            for j in range(image1.size[1]):
                rgb1 = image1.load()[i, j]
                rgb2 = image2.load()[i, j]
                res1 = abs(rgb1[0] - rgb2[0])
                res2 = abs(rgb1[1] - rgb2[1])
                res3 = abs(rgb1[2] - rgb2[2])
                if not (res1 < self.threshold and res2 < self.threshold and res3 < self.threshold):
                    distance = i -self.deviation
                    return distance
        logging.debug('未识别出验证码中的不同位置，或图片定位出现异常')
        return i  # 如果没有识别出不同位置，则象征性的滑动，以刷新下一张验证码

    def get_track(self,distance):
        """
        :param distance:
        :return: 滑动轨迹
        """
        track = []
        current = 0
        mid = int(distance * round(random.uniform(0.6, 0.7), 2))
        jiansu = distance - mid  # 需要减速的距离
        # 计算间隔
        t = 0.2
        # 初速度
        v = 0
        while current < distance:
            if current < mid:
                # 设置加速度动态变化
                # Chrome 浏览器的加速度
                ap = random.uniform(3, 5)
                times = round(ap, 2)
                a = times
                # 初速度v0
                v0 = v
                v = v0 + a * t
                move = v0 * t + 1 / 2 * a * t * t + 0.5
                # 当前位移
                current += move
                # 加入轨迹
                track.append(round(move))
            else:
                a = -1 * (v * v) / (2 * jiansu)
                v0 = v
                v = v0 + a * t
                if distance > 120:
                    move = v0 * t + 1 / 2 * a * t * t  - 1.5
                elif distance <= 120 and distance >= 60:
                    move = v0 * t + 1 / 2 * a * t * t - 1
                else:
                    move = v0 * t + 1 / 2 * a * t * t - 0.5
                if move < 1:
                    move = 1
                current += move
                track.append(round(move))
        return track

    def move_to_gap(self, slider, track):
        """
        拖动滑块到缺口处
        :param slider: 滑块
        :param track: 轨迹
        :return:
        """
        ActionChains(self.browser).click_and_hold(slider).perform()
        for x in track:
            ActionChains(self.browser).move_by_offset(xoffset=x, yoffset=0).perform()
        time.sleep(0.5)
        ActionChains(self.browser).release().perform()

    def check_html(self, html):
        if 'geetest_success_radar_tip_content' in html:
            Select(self.browser.find_element_by_id("clrq")).select_by_index(2)
            return True
        else:
            return False

    def next_page(self):
        """翻页"""
        first_html = self.browser.page_source
        self.page_count.append(first_html)
        try:
            next_page = re.findall('class="(.*?)">下一页</a>', first_html)[0]
        except:
            next_page = ''
        if next_page and '暂无搜索数据' not in first_html:
            for i in range(1, 10):
                self.browser.find_element_by_class_name('next').click()
                info = self.browser.page_source
                self.page_count.append(info)
                next_pages = re.findall('class="(.*?)">下一页</a>', info)[0]
                if 'disabled' in next_pages:  # disabled 在下一页的class里面，就没有下一页
                    return self.page_count
                times = random.uniform(1, 2)
                times = round(times, 2)
                time.sleep(times)
        else:
            return False

    def again_crack(self):
        image1, image2 = self.get_image()
        distance = self.get_distance(image1, image2)
        print(distance)
        track = self.get_track(distance)
        print(track)
        slider = self.get_slider()
        self.move_to_gap(slider, track)
        time.sleep(0.12)
        ActionChains(self.browser).move_by_offset(xoffset=-3, yoffset=0).perform()
        ActionChains(self.browser).move_by_offset(xoffset=3, yoffset=0).perform()
        time.sleep(0.21)
        ActionChains(self.browser).release().perform()
        times = random.uniform(2, 4)
        times = round(times, 1)
        time.sleep(times)
        html = self.browser.page_source
        res = self.check_html(html)
        print('检测html是否滑动成功', res)
        if res == True:
            ress = self.next_page()
            if ress == False:
                self.browser.quit()
                return [html]
            else:
                self.browser.quit()
                return self.page_count
        else:
            raise print('滑动失败')


    def crack(self):
        """
        程序运行流程。。。
        :return:
        """
        self.open()
        button = self.get_slider()
        button.click()
        image1,image2 = self.get_image()
        distance = self.get_distance(image1,image2)
        print(distance)
        track = self.get_track(distance)
        print(track)
        slider = self.get_slider()
        self.move_to_gap(slider, track)
        time.sleep(0.12)
        ActionChains(self.browser).move_by_offset(xoffset=-3, yoffset=0).perform()
        ActionChains(self.browser).move_by_offset(xoffset=3, yoffset=0).perform()
        time.sleep(0.21)
        ActionChains(self.browser).release().perform()
        times = random.uniform(2, 4)
        times = round(times, 1)
        time.sleep(times)
        html = self.browser.page_source
        res = self.check_html(html)
        print('检测html是否滑动成功', res)
        if res == True:
            ress = self.next_page()
            if ress == False:
                self.browser.quit()
                return [html]
            else:
                self.browser.quit()
                return self.page_count
        else:
            retry_time = 3
            while retry_time > 0:
                try:
                    result = self.again_crack()
                    return result
                except:
                    retry_time -= 1

if __name__ == '__main__':
    url = 'https://www.cods.org.cn/'
    left = 57  # 起始位置
    deviation = 7  # 偏移量，误差
    crack = CrackGeetest(url, word='上海绿化', proxy='http://61.190.102.10:39842', searchId='checkContent_index',
                         bowtonID='checkBtn')
    html_list = crack.crack()
    if html_list:
        n = 0
        for html in html_list:
            soup = pq(html)
            div_list = soup('.has-img').items()
            for div in div_list:
                n += 1
                div = pq(div)
                text = div.text()
                try:
                    if '经营状态' in text:
                        name = text.split('经营状态：')[0].replace('\n', '').strip()
                    else:
                        name = text.split('统一社会信用代码：')[0].replace('\n', '').strip()
                except:
                    name = ''
                try:
                    status = re.findall('经营状态：(.*?)统一社会信用代码：', text, re.S | re.I | re.M)[0].strip()
                except:
                    status = ''
                try:
                    creditcode = re.findall('统一社会信用代码：(.*?)成立时间：', text, re.S | re.I | re.M)[0].strip()
                except:
                    try:
                        creditcode = re.findall('统一社会信用代码：(.*?)成立日期：', text, re.S | re.I | re.M)[0].strip()
                    except:
                        creditcode = ''
                try:
                    addresstel = re.findall('注册地址：(.*?)经营期限：', text, re.S | re.I | re.M)[0].strip()
                except:
                    addresstel = ''
                print(name)
                print(status)
                print(creditcode)
                print(addresstel)
        print('数量',n)
