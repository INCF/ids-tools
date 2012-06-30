from fabric.api import *
from fabric.contrib.console import confirm

@task
def add_resource():
    # check if the vault path exists and that permissions are right
    stat_cmd = 'stat --format="%F:%U:%G" ' + env.vault_path + ' 2> /dev/null || echo nopath:0:0'
    stat_out = run(stat_cmd)
    stat_list = stat_out.split(':')

    if stat_list[0] == 'nopath':
        abort('Error: provided storage path %s does not exist on %s'
              % (env.vault_path, env.irods_host))

    if stat_list[0] != 'directory':
        abort('Error: provided storage path %s is not a directory'
              % (env.vault_path,))
    
    if stat_list[1] != 'rods':
        print('The provided storage path needs to be owned by user "rods"')
        if confirm('Set correct storage path ownership?', default=False):
           sudo('chown rods:rods %s' % (env.vault_path,))
        else:
            abort('Cannot set up resource.')

    # run iadmin to add the resource
    sudo('iadmin mkresc %s "unix file system" archive %s %s'
         % (env.resc_name, env.irods_host, env.vault_path))


@task
def remove_resource():
    # run iadmin to remove the resource
    # iadmin will throw an error if there are issues
    sudo('iadmin rmresc %s' % (env.resc_name,))


@task
def ping_server():
    # just used to see if we can connect properly with fab
    # and shows under what user ids we're being run
    run('lsb_release -a')
    run('uname -a')
    run('id -a')
    sudo('id -a')

@task
def get_server_info():
    env.remote_hostname = run('hostname')
    distribution = run('lsb_release -i')
    env.distribution = distribution.split(':')[1].strip('\t')
    codename = run('lsb_release -c')
    env.codename = codename.split(':')[1].strip('\t')
    
