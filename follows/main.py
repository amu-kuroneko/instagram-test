""" This is a test script for instagram """
#!/usr/bin/env python
# --- coding: utf-8 ---

import json
import sys
from datetime import datetime
from math import floor
from random import random
from sys import argv
from sys import stderr
from sys import stdout
from time import sleep

import requests
from requests.cookies import RequestsCookieJar
from selenium.webdriver import ChromeOptions
from splinter import Browser

def _log(level, message):
    level = level.upper()
    if level in ('FATAL', 'ERROR', 'WARNING'):
        file = stderr
    else:
        file = stdout
    print('[%s][%s] %s' % (level, datetime.now().strftime('%Y%m%d%H%M%S'), message), file=file)

class Instagram():
    """
    Instagram 操作用 Class
    """

    def __init__(self, browser):
        self.browser = browser
        self.count = 0
        self.now = datetime.now().strftime('%Y%m%d%H%M%S')
        self.cookie_jar = RequestsCookieJar()

    def screenshot(self):
        """
        Screenshot を撮って /tmp に保存する
        """
        _path = '/tmp/%s-instagram-screenshot-%03d.png' % (self.now, self.count)
        _log('info', 'Save screenshot to %s' % _path)
        self.browser.driver.save_screenshot(_path)
        self.count += 1

    def login(self, username, password):
        """
        Instagram への Login 処理
        """
        self.browser.visit('https://www.instagram.com/')
        sleep(2)
        # Input
        _elements = self.browser.find_by_tag('input')
        if len(_elements) < 2:
            _log('fatal', 'Input form for login does not exist')
            return False
        _elements.first.fill(username)
        _elements.last.fill(password)
        # Button
        _elements = self.browser.find_by_css('button[type=submit]')
        if len(_elements) < 1:
            _log('fatal', 'Submit button for login does not exist')
            return False
        _elements.first.click()

        # checking to move page
        if not self._wait_to_set_cookie('sessionid', 5):
            _log('error', 'Failed to login')
            return False

        if self.browser.url == 'https://www.instagram.com/accounts/onetap/?next=%2F':
            if not self._save_login_info():
                _log('fatal', 'Failed to save login info')
                return False
        self._update_cookies()
        if self.browser.url.startswith('https://www.instagram.com/challenge'):
            if not self._send_security_code():
                _log('error', 'Failed to authenticate by security code')
                return False
        return True

    def get_users(self, keyword):
        """
        Instagram の User 情報を取得する
        """
        _params = {
            'context': 'user',
            'query': keyword,
            'rank_token': random(),
            'include_reel': 'false'}
        _log('debug', 'Search User: %s' % keyword)
        _result = requests.get(
            'https://www.instagram.com/web/search/topsearch/',
            params=_params,
            cookies=self.cookie_jar)
        if _result.status_code != 200:
            _log('error', 'Failed to get users.')
            return None
        try:
            return json.loads(_result.text)
        except json.decoder.JSONDecodeError as error:
            _log('fatal', _result.text)
            self.screenshot()
            raise error

    def follow_user(self, username):
        """
        指定した User を Follow する
        """
        _log('info', 'Try to follow user is %s' % username)
        _url = 'https://www.instagram.com/%s/' % username
        self.browser.visit(_url)
        sleep(2)
        if self.browser.url != _url:
            _log('error', 'Failed to move user page to %s' % _url)
            return False
        _elements = self.browser.find_by_css('main header button')
        if len(_elements) == 0:
            _log('fatal', 'Follow button does not exist in %s' % _url)
            return False
        _text = _elements.first.outer_html
        _elements.first.click()
        sleep(1)
        _elements = self.browser.find_by_css('main header button')
        if _text == _elements.first.outer_html:
            _log('error', 'Failed to follow user: %s' % username)
        return True

    def _save_login_info(self):
        _url = self.browser.url
        _elements = self.browser.find_by_css('button[type=button]')
        if len(_elements) == 0:
            _log('fatal', 'To save login info button does not exist')
            return False
        _elements.first.click()
        return self._wait_to_move_page(_url, 5)

    def _send_security_code(self):
        _elements = self.browser.find_by_css('button')
        if len(_elements) == 0:
            _log('fatal', 'To send security code button does not exist')
            return False
        _elements.last.click()
        sleep(2)
        _elements = self.browser.find_by_css('input[name=security_code]')
        if len(_elements) == 0:
            _log('fatal', 'Input form for security code does not exist')
            return False
        _security_code = input('Input Serucity Code > ')
        _elements.first.fill(_security_code)
        _elements = self.browser.find_by_tag('button')
        if len(_elements) == 0:
            _log('fatal', 'To submit security code button code does not exist')
            return False
        _url = self.browser.url
        _log('debug', 'challenge page: %s' % _url)
        _elements.first.click()
        return self._wait_to_move_page(_url, 5)

    def _wait_to_move_page(self, url, trials):
        for _ in range(trials):
            sleep(1)
            if self.browser.url != url:
                return True
        return False

    def _wait_to_set_cookie(self, cookie_name, trials):
        for _ in range(trials):
            sleep(1)
            if self.browser.driver.get_cookie(cookie_name) is not None:
                return True
        return False

    def _update_cookies(self):
        self.cookie_jar.clear()
        for cookie in self.browser.driver.get_cookies():
            _options = {}
            if 'domain' in cookie:
                _options['domain'] = cookie['domain']
            if 'expire' in cookie:
                _options['expires'] = cookie['expire']
            if 'httpOnly' in cookie and cookie['httpOnly']:
                _options['rest'] = {'HttpOnly': True}
            if 'path' in cookie:
                _options['path'] = cookie['path']
            if 'secure' in cookie and cookie['secure']:
                _options['secure'] = True
            self.cookie_jar.set(cookie['name'], cookie['value'], **_options)

def _init_browser():
    _option = ChromeOptions()
    _option.add_argument('--headless')
    _option.add_argument('--no-sandbox')
    _option.add_argument('--disable-dev-shm-usage')
    _params = {
        'headless': True,
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) '
                      + 'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
        'service_log_path': '/tmp/ghostdriver._log',
        'chrome_options': _option}
    return Browser('chrome', **_params)

def _get_user_info():
    if len(argv) < 3:
        print('Usage: python %s <username> <password>' % argv[0])
        return None
    return {'username': argv[1], 'password': argv[2]}

def _make_search_word(number):
    _characters = 'abcdefghijklmnopqrstrvwxyz'
    _length = 26
    _digit = 1
    _offset = 0
    _value = _length
    while _offset + _value <= number:
        _offset += _value
        _value *= _length
        _digit += 1
    _denominator = 1
    _result = ''
    number -= _offset
    for _ in range(_digit):
        _result = _characters[floor(number / _denominator) % _length] + _result
        _denominator *= _length
    return _result

def _main():
    _user_info = _get_user_info()
    if _user_info is None:
        return 1
    _instagram = Instagram(_init_browser())
    _log('info', 'Try to login as user %s' % _user_info['username'])
    if not _instagram.login(_user_info['username'], _user_info['password']):
        _instagram.screenshot()
        return 1
    _log('info', 'Succeeded to login user as %s' % _user_info['username'])
    if len(argv) >= 4 and argv[3] == 'logincheck':
        return 0

    _user_set = set()
    _count = 0
    try:
        for _i in  range(10000):
            _values = _instagram.get_users(_make_search_word(_i))
            if _values is None:
                return 1
            for _user_value in _values['users']:
                _user = _user_value['user']
                _username = _user['username']
                if _username in _user_set:
                    continue
                _user_set.add(_username)
                if _user['is_private'] or _user['friendship_status']['following']:
                    continue
                if not _instagram.follow_user(_username):
                    _log('error', 'Failed to follow when trying %d times' % _count)
                    _instagram.screenshot()
                    return 1
                _count += 1
                sleep(8)
    except BaseException as exception:
        _instagram.screenshot()
        raise exception
    return 0

sys.exit(_main())
