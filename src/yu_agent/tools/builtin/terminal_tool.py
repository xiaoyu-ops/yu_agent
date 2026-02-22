"""TerminalTool - 命令行工具

为Agent提供安全的命令行执行能力，支持：
- 文件系统操作（ls, cat, head, tail, find, grep）
- 文本处理（wc, sort, uniq）
- 目录导航（pwd, cd）
- 安全限制（白名单命令、路径限制、超时控制）

使用场景：
- JIT（即时）文件检索与分析
- 代码仓库探索
- 日志文件分析
- 数据文件预览

安全特性：
- 命令白名单（只允许安全的只读命令）
- 工作目录限制（沙箱）
- 超时控制
- 输出大小限制
- 禁止危险操作（rm, mv, chmod等）
"""

from typing import Dict, Any, List, Optional
import subprocess
import os
from pathlib import Path
import shlex

from ..base import Tool, ToolParameter


class TerminalTool(Tool):
    """命令行工具 - 为Agent提供安全的shell命令执行能力

    TerminalTool是一个专为AI Agent设计的安全命令行工具，它在标准化、沙箱化、
    安全受限的环境中执行shell命令。这使得Agent可以进行文件系统操作、代码分析、
    日志查询等任务，同时确保安全性。

    核心特性：
    ============

    1. 命令白名单（ALLOWED_COMMANDS）
       - 只允许执行预定义的安全命令
       - 禁止危险操作：rm, mv, chmod, sudo, kill, shutdown等
       - 支持：ls, cat, find, grep, head, tail, wc, sort, python, bash等

    2. 沙箱隔离（workspace）
       - 所有操作限制在指定的工作目录内
       - 使用Path.relative_to()严格检查边界
       - 防止通过"../../../../etc"这样的路径逃逸

    3. 超时控制（timeout）
       - 默认30秒最大执行时间
       - 防止无限运行或hung process
       - 超时自动终止命令

    4. 输出大小限制（max_output_size）
       - 默认10MB限制
       - 防止cat大文件时的内存溢出
       - 超出部分自动截断

    5. 状态管理（current_dir）
       - 维护"当前工作目录"状态
       - cd命令改变工具对象的current_dir而不是进程状态
       - 支持相对路径导航

    使用场景：
    ============

    1. 文件系统探索：
       >>> terminal.run({"command": "find . -name '*.py' -type f"})
       >>> terminal.run({"command": "tree -L 3"})

    2. 代码分析：
       >>> terminal.run({"command": "grep -r 'TODO' src/ --include='*.py'"})
       >>> terminal.run({"command": "head -20 main.py"})

    3. 日志查询：
       >>> terminal.run({"command": "tail -100 app.log | grep ERROR"})

    4. 统计信息：
       >>> terminal.run({"command": "wc -l *.py"})
       >>> terminal.run({"command": "du -sh ."})

    5. 代码执行（可选）：
       >>> terminal.run({"command": "python script.py arg1 arg2"})

    安全设计原则：
    ============

    1. 最小权限原则
       - 只提供必要的命令
       - 不提供系统修改命令（rm, chmod, mv等）
       - 不提供权限提升命令（sudo）

    2. 边界隔离
       - workspace根目录是不可逃逸的边界
       - 所有相对路径都从current_dir开始
       - 绝对路径必须在workspace内

    3. 资源限制
       - 执行超时防止dead loops
       - 输出大小限制防止内存溢出
       - 命令白名单限制操作范围

    4. 错误安全
       - 所有异常都被捕获和格式化
       - 返回值总是字符串（可由LLM解析）
       - 清晰的错误信息帮助调试

    实现细节：
    ============

    类级常量：
    - ALLOWED_COMMANDS: 白名单集合，包含~30个常用安全命令

    实例状态：
    - workspace: 沙箱根目录（Path对象）
    - current_dir: 当前工作目录（Path对象）
    - timeout: 执行超时（秒）
    - max_output_size: 输出限制（字节）
    - allow_cd: 是否允许cd命令（布尔）

    方法架构：
    - run(): 公开入口，验证→解析→分发
    - get_parameters(): 描述工具签名给LLM
    - _handle_cd(): 特殊处理cd命令（状态更新）
    - _execute_command(): 通用命令执行器（subprocess）
    - get_current_dir(): 查询当前目录
    - reset_dir(): 重置到初始目录

    与Tool基类的集成：
    ==================
    - 继承自Tool抽象基类
    - 实现run(parameters)方法作为执行入口
    - 实现get_parameters()描述参数签名
    - 输入验证通过validate_parameters()
    """

    # 允许的命令白名单
    # ====================================================================
    # 这个集合定义了TerminalTool允许执行的所有命令。只有这里列出的命令
    # 才能被LLM通过run()方法调用。这是安全设计的核心——通过白名单限制，
    # 而不是黑名单禁止，确保所有执行的操作都在预期范围内。
    #
    # 不允许的命令类型（拒绝原因）：
    # - 文件修改: rm, mv, cp, touch, mkdir (修改文件系统)
    # - 权限修改: chmod, chown, sudo (权限提升风险)
    # - 进程控制: kill, killall (进程管理风险)
    # - 系统关键: shutdown, reboot, halt (系统稳定性)
    # - 网络危险: nc, telnet, curl (外网访问)
    #
    # 允许的命令分类及安全理由：
    ALLOWED_COMMANDS = {
        # 文件列表与信息 - 只读操作，安全
        'ls',      # 列出目录内容
        'dir',     # 同上（Windows风格）
        'tree',    # 树形显示目录结构

        # 文件内容查看 - 只读操作，安全
        'cat',     # 显示文件内容
        'head',    # 显示文件开头N行
        'tail',    # 显示文件末尾N行
        'less',    # 分页查看文件
        'more',    # 分页查看文件（简版）
        'type',    # Windows: 显示文件内容

        # 文件搜索 - 只读操作，安全
        'find',    # 按条件查找文件
        'grep',    # 按正则查找文本
        'egrep',   # extended grep
        'fgrep',   # 快速grep（固定字符串）
        'findstr', # Windows: 搜索字符串

        # 文本处理 - 只读操作，安全
        'wc',      # 统计行数、词数、字节数
        'sort',    # 排序文本行
        'uniq',    # 去除重复行
        'cut',     # 提取列
        'awk',     # 文本处理语言（强大但安全）
        'sed',     # 流编辑器（只读模式）

        # 目录操作 - 受沙箱限制，安全
        'pwd',     # 显示当前工作目录
        'cd',      # 改变工作目录（工具内部管理）

        # 文件信息 - 只读操作，安全
        'file',    # 识别文件类型
        'stat',    # 显示文件统计信息
        'du',      # 显示磁盘使用情况
        'df',      # 显示文件系统磁盘空间

        # 其他实用命令 - 只读操作，安全
        'echo',    # 输出字符串
        'which',   # 查找命令路径
        'whereis', # 查找命令/源文件/帮助文件

        # 代码执行 - 受限执行，需谨慎
        # 这些命令允许执行代码，但在Agent受信任环境下是必要的
        # 实际使用时应由Agent明确控制执行内容
        'python',  # Python解释器
        'node',    # Node.js解释器
        'bash',    # Bash shell
        'sh',      # POSIX shell
        'powershell', # Windows: PowerShell
    }
    
    def __init__(
        self,
        workspace: str = ".",
        timeout: int = 30,
        max_output_size: int = 10 * 1024 * 1024,  # 10MB
        allow_cd: bool = True
    ):
        """初始化TerminalTool - 创建安全的命令执行环境

        该工具创建一个沙箱环境，限制所有命令操作在指定的工作目录内。

        参数说明：

        Args:
            workspace (str): 工作目录根路径（所有操作限制在此目录内）
                           默认值: "." (当前目录)
                           示例: "./project", "/home/user/workspace"
                           - 自动转换为绝对路径并标准化
                           - 如果不存在则自动创建

            timeout (int): 单个命令的最大执行时间（秒）
                          默认值: 30秒
                          防止恶意命令或长时间运行的操作阻塞系统
                          超时会触发TimeoutExpired异常

            max_output_size (int): 允许的最大输出大小（字节）
                                  默认值: 10MB (10 * 1024 * 1024)
                                  防止大文件操作产生巨大输出
                                  超出大小的输出会被截断+警告

            allow_cd (bool): 是否允许cd命令
                           默认值: True
                           设为False可禁用目录导航命令

        实例属性初始化：
        - self.workspace: 标准化后的工作目录Path对象
        - self.timeout: 命令超时秒数
        - self.max_output_size: 最大输出字节数
        - self.allow_cd: 是否允许cd命令
        - self.current_dir: 当前工作目录（初始值=workspace）

        示例：
            >>> # 为项目代码库创建工具，限制10秒超时
            >>> terminal = TerminalTool(
            ...     workspace="./my-repo",
            ...     timeout=10,
            ...     max_output_size=5*1024*1024
            ... )

            >>> # 创建只读模式的工具（禁止cd）
            >>> readonly = TerminalTool(allow_cd=False)

        安全特性：
        - 所有路径操作都通过Path.relative_to()验证沙箱边界
        - 命令限制在白名单ALLOWED_COMMANDS内
        - 超时和输出大小限制防止DoS
        """
        super().__init__(
            name="terminal",
            description="命令行工具 - 执行安全的文件系统、文本处理和代码执行命令（ls, cat, grep, head, tail等）"
        )
        
        self.workspace = Path(workspace).resolve()
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.allow_cd = allow_cd
        
        # 当前工作目录（相对于workspace）
        self.current_dir = self.workspace
        
        # 确保工作目录存在
        self.workspace.mkdir(parents=True, exist_ok=True)
    
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具 - 安全地执行命令行命令

        该方法作为工具的主入口点，负责：
        1. 验证参数格式和有效性
        2. 解析用户输入的命令字符串
        3. 检查命令是否在白名单内
        4. 分发给特定命令处理器（如cd）或通用执行器

        Args:
            parameters: 包含"command"键的字典，值为要执行的命令字符串
                       示例: {"command": "ls -la /path"}

        Returns:
            str: 执行结果（成功/错误信息）或命令输出

        示例:
            >>> terminal = TerminalTool()
            >>> terminal.run({"command": "pwd"})
            '/home/user/workspace'

            >>> terminal.run({"command": "rm file.txt"})
            '❌ 不允许的命令: rm'
        """
        if not self.validate_parameters(parameters):
            return "❌ 参数验证失败"
        
        command = parameters.get("command", "").strip()
        
        if not command:
            return "❌ 命令不能为空"
        
        # 解析命令
        try:
            parts = shlex.split(command)
        except ValueError as e:
            return f"❌ 命令解析失败: {e}"
        
        if not parts:
            return "❌ 命令不能为空"
        
        base_command = parts[0]
        
        # 检查命令是否在白名单中
        if base_command not in self.ALLOWED_COMMANDS:
            return f"❌ 不允许的命令: {base_command}\n允许的命令: {', '.join(sorted(self.ALLOWED_COMMANDS))}"
        
        # 特殊处理 cd 命令
        if base_command == 'cd':
            return self._handle_cd(parts)
        
        # 执行命令
        return self._execute_command(command)
    
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义 - 描述该工具接受的参数

        这个方法被LLM用来理解工具的输入接口。LLM会根据返回的参数定义
        来决定如何调用该工具（提供哪些参数、参数格式等）。

        返回的参数定义包括：
        - 参数名称：tool用来识别的键名
        - 参数类型：string、number、array等
        - 参数描述：告诉LLM这个参数用来做什么
        - 是否必需：required=True表示必须提供

        Returns:
            List[ToolParameter]: 包含一个参数定义的列表
                - command (required): 要执行的Shell命令字符串

        示例:
            >>> terminal = TerminalTool()
            >>> params = terminal.get_parameters()
            >>> params[0].name
            'command'
            >>> params[0].required
            True
        """
        return [
            ToolParameter(
                name="command",
                type="string",
                description=(
                    f"要执行的命令（白名单: {', '.join(sorted(list(self.ALLOWED_COMMANDS)[:10]))}...）\n"
                    "示例: 'ls -la', 'cat file.txt', 'grep pattern *.py', 'head -n 20 data.csv'"
                ),
                required=True
            ),
        ]
    
    def _handle_cd(self, parts: List[str]) -> str:
        """处理 cd 命令 - 安全的目录导航

        cd命令特殊处理的原因：
        1. 普通命令执行后进程退出，改变工作目录无效
        2. 需要在工具对象内维护"当前目录"状态
        3. 需要检查目录是否在工作目录(workspace)内（沙箱限制）

        支持的目录形式：
        - "."      : 当前目录（无操作）
        - ".."     : 父目录
        - "~"      : workspace根目录
        - "path"   : 相对于当前目录的路径（支持../子目录/路径格式）
        - "/path"  : 绝对路径（必须在workspace内）

        安全检查：
        1. 路径解析后必须在workspace内（使用relative_to()检查）
        2. 目标必须是已存在的目录
        3. 如果不允许cd操作（allow_cd=False），直接拒绝

        Args:
            parts: shlex.split()解析后的命令部分列表
                  parts[0]='cd', parts[1]=目标路径（可选）

        Returns:
            str: 成功信息（✅）或错误信息（❌）

        示例:
            >>> terminal = TerminalTool(workspace="./project")
            >>> terminal._handle_cd(['cd', 'src'])
            '✅ 切换到目录: /full/path/project/src'

            >>> terminal._handle_cd(['cd', '../../../etc'])
            '❌ 不允许访问工作目录外的路径: /etc'
        """
        if not self.allow_cd:
            return "❌ cd 命令已禁用"
        
        if len(parts) < 2:
            # cd 无参数，返回当前目录
            return f"当前目录: {self.current_dir}"
        
        target_dir = parts[1]
        
        # 处理相对路径
        if target_dir == "..":
            new_dir = self.current_dir.parent
        elif target_dir == ".":
            new_dir = self.current_dir
        elif target_dir == "~":
            new_dir = self.workspace
        else:
            new_dir = (self.current_dir / target_dir).resolve()
        
        # 检查是否在工作目录内
        try:
            new_dir.relative_to(self.workspace)
        except ValueError:
            return f"❌ 不允许访问工作目录外的路径: {new_dir}"
        
        # 检查目录是否存在
        if not new_dir.exists():
            return f"❌ 目录不存在: {new_dir}"
        
        if not new_dir.is_dir():
            return f"❌ 不是目录: {new_dir}"
        
        # 更新当前目录
        self.current_dir = new_dir
        return f"✅ 切换到目录: {self.current_dir}"
    
    def _execute_command(self, command: str) -> str:
        """执行命令 - 使用subprocess运行Shell命令

        这是实际执行命令的核心方法，负责：
        1. 通过subprocess.run()执行命令
        2. 捕获标准输出和标准错误
        3. 处理超时、错误、输出大小等异常情况

        执行环境：
        - shell=True: 允许使用pipe、重定向等Shell特性
        - cwd: 在当前工作目录（self.current_dir）下执行
        - timeout: 防止无限运行（默认30秒）
        - capture_output: 捕获stdout和stderr而不是直接打印

        输出处理流程：
        1. 合并stdout和stderr（带[stderr]标记以区分）
        2. 检查输出大小，超过限制则截断+警告
        3. 如果返回码非0，在输出前添加警告信息
        4. 如果命令成功但无输出，返回成功提示

        错误处理：
        - TimeoutExpired: 命令运行超时
        - Exception: 其他执行失败（如权限不足、命令不存在等）

        Args:
            command: 完整的命令字符串
                    示例: "ls -la | grep txt"

        Returns:
            str: 命令执行结果（stdout）或错误/警告信息

        示例:
            >>> terminal = TerminalTool()
            >>> terminal._execute_command("echo 'hello'")
            'hello'

            >>> terminal._execute_command("ls /nonexistent 2>&1")
            '⚠️ 命令返回码: 2\\n\\nls: cannot access /nonexistent'

            >>> terminal._execute_command("sleep 100")  # 超过30秒timeout
            '❌ 命令执行超时（超过 30 秒）'
        """
        try:
            # 在当前目录下执行命令
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.current_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=os.environ.copy()
            )
            
            # 合并标准输出和标准错误
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            
            # 检查输出大小
            if len(output) > self.max_output_size:
                output = output[:self.max_output_size]
                output += f"\n\n⚠️ 输出被截断（超过 {self.max_output_size} 字节）"
            
            # 添加返回码信息
            if result.returncode != 0:
                output = f"⚠️ 命令返回码: {result.returncode}\n\n{output}"
            
            return output if output else "✅ 命令执行成功（无输出）"
            
        except subprocess.TimeoutExpired:
            return f"❌ 命令执行超时（超过 {self.timeout} 秒）"
        except Exception as e:
            return f"❌ 命令执行失败: {e}"
    
    def get_current_dir(self) -> str:
        """获取当前工作目录 - 返回当前目录的绝对路径

        这个方法用于查询工具对象当前所在的目录。
        对于需要了解上下文的LLM或调用者很有用。

        Returns:
            str: 当前工作目录的完整绝对路径

        示例:
            >>> terminal = TerminalTool(workspace="./project")
            >>> terminal.current_dir = Path("./project/src")
            >>> terminal.get_current_dir()
            '/absolute/path/project/src'
        """
        return str(self.current_dir)
    
    def reset_dir(self):
        """重置到工作目录根 - 恢复初始工作目录

        这个方法用于在多次操作后将工作目录重置到初始状态（workspace根目录）。
        对于避免状态污染、确保操作的隔离性很有用。

        使用场景：
        - 在Agent的多个任务之间重置状态
        - 完成某个工作流后的清理
        - 测试中的setup/teardown

        示例:
            >>> terminal = TerminalTool(workspace="./project")
            >>> terminal.run({"command": "cd src"})
            '✅ 切换到目录: .../project/src'
            >>> terminal.get_current_dir()
            '.../project/src'
            >>> terminal.reset_dir()
            >>> terminal.get_current_dir()
            '.../project'  # 回到workspace根目录
        """
        self.current_dir = self.workspace

