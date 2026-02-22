#!/usr/bin/env python
"""
Selenium截图工具 - 可直接与yu_agent集成
"""

import os

# 禁用系统代理
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    if proxy_var in os.environ:
        del os.environ[proxy_var]

from yu_agent.tools.base import Tool, ToolParameter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SeleniumScreenshotTool(Tool):
    """
    使用Selenium进行网页截图的工具

    功能：
    - 访问任意URL
    - 等待页面加载完成
    - 生成高质量截图
    - 支持自定义等待时间

    示例：
    ```python
    from yu_agent import SimpleAgent, AgentsLLM, global_registry

    agent = SimpleAgent("浏览器", AgentsLLM())
    tool = SeleniumScreenshotTool(headless=True)
    global_registry.register_tool(tool)

    response = agent.run("访问https://example.com并截图保存为test.png")
    ```
    """

    def __init__(self, headless=True, window_size="1920x1080"):
        """
        初始化Selenium工具

        Args:
            headless: 是否使用headless模式
            window_size: 窗口大小 (宽x高)
        """
        self.headless = headless
        self.window_size = window_size
        self.driver = None

        super().__init__(
            name="selenium_screenshot",
            description="使用Selenium对网页进行截图"
        )

    def _init_driver(self):
        """初始化Selenium WebDriver"""
        if self.driver is not None:
            return

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
                        logger.info(f"📍 找到Chrome: {chrome_binary}")
                        break
                except:
                    pass

            if chrome_binary:
                options.binary_location = chrome_binary

            # 窗口大小
            if self.window_size:
                options.add_argument(f"--window-size={self.window_size}")

            # Headless模式
            if self.headless:
                options.add_argument("--headless=new")

            # 其他优化选项
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-proxy-auto-detect")  # 禁用代理自动检测
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            # 使用webdriver-manager管理ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("✅ Selenium WebDriver初始化成功")

        except Exception as e:
            error_msg = f"❌ Selenium初始化失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def run(self, params: dict) -> str:
        """
        执行截图

        Args:
            params: 包含以下字段的字典
                - url: 要访问的URL (必需)
                - output_path: 截图保存路径 (默认: screenshot.png)
                - wait_time: 最大等待时间，秒 (默认: 10)
                - wait_for_selector: 等待特定元素出现 (可选)

        Returns:
            执行结果信息
        """
        try:
            # 解析参数
            url = params.get("url")
            if not url:
                return "❌ 错误：未指定URL (url参数)"

            output_path = params.get("output_path", "screenshot.png")
            wait_time = int(params.get("wait_time", 10))
            wait_selector = params.get("wait_for_selector")

            # 确保输出目录存在
            output_dir = Path(output_path).parent
            if output_dir != Path("."):
                output_dir.mkdir(parents=True, exist_ok=True)

            # 初始化驱动
            self._init_driver()

            logger.info(f"📍 访问URL: {url}")
            self.driver.get(url)

            # 等待页面加载
            logger.info(f"⏳ 等待页面加载完成 (最多{wait_time}秒)...")
            WebDriverWait(self.driver, wait_time).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # 如果指定了选择器，等待该元素出现
            if wait_selector:
                logger.info(f"⏳ 等待元素出现: {wait_selector}")
                WebDriverWait(self.driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )

            # 获取页面尺寸，用于截取整页
            try:
                S = lambda X: self.driver.execute_script('return document.documentElement.scrollHeight')
                H = S(0)
                self.driver.set_window_size(1920, H + 100)
            except:
                # 如果出错，就用默认大小
                pass

            # 保存截图
            self.driver.save_screenshot(output_path)

            file_size = Path(output_path).stat().st_size
            logger.info(f"✅ 截图成功: {output_path} ({file_size} bytes)")

            return f"✅ 截图成功保存到: {output_path}\n📊 文件大小: {file_size} bytes"

        except Exception as e:
            error_msg = f"❌ 截图失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def get_parameters(self) -> list:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="url",
                type="string",
                description="要访问的网页URL (如: https://example.com)",
                required=True
            ),
            ToolParameter(
                name="output_path",
                type="string",
                description="截图保存路径 (默认: screenshot.png)",
                required=False
            ),
            ToolParameter(
                name="wait_time",
                type="number",
                description="等待页面加载的最长时间，单位秒 (默认: 10)",
                required=False
            ),
            ToolParameter(
                name="wait_for_selector",
                type="string",
                description="等待特定元素出现的CSS选择器 (可选)",
                required=False
            )
        ]

    def click(self, selector: str, wait_time: int = 10) -> str:
        """点击页面元素"""
        try:
            element = WebDriverWait(self.driver, wait_time).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            element.click()
            return f"✅ 成功点击元素: {selector}"
        except Exception as e:
            return f"❌ 点击失败: {str(e)}"

    def fill_input(self, selector: str, text: str, wait_time: int = 10) -> str:
        """填写表单输入"""
        try:
            element = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            element.clear()
            element.send_keys(text)
            return f"✅ 成功填写: {selector}"
        except Exception as e:
            return f"❌ 填写失败: {str(e)}"

    def get_page_content(self) -> str:
        """获取页面HTML内容"""
        try:
            return self.driver.page_source
        except Exception as e:
            return f"❌ 获取内容失败: {str(e)}"

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("✅ 浏览器已关闭")

    def __del__(self):
        """析构时清理资源"""
        self.close()


# 使用示例
if __name__ == "__main__":
    import sys
    import os

    # 添加项目路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    sys.path.insert(0, project_root)
    sys.path.insert(0, os.path.join(project_root, "src"))

    from yu_agent import SimpleAgent, AgentsLLM, global_registry

    print("=" * 60)
    print("Selenium截图工具 - Agent集成示例")
    print("=" * 60)

    # 创建Agent
    agent = SimpleAgent("截图助手", AgentsLLM())

    # 创建并注册Selenium工具
    selenium_tool = SeleniumScreenshotTool(headless=True)
    global_registry.register_tool(selenium_tool)

    print("\n✅ Selenium工具已注册")
    print("📝 可用工具:")
    for tool_name in global_registry.list_tools():
        print(f"   - {tool_name}")

    # Agent使用工具
    print("\n🤖 Agent正在执行任务...")
    print("-" * 60)

    response = agent.run("请使用selenium_screenshot工具访问https://example.com并截图保存为example.png")

    print("\n" + "=" * 60)
    print("Agent回复:")
    print(response)
    print("=" * 60)

    # 清理
    selenium_tool.close()
