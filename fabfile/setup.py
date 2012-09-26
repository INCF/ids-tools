import os
import string
import random
import re

from fabric.api import *
from fabric.contrib.files import upload_template, sed, uncomment, exists


# where to download the irods packages from
apt_sources = 'dbio.list'
apt_key_url = 'http://apt-dbio-west.s3.amazonaws.com/pubkey.gpg'


# misc variables ... you probably don't want to change these
odbc_driver_file = '/usr/share/psqlodbc/odbcinst.ini.template'
psql_cmd = "PGPASSWORD=%s psql -h %s -U %s -d %s -f %s"
irods_default_zone = 'tempZone'
irods_schema_dir = '/usr/lib/irods/schema'


@task
def install_packages(is_icat=False):
    # set up the apt repo for irods packages
    upload_template(os.path.join(env.templates, 'dbio.list.tmpl'),
                    '/etc/apt/sources.list.d/dbio.list', 
                    context=env, use_sudo=True, mode=0644)
    sudo('wget -O - %s | apt-key add -' % (apt_key_url,))
    sudo('apt-get -qq update')

    # install required packages
    if is_icat:
        sudo('apt-get -q -y install postgresql odbc-postgresql cpp')
    sudo('apt-get -q -y install irods-server ssl-cert')


@task
def create_icat_db():
    execute(create_tmpdir)

    # install Postgres's ODBC driver in the system /etc/odbcinst.ini
    # sed part makes sure connection logging is turned off
    sudo('rm -f /etc/odbcinst.ini')
    sudo("cat %s | sed -e 's/^CommLog.*/CommLog\t= 0/' | odbcinst -i -d -r"
         % (odbc_driver_file,))

    # set up the ICAT database and user
    sudo('createuser -e -SDRl %s'
         % (env.db_user,), user='postgres')
    sudo('psql -c "ALTER ROLE %s ENCRYPTED PASSWORD \'%s\'"'
         % (env.db_user, env.db_pass), user='postgres')

    # use template0 so we can specify C collation for irods
    sudo('createdb --lc-collate=C -T template0 -e -O %s %s'
         % (env.db_user, env.db_name), user='postgres')

    # modify some database settings
    sudo('psql -c "ALTER DATABASE %s SET standard_conforming_strings TO off"'
         % (env.db_name,), user='postgres')
    
    # set up the ODBC DSN
    odbc_ini = os.path.join(env.tmpdir, 'odbc.ini')
    upload_template(os.path.join(env.templates, 'odbc.ini.tmpl'),
                    odbc_ini, context=env)
    sudo('odbcinst -i -s -l -f %s' % (odbc_ini,))
    

@task
def create_icat_schema():
    execute(create_tmpdir)

    # prep schema files
    run('cp %s %s'
        % (os.path.join(irods_schema_dir, '*'), env.tmpdir))
    run('perl %s postgres %s'
        % (os.path.join(env.tmpdir, 'convertSql.pl'), env.tmpdir))
    sed(os.path.join(env.tmpdir, 'icatSysInserts.sql'),
        irods_default_zone, env.irods_zone)

    # load schema
    run(psql_cmd % (env.db_pass, env.db_host, env.db_user, env.db_name,
                    os.path.join(env.tmpdir, 'icatCoreTables.sql')))
    run(psql_cmd % (env.db_pass, env.db_host, env.db_user, env.db_name,
                    os.path.join(env.tmpdir, 'icatSysTables.sql')))
    run(psql_cmd % (env.db_pass, env.db_host, env.db_user, env.db_name,
                    os.path.join(env.tmpdir, 'icatCoreInserts.sql')))
    run(psql_cmd % (env.db_pass, env.db_host, env.db_user, env.db_name,
                    os.path.join(env.tmpdir, 'icatSysInserts.sql')))
     

@task
def configure_irods(is_icat=False):

    if is_icat:
        # generate a scramble key for the DB password,
        # and scramble the DB password (for the server.config)
        env.db_key = ''.join(random.choice(string.ascii_lowercase+string.ascii_uppercase+string.digits)
                             for x in range(6))
        env.db_spass = run("iadmin spass %s %s | sed -e 's/Scrambled form is://'"
                           % (env.db_pass, env.db_key))
        upload_template(os.path.join(env.templates, 'icat.config.tmpl'),
                        '/etc/irods/server.config', 
                        context=env, use_sudo=True, mode=0600)
    else:
        upload_template(os.path.join(env.templates, 'server.config.tmpl'),
                        '/etc/irods/server.config', 
                        context=env, use_sudo=True, mode=0600)
    sudo('chown irods:irods /etc/irods/server.config*')

    if is_icat:
        upload_template(os.path.join(env.templates, 'ids-src.re.tmpl'),
                        '/etc/irods/reConfigs/ids-src.re',
                        context=env, use_sudo=True, mode=0644)
        sudo('chown irods:irods /etc/irods/reConfigs/ids-src.re*')

    upload_template(os.path.join(env.templates, 'ids.re.tmpl'),
                    '/etc/irods/reConfigs/ids.re',
                    context=env, use_sudo=True, mode=0644)
    sudo('chown irods:irods /etc/irods/reConfigs/ids.re*')

    upload_template(os.path.join(env.templates, 'server.env.tmpl'),
                    '/etc/irods/server.env', 
                    context=env, use_sudo=True, mode=0644)
    sudo('chown irods:irods /etc/irods/server.env*')

    if is_icat:
        env.irods_host = env.icat_host
    env.irods_short_hostname = env.irods_host.split('.')[0]
    upload_template(os.path.join(env.templates, 'irodsHost.tmpl'),
                    '/etc/irods/irodsHost',
                    context=env, use_sudo=True, mode=0644)
    sudo('chown irods:irods /etc/irods/irodsHost')

    # set up the server's credentials
    with settings(hide('running', 'stdout', 'stderr'), warn_only=True):
        with prefix('. /etc/irods/server.env'):
            sudo('iinit %s' % (env.irods_pass,), user='irods')


@task
def setup_icat():
    execute(create_tmpdir)
    
    env.irods_boot_user = 'rodsBoot'

    # sets up the initial zone namespace
    upload_template(os.path.join(env.templates, 'irodsBootEnv.tmpl'),
                    '%s/.irodsBootEnv' % (env.tmpdir,), context=env)
    # this is used to set up a "specific query" that results in a
    # compact ACL display for collections when using 'ils -A'
    upload_template(os.path.join(env.templates, 'compact_ils_sq.tmpl'),
                    '%s/compact_ils_sq' % (env.tmpdir,), context=env)
    with prefix('. %s/.irodsBootEnv' % (env.tmpdir,)):
        run('iinit RODS')
        run('imkdir /%s' % (env.irods_zone,))
        run('imkdir /%s/home' % (env.irods_zone,))
        run('imkdir /%s/trash' % (env.irods_zone,))
        run('imkdir /%s/trash/home' % (env.irods_zone,))
        run('iadmin mkgroup public')
        run('iadmin mkuser %s rodsadmin' % (env.irods_user,))
        run('iadmin moduser %s password %s' % (env.irods_user, env.irods_pass))
        run('ichmod own %s /' % (env.irods_user,))
        run('ichmod own %s /%s' % (env.irods_user, env.irods_zone))
        run('ichmod own %s /%s/home' % (env.irods_user, env.irods_zone))
        run('ichmod own %s /%s/trash' % (env.irods_user, env.irods_zone))
        run('ichmod own %s /%s/trash/home' % (env.irods_user, env.irods_zone))
        run('ichmod read public /')
        run('ichmod read public /%s' % (env.irods_zone,))
        run('ichmod read public /%s/home' % (env.irods_zone,))
        run('iadmin moduser rodsBoot password %s' % (env.irods_pass,))


@task
def setup_root_irodsenv():
    # set up the root user to be able to act as the iRODS admin user
    sudo('mkdir -p /root/.irods')
    upload_template(os.path.join(env.templates, 'irodsEnv.tmpl'),
                    '/root/.irods/.irodsEnv', context=env, use_sudo=True)
    sudo('chown root:root /root/.irods/.irodsEnv')
    sudo('chmod 644 /root/.irods/.irodsEnv')
    with settings(sudo_prefix="sudo -i -S -p '%(sudo_prompt)s'"):
        sudo('iinit %s' % (env.irods_pass,))


@task
def create_tmpdir():
    if not 'tmpdir' in env or not env.tmpdir:
        env.tmpdir = run('mktemp -d')


@task
def clean_tmpdir():
    if 'tmpdir' in env and env.tmpdir:
        run('rm -rf %s' % (env.tmpdir,))
        del env['tmpdir']


