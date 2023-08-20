import setuptools

if __name__ == "__main__":
    setuptools.setup(
        name='fulgens',
        version='0.2.0',
        description='COMPFEST Attack-and-Defense CTF challenge checker helper',
        author='CTF COMPFEST',
        py_modules=["fulgens"],
        install_requires=["fabric (>3.0, <4.0)", "PyYAML (>5.0, <7.0)"],
    )