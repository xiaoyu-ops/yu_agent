from setuptools import setup, find_packages

setup(
    name="yu_agent",
    version="0.1.1",
# exclude 参数可以排除掉不需要打包的文件夹
packages=find_packages(exclude=["test", "test.*", "tests","test_the_yu_agent","test_the_yu_agent.*"]),
    install_requires=[
        "google_search_results==2.4.2",
        "openai==2.18.0",
        "pydantic==2.12.5",
        "serpapi==0.1.5",
        "tavily==1.1.0",
        "tavily_python==0.7.19"
    ],
    author="Zhuoyang Wu",
    description="学习阶段的agent框架实现,主体是helloagents中的大致框架,后续会逐步完善",
    license="MIT",
    url="https://github.com/xiaoyu-ops/agent",
    python_requires='>=3.10',
)