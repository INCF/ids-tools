import zone
import ds

from fabric.api import *

@task
def show_env():
    run('uname -a')
    with prefix('export MYVAR=myval'):
        with settings(warn_only=True):
            run_result = run('env | grep MYVAR')
            if run_result.failed:
                # it's ok
                print 'failed'
            else:
                print run_result

