import time
import os
import re
import sys

import requests
from loguru import logger
from utils.xianyu_utils import generate_sign


class XianyuApis:
    def _post_wrapper(self, url, **kwargs):
        """Post请求的包装器，用于打印请求和响应信息
        
        Args:
            url: 请求URL
            **kwargs: requests.post的其他参数
            
        Returns:
            requests.Response: 响应对象
        """
        # 打印请求信息
        logger.debug(f"POST请求 URL: {url}")
        if 'headers' in kwargs:
            logger.debug(f"请求头: {kwargs['headers']}")
        if 'params' in kwargs:
            logger.debug(f"URL参数: {kwargs['params']}")
        if 'data' in kwargs:
            logger.debug(f"请求体: {kwargs['data']}")
            
        # 发送请求
        response = self.session.post(url, **kwargs)
        
        # 打印响应信息
        logger.debug(f"响应状态码: {response.status_code}")
        logger.debug(f"响应头: {dict(response.headers)}")
        try:
            logger.debug(f"响应内容: {response.json()}")
        except:
            logger.debug(f"响应内容: {response.text[:200]}...")  # 只打印前200个字符
            
        return response

    def __init__(self):
        proxy = os.getenv("XIANYU_PROXY", None)
        self.url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/'
        self.session = requests.Session()
        # 设置代理
        if proxy:
            self.session.proxies = {
                'http': proxy,
                'https': proxy
            }
        # token 缓存相关
        self._token_cache = None
        self._token_expire_time = 0
        self._token_valid_duration = 3600  # token 有效期1小时
        self.session.headers.update({
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://www.goofish.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.goofish.com/',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        })
        
    def clear_duplicate_cookies(self, update_env=True):
        """清理重复的cookies
        
        Args:
            update_env: 是否更新.env文件，默认为True
        """
        # 创建一个新的CookieJar
        new_jar = requests.cookies.RequestsCookieJar()
        
        # 记录已经添加过的cookie名称
        added_cookies = set()
        
        # 按照cookies列表的逆序遍历（最新的通常在后面）
        cookie_list = list(self.session.cookies)
        cookie_list.reverse()
        
        for cookie in cookie_list:
            # 如果这个cookie名称还没有添加过，就添加到新jar中
            if cookie.name not in added_cookies:
                new_jar.set_cookie(cookie)
                added_cookies.add(cookie.name)
                
        # 替换session的cookies
        self.session.cookies = new_jar
        
        # 更新完cookies后，根据参数决定是否更新.env文件
        if update_env:
            self.update_env_cookies()
            
    def update_env_cookies(self):
        """更新.env文件中的COOKIES_STR"""
        try:
            # 获取当前cookies的字符串形式
            cookie_str = '; '.join([f"{cookie.name}={cookie.value}" for cookie in self.session.cookies])
            
            # 读取.env文件
            env_path = os.path.join(os.getcwd(), '.env')
            if not os.path.exists(env_path):
                logger.warning(".env文件不存在，无法更新COOKIES_STR")
                return
            
            # 使用文件锁确保并发安全
            with open(env_path, 'r+', encoding='utf-8') as f:
                try:
                    # 尝试获取文件锁
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_EX)
                except ImportError:
                    # Windows系统不支持fcntl，跳过锁定
                    pass
                
                try:
                    env_content = f.read()
                    if 'COOKIES_STR=' in env_content:
                        new_env_content = re.sub(
                            r'COOKIES_STR=.*', 
                            f'COOKIES_STR={cookie_str}',
                            env_content
                        )
                        
                        # 回到文件开头并截断文件
                        f.seek(0)
                        f.truncate()
                        f.write(new_env_content)
                        logger.debug("已更新.env文件中的COOKIES_STR")
                    else:
                        logger.warning(".env文件中未找到COOKIES_STR配置项")
                finally:
                    try:
                        # 释放文件锁
                        fcntl.flock(f, fcntl.LOCK_UN)
                    except ImportError:
                        pass
                        
        except Exception as e:
            logger.warning(f"更新.env文件失败: {str(e)}")
        
    def hasLogin(self, retry_count=0):
        """调用hasLogin.do接口进行登录状态检查"""
        current_retry = retry_count
        while current_retry < 2:  # 最多重试2次
            try:
                url = 'https://passport.goofish.com/newlogin/hasLogin.do'
                params = {
                    'appName': 'xianyu',
                    'fromSite': '77'
                }
                data = {
                    'hid': self.session.cookies.get('unb', ''),
                    'ltl': 'true',
                    'appName': 'xianyu',
                    'appEntrance': 'web',
                    '_csrf_token': self.session.cookies.get('XSRF-TOKEN', ''),
                    'umidToken': '',
                    'hsiz': self.session.cookies.get('cookie2', ''),
                    'bizParams': 'taobaoBizLoginFrom=web',
                    'mainPage': 'false',
                    'isMobile': 'false',
                    'lang': 'zh_CN',
                    'returnUrl': '',
                    'fromSite': '77',
                    'isIframe': 'true',
                    'documentReferer': 'https://www.goofish.com/',
                    'defaultView': 'hasLogin',
                    'umidTag': 'SERVER',
                    'deviceId': self.session.cookies.get('cna', '')
                }
                
                response = self._post_wrapper(url, params=params, data=data)
                res_json = response.json()
                
                if res_json.get('content', {}).get('success'):
                    logger.debug("Login成功")
                    # 清理和更新cookies
                    self.clear_duplicate_cookies()
                    return True
                else:
                    logger.warning(f"Login失败 (第{current_retry + 1}次尝试): {res_json}")
                    time.sleep(0.5)
                    current_retry += 1
                    continue
                    
            except Exception as e:
                logger.error(f"Login请求异常 (第{current_retry + 1}次尝试): {str(e)}")
                time.sleep(0.5)
                current_retry += 1
                continue
                
        logger.error("Login检查失败，重试次数过多")
        return False

    def _is_token_valid(self):
        """检查缓存的token是否有效"""
        if not self._token_cache:
            return False
        return time.time() < self._token_expire_time

    def get_token(self, device_id, retry_count=0):
        """获取token
        
        Args:
            device_id: 设备ID
            retry_count: 重试次数，默认为0
            
        Returns:
            dict: 包含token的响应数据
            
        Raises:
            SystemExit: 当token获取失败且重试次数达到上限时
        """
        # 检查缓存的token是否有效
        if self._is_token_valid():
            logger.debug("使用缓存的token")
            return {"data": {"accessToken": self._token_cache}}
            
        current_retry = retry_count
        while True:
            if current_retry >= 3:  # 最多重试3次（初始请求 + 3次重试）
                logger.error("获取token失败，已达到最大重试次数")
                logger.info("尝试重新登录...")
                
                # 尝试通过hasLogin重新登录
                if self.hasLogin():
                    logger.info("重新登录成功，重新尝试获取token")
                    # 清理所有cookie并重新获取token
                    self.clear_duplicate_cookies()
                    current_retry = 0  # 重置重试次数
                    continue
                else:
                    logger.error("重新登录失败，可能原因：")
                    logger.error("1. Cookie已过期")
                    logger.error("2. 账号在其他设备登录")
                    logger.error("3. 网络连接问题")
                    logger.error("🔴 程序即将退出，请检查以下内容：")
                    logger.error("1. .env文件中的COOKIES_STR是否最新")
                    logger.error("2. 网络连接是否正常")
                    logger.error("3. 是否需要重新登录闲鱼网页版获取新的Cookie")
                    sys.exit(1)  # 直接退出程序
                
            params = {
                'jsv': '2.7.2',
                'appKey': '34839810',
                't': str(int(time.time()) * 1000),
                'sign': '',
                'v': '1.0',
                'type': 'originaljson',
                'accountSite': 'xianyu',
                'dataType': 'json',
                'timeout': '20000',
                'api': 'mtop.taobao.idlemessage.pc.login.token',
                'sessionOption': 'AutoLoginOnly',
                'spm_cnt': 'a21ybx.im.0.0',
            }
            data_val = '{"appKey":"444e9908a51d1cb236a27862abc769c9","deviceId":"' + device_id + '"}'
            data = {
                'data': data_val,
            }
            
            # 简单获取token，信任cookies已清理干净
            token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
            
            sign = generate_sign(params['t'], token, data_val)
            params['sign'] = sign
            
            try:
                response = self._post_wrapper('https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/', params=params, data=data)
                res_json = response.json()
                logger.info(f"Token API响应: {res_json}")
                
                if isinstance(res_json, dict):
                    ret_value = res_json.get('ret', [])
                    # 检查ret是否包含成功信息
                    if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                        error_msg = '; '.join(ret_value)
                        logger.warning(f"Token API调用失败 (第{current_retry + 1}次尝试)")
                        logger.warning(f"错误信息: {error_msg}")
                        
                        # 处理响应中的Set-Cookie
                        if 'Set-Cookie' in response.headers:
                            logger.debug("检测到Set-Cookie，更新cookie")
                            self.clear_duplicate_cookies(update_env=False)
                            
                        # 根据错误信息调整重试策略
                        if any('令牌过期' in ret for ret in ret_value):
                            logger.info("Token已过期，立即重试")
                        elif any('请求太频繁' in ret for ret in ret_value):
                            wait_time = min(2 ** current_retry, 8)  # 指数退避，最多等待8秒
                            logger.info(f"请求频率限制，等待{wait_time}秒后重试")
                            time.sleep(wait_time)
                        else:
                            time.sleep(10.5)
                            
                        current_retry += 1
                        continue
                        
                    else:
                        logger.info("Token获取成功")
                        # 更新token缓存
                        if 'data' in res_json and 'accessToken' in res_json['data']:
                            self._token_cache = res_json['data']['accessToken']
                            self._token_expire_time = time.time() + self._token_valid_duration
                            logger.debug("Token缓存已更新，有效期1小时")
                        return res_json
                else:
                    logger.error(f"Token API返回格式异常: {res_json}")
                    logger.error("这可能是API结构发生变化导致的")
                    time.sleep(10.5)
                    current_retry += 1
                    continue
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Token API网络请求异常: {str(e)}")
                time.sleep(10)  # 网络错误等待更长时间
                current_retry += 1
                continue
            except Exception as e:
                logger.error(f"Token API未知异常: {str(e)}")
                time.sleep(10.5)
                current_retry += 1
                continue

    def get_item_info(self, item_id, retry_count=0):
        """获取商品信息，自动处理token失效的情况"""
        current_retry = retry_count
        while current_retry < 3:  # 最多重试3次
            try:
                params = {
                    'jsv': '2.7.2',
                    'appKey': '34839810',
                    't': str(int(time.time()) * 1000),
                    'sign': '',
                    'v': '1.0',
                    'type': 'originaljson',
                    'accountSite': 'xianyu',
                    'dataType': 'json',
                    'timeout': '20000',
                    'api': 'mtop.taobao.idle.pc.detail',
                    'sessionOption': 'AutoLoginOnly',
                    'spm_cnt': 'a21ybx.im.0.0',
                }
                
                data_val = '{"itemId":"' + item_id + '"}'
                data = {
                    'data': data_val,
                }
                
                # 简单获取token，信任cookies已清理干净
                token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
                
                sign = generate_sign(params['t'], token, data_val)
                params['sign'] = sign
                
                response = self._post_wrapper(
                    'https://h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail/1.0/', 
                    params=params, 
                    data=data
                )
                
                res_json = response.json()
                # 检查返回状态
                if isinstance(res_json, dict):
                    ret_value = res_json.get('ret', [])
                    # 检查ret是否包含成功信息
                    if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                        logger.warning(f"商品信息API调用失败 (第{current_retry + 1}次尝试)")
                        logger.warning(f"错误信息: {ret_value}")
                        # 处理响应中的Set-Cookie
                        if 'Set-Cookie' in response.headers:
                            logger.debug("检测到Set-Cookie，更新cookie")
                            self.clear_duplicate_cookies(update_env=False)
                        time.sleep(0.5)
                        current_retry += 1
                        continue
                    else:
                        logger.debug(f"商品信息获取成功: {item_id}")
                        return res_json
                else:
                    logger.error(f"商品信息API返回格式异常: {res_json}")
                    time.sleep(0.5)
                    current_retry += 1
                    continue
                    
            except Exception as e:
                logger.error(f"商品信息API请求异常 (第{current_retry + 1}次尝试): {str(e)}")
                time.sleep(0.5)
                current_retry += 1
                continue
                
        logger.error("获取商品信息失败，重试次数过多")
        return {"error": "获取商品信息失败，重试次数过多"}
