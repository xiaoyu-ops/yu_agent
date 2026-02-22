#!/usr/bin/env python3
"""
Selenium HTTP 服务器 - 持久化WebDriver实例
使用HTTP而不是Stdio，让WebDriver保持连接
"""

import os
import sys

# ⚠️ 必须在导入任何其他模块之前禁用系统代理！
# 使用更激进的方式：设置为空字符串而不是删除
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY',
                  'http_proxy_config', 'https_proxy_config', 'no_proxy', 'NO_PROXY']:
    os.environ[proxy_var] = ''
    if proxy_var in os.environ and os.environ[proxy_var]:
        del os.environ[proxy_var]

import json
import logging
from typing import Dict, Any
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# 全局WebDriver实例 - 在整个服务器生命周期内保持
# ============================================================================

_driver_instance = None
_driver_lock = threading.Lock()


def get_driver():
    """获取或初始化WebDriver"""
    global _driver_instance

    with _driver_lock:
        if _driver_instance is None:
            init_driver()
        return _driver_instance


def init_driver():
    """初始化WebDriver"""
    global _driver_instance

    try:
        options = webdriver.ChromeOptions()

        # 尝试找到Chrome浏览器路径
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "google-chrome",
            "google-chrome-stable",
            "chromium"
        ]

        chrome_binary = None
        for path in chrome_paths:
            try:
                if Path(path).exists():
                    chrome_binary = path
                    break
            except:
                pass

        if chrome_binary:
            options.binary_location = chrome_binary
            logger.info(f"📍 使用Chrome: {chrome_binary}")

        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-proxy-auto-detect")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # 使用webdriver-manager自动管理ChromeDriver
        service = Service(ChromeDriverManager().install())
        _driver_instance = webdriver.Chrome(service=service, options=options)
        logger.info("✅ WebDriver初始化成功")
    except Exception as e:
        logger.error(f"❌ WebDriver初始化失败: {e}")
        raise


def close_driver():
    """关闭WebDriver"""
    global _driver_instance

    with _driver_lock:
        if _driver_instance:
            try:
                _driver_instance.quit()
                _driver_instance = None
                logger.info("🔌 WebDriver已关闭")
            except Exception as e:
                logger.error(f"❌ 关闭WebDriver失败: {e}")


# ============================================================================
# 工具函数
# ============================================================================

def browser_navigate(url: str, wait_time: int = 10) -> Dict[str, Any]:
    """导航到指定URL"""
    try:
        driver = get_driver()
        logger.info(f"📍 导航到: {url}")
        driver.get(url)

        # 等待页面加载
        WebDriverWait(driver, wait_time).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        return {
            "success": True,
            "message": f"✅ 成功导航到: {url}",
            "url": driver.current_url,
            "title": driver.title
        }
    except Exception as e:
        logger.error(f"❌ 导航失败: {e}")
        return {"success": False, "error": str(e)}


def browser_screenshot(output_path: str, wait_for_selector: str = None) -> Dict[str, Any]:
    """对当前页面进行截图"""
    try:
        driver = get_driver()

        # 如果指定了选择器，等待元素出现
        if wait_for_selector:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
            )

        # 确保输出目录存在，并转换为绝对路径
        output_path = str(Path(output_path).resolve())
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        driver.save_screenshot(output_path)
        file_size = Path(output_path).stat().st_size

        logger.info(f"📸 截图保存: {output_path} ({file_size} bytes)")

        return {
            "success": True,
            "message": f"✅ 截图成功: {output_path}",
            "file": output_path,
            "size": file_size
        }
    except Exception as e:
        logger.error(f"❌ 截图失败: {e}")
        return {"success": False, "error": str(e)}


def browser_click(selector: str) -> Dict[str, Any]:
    """点击页面元素"""
    try:
        driver = get_driver()

        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        element.click()

        logger.info(f"🖱️  点击: {selector}")

        return {
            "success": True,
            "message": f"✅ 成功点击: {selector}"
        }
    except Exception as e:
        logger.error(f"❌ 点击失败: {e}")
        return {"success": False, "error": str(e)}


def browser_fill(selector: str, text: str) -> Dict[str, Any]:
    """填写表单输入框"""
    try:
        driver = get_driver()

        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        element.clear()
        element.send_keys(text)

        logger.info(f"⌨️  填写: {selector} = {text}")

        return {
            "success": True,
            "message": f"✅ 成功填写: {selector}"
        }
    except Exception as e:
        logger.error(f"❌ 填写失败: {e}")
        return {"success": False, "error": str(e)}


def browser_close() -> Dict[str, Any]:
    """关闭浏览器"""
    try:
        close_driver()
        return {
            "success": True,
            "message": "✅ 浏览器已关闭"
        }
    except Exception as e:
        logger.error(f"❌ 关闭失败: {e}")
        return {"success": False, "error": str(e)}


def get_server_info() -> Dict[str, Any]:
    """获取服务器信息"""
    return {
        "name": "Selenium HTTP Server",
        "version": "1.0.0",
        "description": "持久化Selenium浏览器自动化服务",
        "tools": [
            "browser_navigate",
            "browser_screenshot",
            "browser_click",
            "browser_fill",
            "browser_close",
            "get_server_info"
        ]
    }


# ============================================================================
# HTTP 请求处理器
# ============================================================================

class SeleniumHTTPHandler(BaseHTTPRequestHandler):
    """处理HTTP请求的处理器"""

    def do_POST(self):
        """处理POST请求"""
        try:
            # 解析请求路径
            path = urlparse(self.path).path

            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode('utf-8')) if body else {}
            except json.JSONDecodeError:
                data = {}

            # 路由到相应的函数
            if path == '/browser_navigate':
                result = browser_navigate(
                    url=data.get('url'),
                    wait_time=int(data.get('wait_time', 10))
                )
            elif path == '/browser_screenshot':
                result = browser_screenshot(
                    output_path=data.get('output_path'),
                    wait_for_selector=data.get('wait_for_selector')
                )
            elif path == '/browser_click':
                result = browser_click(selector=data.get('selector'))
            elif path == '/browser_fill':
                result = browser_fill(
                    selector=data.get('selector'),
                    text=data.get('text')
                )
            elif path == '/browser_close':
                result = browser_close()
            elif path == '/get_server_info':
                result = get_server_info()
            else:
                result = {"success": False, "error": f"Unknown endpoint: {path}"}

            # 返回结果
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            logger.error(f"❌ HTTP请求处理失败: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "error": str(e)
            }).encode('utf-8'))

    def do_GET(self):
        """处理GET请求"""
        # 支持GET方式查询服务器信息
        path = urlparse(self.path).path
        if path == '/get_server_info':
            result = get_server_info()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """抑制默认日志"""
        pass


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    import signal

    host = "127.0.0.1"
    port = 18888  # 自定义端口

    def signal_handler(sig, frame):
        logger.info("📛 收到关闭信号，正在关闭...")
        close_driver()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        server = HTTPServer((host, port), SeleniumHTTPHandler)
        logger.info(f"🚀 Selenium HTTP服务器启动成功")
        logger.info(f"📍 地址: http://{host}:{port}")
        logger.info(f"✅ WebDriver将保持连接状态")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {e}")
        sys.exit(1)
    finally:
        close_driver()
