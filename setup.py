from distutils.core import setup
import setuptools
import versioneer


setup(name='databroker-browser',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      packages=['databroker_browser',
                'databroker_browser.qt'],
      install_requires=['matplotlib', 'six', 'numpy'],
     )
