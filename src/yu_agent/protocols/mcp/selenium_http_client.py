#!/usr/bin/env python
"""
Selenium HTTP客户端 - 连接到HTTP服务器的MCP工具包装
"""

import requests
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SeleniumHTTPClient:
    """连接到Selenium HTTP服务器的客户端"""

    def __init__(self, host: str = "127.0.0.1", port: int = 18888):
        """
        初始化客户端

        Args:
            host: 服务器地址
            port: 服务器端口
        """
        self.base_url = f"http://{host}:{port}"
        self.timeout = 60

    def _request(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送HTTP请求"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.post(url, json=data or {}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"无法连接到Selenium服务器: {self.base_url}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def navigate(self, url: str, wait_time: int = 10) -> Dict[str, Any]:
        """导航到URL"""
        return self._request("/browser_navigate", {
            "url": url,
            "wait_time": wait_time
        })

    def screenshot(self, output_path: str, wait_for_selector: str = None) -> Dict[str, Any]:
        """截图"""
        return self._request("/browser_screenshot", {
            "output_path": output_path,
            "wait_for_selector": wait_for_selector
        })

    def click(self, selector: str) -> Dict[str, Any]:
        """点击元素"""
        return self._request("/browser_click", {"selector": selector})

    def fill(self, selector: str, text: str) -> Dict[str, Any]:
        """填写表单"""
        return self._request("/browser_fill", {
            "selector": selector,
            "text": text
        })

    def close(self) -> Dict[str, Any]:
        """关闭浏览器"""
        return self._request("/browser_close", {})

    def get_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        return self._request("/get_server_info", {})
