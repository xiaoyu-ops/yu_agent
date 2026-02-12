from setuptools import setup, find_packages

setup(
    name="yu_agent",
    version="0.1.2",
    # src 布局：源代码在 src 目录中
    packages=find_packages(where="src", exclude=["tests", "tests.*"]),
    package_dir={"": "src"},
    install_requires=[
        "google_search_results==2.4.2",
        "openai==2.18.0",
        "pydantic==2.12.5",
        "serpapi==0.1.5",
        "tavily==1.1.0",
        "tavily_python==0.7.19"
    ],
    author="Zhuoyang Wu",
    description="学习阶段的agent框架实现,主体是helloagents中的大致框架,补充了memory和rag相关的实现",
    license="MIT",
    url="https://github.com/xiaoyu-ops/yu_agent",
    python_requires='>=3.10',
)