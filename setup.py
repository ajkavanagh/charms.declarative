from setuptools import setup
import os


version_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'VERSION'))
with open(version_file) as v:
    VERSION = v.read().strip()


SETUP = {
    'name': "charms.declarative",
    'version': VERSION,
    'author': "Charm Declarative Framework Maintainers",
    # temporary, until we assign it in some way (we are skunk works!)
    'author_email': "alex@ajkavanagh.co.uk",
    'url': "https://github.com/ajkavanagh/charms.declarative",
    'packages': [
        "charms",
        "charms.declarative",
    ],
    'install_requires': [
        'pyaml',
        'charmhelpers',
    ],
    'license': "Apache License 2.0",
    'long_description': open('README.rst').read(),
    'description': 'Framework for writing reactive-style Juju Charms',
}

try:
    from sphinx_pypi_upload import UploadDoc
    SETUP['cmdclass'] = {'upload_sphinx': UploadDoc}
except ImportError:
    pass

if __name__ == '__main__':
    setup(**SETUP)
