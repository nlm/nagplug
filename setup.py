from setuptools import setup, find_packages

setup(
    name = "nagplug",
    version = "1.1",
    packages = find_packages(),
    author = "Nicolas Limage",
    description = ("Nagios guidelines-compliant monitoring "
                   "plugin creation library (Shinken, Icinga, Centreon)"),
    license = "MIT",
    keywords = "nagios plugin shinken icinga centreon monitoring",
    url = "https://github.com/nlm/nagplug",
    test_suite = 'test_nagplug',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: System :: Monitoring',
    ],
)
