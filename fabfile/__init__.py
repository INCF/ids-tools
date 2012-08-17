import setup
import manage
from fabric.api import env, task, execute

env.use_ssh_config = True

@task
def setup_ds():
    execute(manage.get_server_info)
    execute(setup.install_packages)
    execute(setup.configure_irods)
    execute(manage.start_irods)
    execute(setup.setup_root_irodsenv)
    execute(setup.clean_tmpdir)
    if env.vault_path:
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
