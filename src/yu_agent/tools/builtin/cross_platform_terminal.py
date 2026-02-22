"""CrossPlatformTerminal - 跨平台终端工具

为Agent提供跨平台的终端能力，自动根据操作系统选择合适的命令。

支持的平台：
- Windows (cmd.exe, PowerShell)
- Linux (bash, sh)
- macOS (zsh, bash)

使用场景：
- 跨平台的文件系统操作
- 跨平台的代码分析
- 跨平台的日志查询

示例：
```python
from yu_agent.tools.builtin.cross_platform_terminal import CrossPlatformTerminal

terminal = CrossPlatformTerminal(workspace="./my_project")

# 自动适配Windows/Linux
terminal.list_files(".")
terminal.search_pattern("def", ".")
terminal.show_directory_structure(".")
```
"""

import platform
from typing import Optional
from .terminal_tool import TerminalTool


class CrossPlatformTerminal:
    """跨平台终端工具包装器

    自动根据操作系统选择合适的命令（Windows vs Unix/Linux）。
    提供统一的接口，隐藏平台差异。

    支持的平台：
    - Windows (cmd.exe)
    - Linux (bash/sh)
    - macOS (bash/zsh)

    特点：
    1. 透明的跨平台 - 调用代码无需关注平台差异
    2. 灵活的命令选择 - 根据OS自动选择最合适的命令
    3. 易于扩展 - 添加新的跨平台方法很简单
    4. 向后兼容 - 原有的TerminalTool不需要修改
    5. 安全可靠 - 所有命令仍经过白名单检查

    用法示例：
    ```python
    terminal = CrossPlatformTerminal(workspace="./project")

    # 列出文件 - 自动适配Windows/Linux
    print(terminal.list_files("."))

    # 搜索模式 - 自动使用findstr(Windows)或grep(Linux)
    print(terminal.search_pattern("def", "."))

    # 显示目录树 - 自动适配tree命令
    print(terminal.show_directory_structure("."))
    ```
    """

    def __init__(self, workspace: str = "."):
        """初始化跨平台终端

        Args:
            workspace: 工作目录
        """
        self.terminal = TerminalTool(workspace=workspace)
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() in ("Linux", "Darwin")  # Darwin = macOS

    def list_files(self, path: str = ".") -> str:
        """列出目录文件 - 跨平台

        根据操作系统自动选择合适的列表命令。

        Args:
            path: 目录路径

        Returns:
            命令执行结果

        示例：
            >>> terminal = CrossPlatformTerminal()
            >>> print(terminal.list_files("."))
            # Windows 输出: dir /B 的结果
            # Linux 输出: ls -la 的结果
        """
        if self.is_windows:
            # Windows: dir /B (简洁模式)
            cmd = f"dir /B {path}"
        else:
            # Linux/Mac: ls -la
            cmd = f"ls -la {path}"

        return self.terminal.run({"command": cmd})

    def list_files_detailed(self, path: str = ".") -> str:
        """列出目录文件（详细信息） - 跨平台

        显示完整的文件属性信息。

        Args:
            path: 目录路径

        Returns:
            命令执行结果
        """
        if self.is_windows:
            # Windows: dir /A (显示所有，包括隐藏)
            cmd = f"dir /A {path}"
        else:
            # Linux/Mac: ls -laR
            cmd = f"ls -laR {path}"

        return self.terminal.run({"command": cmd})

    def search_pattern(self, pattern: str, path: str = ".") -> str:
        """搜索文件内容 - 跨平台

        在文件中搜索匹配指定模式的内容。

        Args:
            pattern: 搜索模式/正则表达式
            path: 搜索范围

        Returns:
            命令执行结果

        示例：
            >>> terminal = CrossPlatformTerminal()
            >>> print(terminal.search_pattern("def", "."))
            # Windows 输出: findstr /S /R "def" .\* 的结果
            # Linux 输出: grep -r "def" . 的结果
        """
        if self.is_windows:
            # Windows: findstr /R "pattern" (递归搜索)
            cmd = f"findstr /S /R \"{pattern}\" {path}\\*"
        else:
            # Linux/Mac: grep -r "pattern"
            cmd = f"grep -r \"{pattern}\" {path}"

        return self.terminal.run({"command": cmd})

    def show_directory_structure(self, path: str = ".") -> str:
        """显示目录树形结构 - 跨平台

        以树形格式显示目录和文件的层级关系。

        Args:
            path: 目录路径

        Returns:
            命令执行结果

        示例：
            >>> terminal = CrossPlatformTerminal()
            >>> print(terminal.show_directory_structure("."))
            # 显示目录树
        """
        if self.is_windows:
            # Windows: tree /F (显示文件)
            cmd = f"tree /F {path}"
        else:
            # Linux/Mac: tree -L 3
            cmd = f"tree -L 3 {path}"

        return self.terminal.run({"command": cmd})

    def count_lines(self, filepath: str) -> str:
        """统计文件行数 - 跨平台

        计算文件中的总行数。

        Args:
            filepath: 文件路径

        Returns:
            命令执行结果

        示例：
            >>> terminal = CrossPlatformTerminal()
            >>> print(terminal.count_lines("main.py"))
            # Windows 输出: 行数信息
            # Linux 输出: 行数信息
        """
        if self.is_windows:
            # Windows: find /C /V "" (统计行数)
            cmd = f"find /C /V \"\" {filepath}"
        else:
            # Linux/Mac: wc -l
            cmd = f"wc -l {filepath}"

        return self.terminal.run({"command": cmd})

    def change_directory(self, target_dir: str) -> str:
        """改变目录 - 跨平台

        切换到指定目录。

        Args:
            target_dir: 目标目录

        Returns:
            命令执行结果
        """
        return self.terminal.run({"command": f"cd {target_dir}"})

    def get_current_dir(self) -> str:
        """获取当前工作目录

        Returns:
            当前目录路径

        示例：
            >>> terminal = CrossPlatformTerminal()
            >>> print(terminal.get_current_dir())
            # 输出: /current/working/directory
        """
        return self.terminal.get_current_dir()

    def show_file_content(self, filepath: str, lines: Optional[int] = None) -> str:
        """显示文件内容 - 跨平台

        显示指定文件的全部或部分内容。

        Args:
            filepath: 文件路径
            lines: 显示行数（None=全部）

        Returns:
            命令执行结果

        示例：
            >>> terminal = CrossPlatformTerminal()
            >>> # 显示整个文件
            >>> print(terminal.show_file_content("README.md"))

            >>> # 显示前20行
            >>> print(terminal.show_file_content("main.py", lines=20))
        """
        if lines:
            if self.is_windows:
                # Windows: 使用powershell
                cmd = f"powershell -Command \"Get-Content '{filepath}' -Head {lines}\""
            else:
                # Linux/Mac: head -n
                cmd = f"head -n {lines} {filepath}"
        else:
            if self.is_windows:
                # Windows: type
                cmd = f"type {filepath}"
            else:
                # Linux/Mac: cat
                cmd = f"cat {filepath}"

        return self.terminal.run({"command": cmd})

    def run_custom_command(self, command: str) -> str:
        """运行自定义命令（仅当需要特定平台命令时使用）

        对于需要特定平台命令的情况，直接传入完整命令字符串。
        注意：此方法不提供跨平台抽象，需要手动处理平台差异。

        Args:
            command: 完整的shell命令

        Returns:
            命令执行结果

        示例：
            >>> terminal = CrossPlatformTerminal()
            >>> # 直接运行特定平台命令
            >>> print(terminal.run_custom_command("echo 'hello'"))
        """
        return self.terminal.run({"command": command})
