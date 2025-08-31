from setuptools import setup, find_packages

setup(
    name="betnix-earth",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pygame",
        "PyOpenGL",
        "Pillow",
        "requests"
    ],
    description="Betnix Earth 3D Globe Python Module",
    author="Your Name",
    url="https://github.com/BetnixTech/betnix-earth-pymodule",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
