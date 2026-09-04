#!/usr/bin/env python
# Copyright (c) Megvii, Inc. and its affiliates. All Rights Reserved

import re
import os
import setuptools
import glob
import torch
from torch.utils.cpp_extension import CppExtension

torch_ver = [int(x) for x in torch.__version__.split(".")[:2]]
assert torch_ver >= [1, 3], "Requires PyTorch >= 1.3"


def get_extensions():
    # this_dir = path.dirname(path.relpath(__file__))
    # extensions_dir = os.path.join(os.getcwd(), "yolox", "layers", "csrc")
    # main_source = os.path.join(extensions_dir, "vision.cpp")
    # sources = glob.glob(os.path.join(extensions_dir, "**", "*.cpp"))
    # sources = [main_source] + sources
   
    extension = CppExtension

    sources = ['yolox/layers/csrc/vision.cpp', 
               'yolox/layers/csrc/cocoeval/cocoeval.cpp']
    
    include_dirs = ['yolox/layers/csrc']

    define_macros = []

    extra_compile_args = {"cxx": ["-O3"]}

    ext_modules = [
        extension(
            "yolox._C",
            sources,
            include_dirs=include_dirs,
            define_macros=define_macros,
            extra_compile_args=extra_compile_args,
        )
    ]

    return ext_modules


with open("yolox/__init__.py", "r") as f:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        f.read(), re.MULTILINE
    ).group(1)


with open("README.md", "r") as f:
    long_description = f.read()


setuptools.setup(
    name="yolox",
    version=version,
    author="basedet team",
    python_requires=">=3.6",
    long_description=long_description,
    ext_modules=get_extensions(),
    classifiers=["Programming Language :: Python :: 3", "Operating System :: OS Independent"],
    cmdclass={"build_ext": torch.utils.cpp_extension.BuildExtension},
    packages=setuptools.find_namespace_packages(),
)
