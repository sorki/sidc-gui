from distutils.core import setup
import os

NAME = 'sidc-gui'
VERSION = '0.3'


# Compile the list of packages available, because distutils doesn't have
# an easy way to do this.
packages, data_files = [], []
root_dir = os.path.dirname(__file__)
if root_dir:
    os.chdir(root_dir)

for dirpath, dirnames, filenames in os.walk('sidc_gui'):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'): del dirnames[i]
    if '__init__.py' in filenames:
        pkg = dirpath.replace(os.path.sep, '.')
        if os.path.altsep:
            pkg = pkg.replace(os.path.altsep, '.')
        packages.append(pkg)
    elif filenames:
        prefix = dirpath[9:] # Strip "sidc_gui/" or "sidc_gui\"
        for f in filenames:
            data_files.append(os.path.join(prefix, f))


f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
long_description = f.read().strip()
f.close()




setup(name=NAME,
        version=VERSION,
        description='Sudden ionospheric disturbance colletor (sidc) GUI',
        long_description=long_description,
        author='Richard Marko',
        author_email='rissko@gmail.com',
        url='http://github.com/sorki/sidc_gui',
        license='BSD',
        package_dir={'sidc_gui': 'sidc_gui'},
        packages=packages,
        scripts=['sidc_gui/sidc_gui'],
        package_data={'sidc_gui': data_files},

        classifiers=['Development Status :: 4 - Beta',
                   'Environment :: X11 Applications',
                   'Intended Audience :: Science/Research',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Scientific/Engineering :: Visualization'],


    )

