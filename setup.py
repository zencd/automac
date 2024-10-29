import sys
from setuptools import setup

dev_requirements = ['pytest>=7.0', 'twine>=4.0.2']

if len(sys.argv) >= 2 and sys.argv[1] == 'print-dev-requirements':
    for dep in dev_requirements:
        print(dep)
else:
    setup(
        name='automac',
        version='1.0.0',
        long_description='A utility (framework) to configure macos to a wanted state in one step. You write configurations in Python.',
        long_description_content_type='text/markdown',
        package_dir={'': 'src'},
        install_requires=[],
        extras_require={'dev': dev_requirements},
    )
