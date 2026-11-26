from .moments import install
import runpy

if __name__=='__main__':
    install()
    runpy.run_module('shortsflow',run_name='__main__')
