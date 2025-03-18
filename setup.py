from setuptools import setup, find_packages

from src.release import __version__  # Update this import path


def read_file(file_name):
    """Read file and return its contents."""
    with open(file_name, 'r') as f:
        return f.read()


def read_requirements(file_name):
    """Read requirements file as a list."""
    reqs = read_file(file_name).splitlines()
    if not reqs:
        raise RuntimeError(
            "Unable to read requirements from the %s file"
            "That indicates this copy of the source code is incomplete."
            % file_name
        )
    return reqs


setup(
    name='glacier-rsync',
    version=__version__,
    url='https://github.com/cagdasbas/glacier-rsync',
    python_requires='>=3.8',
    description='Rsync like utility for backing up files/folders to AWS Glacier',
    long_description=read_file('README.md'),
    long_description_content_type="text/markdown",
    author='Cagdas Bas',
    author_email='cagdasbs@gmail.com',
    package_dir={"": "src"},  # Add this line
    packages=find_packages("src"),  # Update this line
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "grsync = src.__main__:main",  # Update this line
        ]
    },
    install_requires=read_requirements('requirements.txt'),
    extras_require={
        'compression': ["zstandard"],
        'encryption': ["cryptography"],
        'full': ["zstandard", "cryptography", "tqdm"]
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
