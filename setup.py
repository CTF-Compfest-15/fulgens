import setuptools

if __name__ == "__main__":
    setuptools.setup(
        name='Fulgens',
        version='0.1.0',
        description='COMPFEST Attack-and-Defense CTF challenge checker helper',
        author='CTF COMPFEST',
        py_modules=["fulgens"],
        requires=["fabric (>3.0, <4.0)", "PyYAML (>5.0, <7.0)"],
    )