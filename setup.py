from setuptools import setup, find_packages

setup(
    name="video_reducer",
    version="1.0.0",
    description="Riduce le dimensioni dei file video tramite codec ad alta efficienza",
    author="David",
    packages=find_packages(),
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "video-reducer=video_reducer.cli:main",
        ],
    },
)
