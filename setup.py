import pathlib
import setuptools


LOCATION = pathlib.Path(__file__).parent.resolve()

readme_file = LOCATION / "README.md"
long_description = readme_file.open(encoding="utf8").read()

setuptools.setup(
    name="df_stats",
    version="0.1.2",
    scripts=[],
    author="Denis Kuznetsov",
    author_email="kuznetsov.den.p@gmail.com",
    description="Statistics collection extension for Dialog Flow Framework "
    "(https://github.com/deepmipt/dialog_flow_framework).",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kudep/dff-node-stats",
    packages=setuptools.find_packages(where="."),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        (LOCATION / "requirements.txt").open(encoding="utf8").read().splitlines()
    ],
    include_package_data=True,
    extras_require = {
        "postgres": ["asyncpg>=0.26.0"],
        "clickhouse": ["aiochclient>=2.2.0", "httpx<=0.23.0"],
    },
    entry_points = {
        'console_scripts': ['df_stats=df_stats.__main__:main'],
    }
)
