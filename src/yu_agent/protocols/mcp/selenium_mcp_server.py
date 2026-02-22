#!/usr/bin/env python3
"""
Selenium MCP 服务器 - 使用hello_agents.protocols.MCPServer
这样和天气查询MCP服务器一样的方式
"""

import json
import logging
from typing import Dict, Any
from pathlib import Path
import os

# 禁用系统代理
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    if proxy_var in os.environ:
        del os.environ[proxy_var]

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from hello_agents.protocols import MCPServer
except ImportError:
    print("❌ 需要安装: pip install hello-agents")
    exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建MCP服务器
selenium_server = MCPServer(name="selenium-server", description="Selenium浏览器自动化服务")

# 全局WebDriver实例
driver = None


def init_driver():
    """初始化WebDriver"""
    global driver
    if driver is None:
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-proxy-auto-detect")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            driver = webdriver.Chrome(options=options)
            logger.info("✅ WebDriver初始化成功")
        except Exception as e:
            logger.error(f"❌ WebDriver初始化失败: {e}")
            raise


def browser_navigate(url: str, wait_time: int = 10) -> str:
    """
    导航到指定URL

    Args:
        url: 要访问的URL
        wait_time: 等待时间（秒）

    Returns:
        执行结果JSON字符串
    """
    try:
        init_driver()

        logger.info(f"📍 导航到: {url}")
        driver.get(url)

        # 等待页面加载
        WebDriverWait(driver, wait_time).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        result = {
            "success": True,
            "message": f"✅ 成功导航到: {url}",
            "url": driver.current_url,
            "title": driver.title
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def browser_screenshot(output_path: str, wait_for_selector: str = None) -> str:
    """
    对当前页面进行截图

    Args:
        output_path: 截图保存路径
        wait_for_selector: 等待特定元素出现的CSS选择器（可选）

    Returns:
        执行结果JSON字符串
    """
    try:
        if driver is None:
            return json.dumps({"success": False, "error": "浏览器未初始化"}, ensure_ascii=False)

        # 如果指定了选择器，等待元素出现
        if wait_for_selector:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
            )

        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        driver.save_screenshot(output_path)
        file_size = Path(output_path).stat().st_size

        logger.info(f"📸 截图保存: {output_path} ({file_size} bytes)")

        result = {
            "success": True,
            "message": f"✅ 截图成功: {output_path}",
            "file": output_path,
            "size": file_size
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def browser_click(selector: str) -> str:
    """
    点击页面元素

    Args:
        selector: CSS选择器

    Returns:
        执行结果JSON字符串
    """
    try:
        if driver is None:
            return json.dumps({"success": False, "error": "浏览器未初始化"}, ensure_ascii=False)

        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        element.click()

        logger.info(f"🖱️  点击: {selector}")

        result = {
            "success": True,
            "message": f"✅ 成功点击: {selector}"
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def browser_fill(selector: str, text: str) -> str:
    """
    填写表单输入框

    Args:
        selector: CSS选择器
        text: 要输入的文本

    Returns:
        执行结果JSON字符串
    """
    try:
        if driver is None:
            return json.dumps({"success": False, "error": "浏览器未初始化"}, ensure_ascii=False)

        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        element.clear()
        element.send_keys(text)

        logger.info(f"⌨️  填写: {selector} = {text}")

        result = {
            "success": True,
            "message": f"✅ 成功填写: {selector}"
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def browser_close() -> str:
    """
    关闭浏览器

    Returns:
        执行结果JSON字符串
    """
    try:
        global driver
        if driver:
            driver.quit()
            driver = None
            logger.info("🔌 浏览器已关闭")

        result = {
            "success": True,
            "message": "✅ 浏览器已关闭"
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def get_server_info() -> str:
    """
    获取服务器信息

    Returns:
        服务器信息JSON字符串
    """
    info = {
        "name": "Selenium MCP Server",
        "version": "1.0.0",
        "description": "Selenium浏览器自动化服务",
        "tools": [
            "browser_navigate",
            "browser_screenshot",
            "browser_click",
            "browser_fill",
            "browser_close",
            "get_server_info"
        ]
    }
    return json.dumps(info, ensure_ascii=False, indent=2)


# ✅ 注册所有工具到MCP服务器（和天气查询服务器一样的方式！）
selenium_server.add_tool(browser_navigate)
selenium_server.add_tool(browser_screenshot)
selenium_server.add_tool(browser_click)
selenium_server.add_tool(browser_fill)
selenium_server.add_tool(browser_close)
selenium_server.add_tool(get_server_info)


if __name__ == "__main__":
    logger.info("🚀 启动Selenium MCP服务器...")
    selenium_server.run()
