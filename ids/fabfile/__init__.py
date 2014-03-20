import os

from fabric.api import env, task, execute

import setup
import manage

env.use_ssh_config = True

# Fabric needs ~/.ssh/config to exist (even if empty) when
# use_ssh_config is set, so make sure it exists
dot_ssh = os.path.join(os.environ.get('HOME', ''), '.ssh')
if not os.path.isdir(dot_ssh):
    os.mkdir(dot_ssh, 0700)
ssh_config = os.path.join(dot_ssh, 'config')
if not os.path.isfile(ssh_config):
    open(ssh_config, 'a').close()

@task
def setup_ds():
    execute(manage.get_server_info)
    execute(setup.install_packages)
    execute(setup.configure_irods)
    execute(manage.start_irods)
    execute(setup.setup_root_irodsenv)
    execute(setup.clean_tmpdir)
    if 'vault_path' in env:
        execute(manage.add_resource)
    
@task
def setup_zone():
    execute(manage.get_server_info)
    execute(setup.install_packages, is_icat=True)
    execute(setup.create_icat_db)
    execute(setup.create_icat_schema)
    execute(setup.configure_irods, is_icat=True)
    execute(manage.start_irods)
    execute(setup.setup_icat)
    execute(setup.setup_root_irodsenv)
    execute(setup.clean_tmpdir)
