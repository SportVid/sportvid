import re
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.extension import Extension

HERE = Path(__file__).resolve().parent

def readme():
    candidates = [
        HERE / "TORCHREID_README.rst",
        HERE / "README.rst",
        HERE / "README.md",
        HERE / "README",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return "torchreid"

def find_version():
    version_file = HERE / "torchreid" / "__init__.py"
    content = version_file.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*[\'"]([^\'"]+)[\'"]', content, re.MULTILINE)
    if not match:
        raise RuntimeError("Unable to find __version__")
    return match.group(1)

def get_extensions():
    import numpy
    from Cython.Build import cythonize

    extensions = [
        Extension(
            "torchreid.metrics.rank_cylib.rank_cy",
            ["torchreid/metrics/rank_cylib/rank_cy.pyx"],
            include_dirs=[numpy.get_include()],
        )
    ]
    return cythonize(extensions)

def get_requirements(filename="requirements.txt"):
    req_file = HERE / filename
    if not req_file.exists():
        return []
    return [
        line.strip()
        for line in req_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="torchreid",
    version=find_version(),
    description="A library for deep learning person re-ID in PyTorch",
    author="Kaiyang Zhou",
    license="MIT",
    long_description=readme(),
    url="https://github.com/KaiyangZhou/deep-person-reid",
    packages=find_packages(),
    install_requires=get_requirements(),
    keywords=["Person Re-Identification", "Deep Learning", "Computer Vision"],
    ext_modules=get_extensions(),
)