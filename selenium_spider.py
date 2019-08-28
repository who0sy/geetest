import json
import time as time_

from lxml import etree
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options


class SeleniumSpider(WebDriver):
    """基于selenium进一步封装"""

    def __init__(self, path, params=None, max_window=False, *args, **kwargs):
        """
        初始化
        :param path: str selenium驱动路径
        :param params: list driver 附加参数
        :param args: tuple
        :param kwargs:
        """
        self.__path = path
        self.__params = params
        # 初始化
        self.__options = Options()
        self.__options.add_argument('--dns-prefetch-disable')
        self.__options.add_argument('--disable-gpu')  # 谷歌文档提到需要加上这个属性来规避bug
        self.__options.add_argument('disable-infobars')  # 隐藏"Chrome正在受到自动软件的控制"
        # self.__options.add_argument("--proxy-server=http://193.112.55.45:8118")
        # self.__options.add_argument('--headless')
        self.is_maximize_window = max_window  # 是否开启全屏模式

        # 过检测 具体参考文档: https://juejin.im/post/5c62b6d5f265da2dab17ae3c
        self.__options.add_experimental_option('excludeSwitches', ['enable-automation'])

        if params:
            for i in params:
                self.__options.add_argument(i)
        super(SeleniumSpider, self).__init__(executable_path=self.__path, options=self.__options, *args, **kwargs)
        # 过检测准备工作
        self.execute_chrome_protocol_js(
            protocol="Page.addScriptToEvaluateOnNewDocument",
            params={"source": """
           Object.defineProperty(navigator, 'webdriver', {
           get: () => false,
           });"""})
        if self.is_maximize_window:
            self.maximize_window()

        # 规则部分
        self.ID = "id"
        self.XPATH = "xpath"
        self.LINK_TEXT = "link text"
        self.PARTIAL_LINK_TEXT = "partial link text"
        self.NAME = "name"
        self.TAG_NAME = "tag name"
        self.CLASS_NAME = "class name"
        self.CSS_SELECTOR = "css selector"

    def cookies_dict_to_selenium_cookies(self, cookies: dict, domain):
        """
        requests cookies 转换到 selenium cookies
        :param cookies: requests cookies
        :return: selenium 支持的cookies
        """
        temp_cookies = []
        for key, value in cookies.items():
            # requests 有bug 域区分的不是很清楚 手动区分 只限全国电信接口能用
            temp_cookies.append({"name": key, "value": value, "domain": domain})
        return temp_cookies

    # def get(self, url: str, cookies=None, domain=None):
    #     """
    #     请求数据
    #     :param url: 待请求的url
    #     :param cookies: 添加cookies cookies 格式 [{"name": key, "value": value, "domain": domain},...]
    #     :param domain: cookie作用域
    #     :return:
    #     """
    #     super().get(url)
    #     if cookies:
    #         # 执行
    #         if type(cookies) == list:
    #             for cookie in cookies:
    #                 if "name" in cookie.keys() and "value" in cookie.keys() and "domain" in cookie.keys():
    #                     self.add_cookie(cookie)
    #                 else:
    #                     raise TypeError('cookies错误请传入正确格式[{"name": key, "value": value, "domain": domain},...'
    #                                     '] 或者{key: vale,...}')
    #         elif type(cookies) == dict:
    #             if domain:
    #                 for i in self.cookies_dict_to_selenium_cookies(cookies, domain):
    #                     self.add_cookie(i)
    #             else:
    #                 raise ValueError("{key:vale}格式必须传入doamin参数")
    #         # 刷新页面
    #         self.refresh()

    def web_driver_wait_ruishu(self, time: int, rule: str, num: str):
        """
        笨方法 遍历页面匹配
        :param time: 等待时间
        :param rule: 规则 [id, class]
        :param num: 根据元素id
        :return:
        """
        while time:
            response = self.execute_js("document.documentElement.outerHTML")
            try:
                html = etree.HTML(text=response["value"])
                inp = html.xpath("//*[contains(@%s, '%s')]" % (rule, num))
                if inp:
                    break
            except Exception as e:
                continue
            time_.sleep(1)
            time -= 1
        if not time:
            raise Exception("未找到 %s" % num)

    def execute_chrome_protocol_js(self, protocol, params: dict):
        """
        Chrome DevTools 协议操作 具体协议请参考 https://chromedevtools.github.io/devtools-protocol/
        :param protocol: str 协议名称
        :param params: dict 参数
        :return:
        """
        resource = "/session/%s/chromium/send_command_and_get_result" % self.session_id
        command_executor = self.command_executor
        url = command_executor._url + resource
        body = json.dumps({'cmd': protocol, 'params': params})
        response = command_executor._request('POST', url, body)
        if "status" in response:
            return response
        return response["value"]

    def execute_js(self, js):
        """
        执行js  过瑞数检测
        :param js: str 待执行的js
        :return:  {"type": "xxx", value: "xxx"}
        """
        resource = "/session/%s/chromium/send_command_and_get_result" % self.session_id
        command_executor = self.command_executor
        url = command_executor._url + resource
        body = json.dumps({'cmd': "Runtime.evaluate", 'params': {"expression": js}})
        response = command_executor._request('POST', url, body)
        if "status" in response:
            return response
        return response["value"]["result"]
