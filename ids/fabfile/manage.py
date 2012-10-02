from fabric.api import *
from fabric.contrib.console import confirm
from fabric.contrib.files import upload_template, sed, uncomment, exists

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
    
    if stat_list[1] != 'irods':
        print('The provided storage path needs to be owned by user "irods"')
        if confirm('Set correct storage path ownership?', default=False):
           sudo('chown irods:irods %s' % (env.vault_path,))
        else:
            abort('Cannot set up resource.')

    # run iadmin to add the resource
    with settings(sudo_prefix="sudo -i -S -p '%(sudo_prompt)s'"):
        sudo('iadmin mkresc %s "unix file system" archive %s %s'
             % (env.resc_name, env.irods_host, env.vault_path))


@task
def remove_resource():
    # run iadmin to remove the resource
    # iadmin will throw an error if there are issues
    with settings(sudo_prefix="sudo -i -S -p '%(sudo_prompt)s'"):
        sudo('iadmin rmresc %s' % (env.resc_name,))


@task
def get_server_info():
    env.remote_hostname = run('hostname')
    distribution = run('lsb_release -i')
    env.distribution = distribution.split(':')[1].strip('\t').lower()
    codename = run('lsb_release -c')
    env.codename = codename.split(':')[1].strip('\t')


@task
def start_irods():
    # make sure it's set to start at boot
    sed('/etc/default/irods',
        'START_IRODS=no',
        'START_IRODS=yes',
        use_sudo=True)
    sudo('service irods start')

    

