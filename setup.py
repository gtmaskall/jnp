from setuptools import setup, find_packages

setup(
    name='jnp',
    version='2020.1.0',
    url='TODO',
    author='Guy Maskall',
    author_email='guymaskall@gmail.com',
    description='Jupyter notebook processing',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
)
