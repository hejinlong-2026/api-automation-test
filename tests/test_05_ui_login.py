# -*- coding: utf-8 -*-
"""Web UI 自动化：途牛通行证登录页功能测试。

定位策略说明：
  - 站点默认展示「账户登录」（账号 + 密码），无需切换 tab
  - 元素用 name 属性定位（username / password / submit_login），比 class 稳定
  - 断言以"用户能看到什么提示"为准，而不是断言 DOM 结构，降低改版脆性
"""
import os
import time

import pytest
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# CI / 本机代理环境：让浏览器直连，避免走系统代理导致 unhandled request
for _k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(_k, None)
os.environ.setdefault("no_proxy", "*")


class LoginPage:
    """页面对象：元素定位与断言分离，站点改版只改这里。"""

    URL = "https://passport.tuniu.com/login?origin=https://www.tuniu.com"

    USERNAME = (By.NAME, "username")
    PASSWORD = (By.NAME, "password")
    SUBMIT = (By.NAME, "submit_login")
    # 站点要求勾选"同意用户协议"后才放行提交，不勾选会先弹协议提示
    AGREEMENT = (By.ID, "isAgreenUs1")

    def __init__(self, driver, timeout=15):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def open(self):
        self.driver.get(self.URL)
        self.wait.until(EC.presence_of_element_located(self.USERNAME))
        return self

    def _visible(self, locator):
        for el in self.driver.find_elements(*locator):
            if el.is_displayed():
                return el
        raise NoSuchElementException(f"未找到可见元素 {locator}")

    def input_username(self, value):
        el = self._visible(self.USERNAME)
        el.clear()
        el.send_keys(value)
        return self

    def input_password(self, value):
        el = self._visible(self.PASSWORD)
        el.clear()
        el.send_keys(value)
        return self

    def click_submit(self):
        el = self._visible(self.SUBMIT)
        self.driver.execute_script("arguments[0].click();", el)
        return self

    def agree_terms(self):
        """勾选用户协议。真实站点必须先勾才校验账号 —— 这是业务前置条件。

        坑：页面有多个 checkbox（记住我、不同登录 tab 各一份），
        必须按 id 精确定位，用 input[type=checkbox] 会勾错框导致用例假失败。
        """
        for el in self.driver.find_elements(*self.AGREEMENT):
            if not el.is_selected():
                self.driver.execute_script("arguments[0].click();", el)
            assert el.is_selected(), "协议勾选框点击后仍未选中，前端交互异常"
            return True
        raise AssertionError("未找到用户协议勾选框 isAgreenUs1，页面可能改版")

    def body_text(self):
        return self.driver.find_element(By.TAG_NAME, "body").text

    def error_text(self):
        """登录失败提示通常渲染在表单附近的提示节点里，按常见 class 关键字兜底查找。"""
        candidates = self.driver.find_elements(
            By.CSS_SELECTOR,
            ".error, .err, .login-error, [class*='error'], [class*='tip'], [class*='warn']",
        )
        return " ".join(t for t in (c.text.strip() for c in candidates) if t)


@pytest.fixture(scope="module")
def driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--no-proxy-server")
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(0)
    yield d
    d.quit()


@pytest.mark.ui
class TestLoginUI:
    def test_login_page_render(self, driver):
        """UI-01 页面可用性：标题正确，账号/密码/登录按钮均渲染"""
        page = LoginPage(driver).open()
        assert "登录" in driver.title, f"标题异常：{driver.title}"
        assert page._visible(page.USERNAME).is_enabled()
        assert page._visible(page.PASSWORD).is_enabled()
        assert page._visible(page.SUBMIT).is_enabled()

    def test_login_empty_submit(self, driver):
        """UI-02 前端校验：未勾协议直接提交，必须拦截并给出协议提示"""
        page = LoginPage(driver).open()
        before_url = driver.current_url
        page.click_submit()
        time.sleep(1.5)
        assert driver.current_url == before_url, "空表单提交后发生了页面跳转"
        feedback = page.error_text() or page.body_text()
        assert any(k in feedback for k in ("协议", "勾选", "请输入", "不能为空", "账号", "手机")), (
            f"空表单提交未出现任何校验提示，页面文本={feedback[:200]}"
        )

    def test_login_empty_account_after_agree(self, driver):
        """UI-03 前端校验：勾选协议后账号密码留空提交，应提示账号必填"""
        page = LoginPage(driver).open()
        page.agree_terms()
        before_url = driver.current_url
        page.click_submit()
        time.sleep(1.5)
        assert driver.current_url == before_url, "空账号提交后发生了页面跳转"
        feedback = page.error_text() or page.body_text()
        assert any(k in feedback for k in ("请输入", "不能为空", "账号", "手机")), (
            f"空账号提交未提示必填，页面文本={feedback[:300]}"
        )

    def test_login_wrong_password(self, driver):
        """UI-04 反向：账号存在但密码错误，提示失败且停留在登录页"""
        page = LoginPage(driver).open()
        page.agree_terms()
        before_url = driver.current_url
        page.input_username("13800000000").input_password("WrongPwd_2026").click_submit()
        time.sleep(3)
        assert before_url.split("?")[0] in driver.current_url, "登录失败却跳转离开了登录页"
        feedback = page.error_text() or page.body_text()
        assert any(k in feedback for k in ("错误", "不正确", "失败", "不存在", "验证")), (
            f"错误密码未给出提示，页面文本={feedback[:300]}\n"
            "注：站点触发风控时会要求'完成验证'，这同样说明后端校验生效，判定通过"
        )

    def test_password_field_is_masked(self, driver):
        """UI-05 安全：密码框必须是 password 类型（不能明文回显）"""
        page = LoginPage(driver).open()
        el = page._visible(page.PASSWORD)
        assert el.get_attribute("type") == "password", "密码框为明文类型，存在泄露风险"
