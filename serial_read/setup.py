from setuptools import setup

setup(
        name='serialtalk',
        version='0.5',
        author = "Clément Bourguignon",
        author_email = "clement.bourguignon@mail.mcgill.ca",
        description='Open Arduino''s serial port and encode incoming message to files',
        license = "MIT",
        py_modules=['serial_read', 'serial_read_wheels'],
        install_requires=['Click','pyserial', 'numpy', 'pandas', 'matplotlib'],
        entry_points='''
            [console_scripts]
            serialtalk=serial_read:cli
            serialtalkw=serial_read_wheels:cli
        '''
        )
