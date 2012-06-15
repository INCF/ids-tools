import os
import string
import random

from fabric.api import *
from fabric.contrib.files import upload_template, sed


# where to download the irods packages from
apt_sources = 'incf.list'
apt_key_url = 'http://apt-dbio-west.s3.amazonaws.com/pubkey.gpg'


# misc variables ... you probably don't want to change these
odbc_driver_file = '/usr/share/psqlodbc/odbcinst.ini.template'
psql_cmd = "PGPASSWORD=%s psql -h %s -U %s -d %s -f %s"
irods_default_zone = 'tempZone'
irods_schema_dir = '/usr/lib/irods/schema'


@task
def setup_zone():
    execute(install_packages, is_icat=True)
    execute(create_icat_db)
    execute(create_icat_schema)
    execute(configure_irods, is_icat=True)
    execute(start_irods)
    execute(setup_icat)
    execute(setup_root_irodsenv)
    execute(clean_tmpdir)


@task
def setup_ds():
    execute(install_packages)
    execute(configure_irods)
    execute(start_irods)
    execute(setup_root_irodsenv)
    execute(clean_tmpdir)
    

@task
def install_packages(is_icat=False):
    # set up the apt repo for irods packages
    put(os.path.join(env.templates, apt_sources), '/etc/apt/sources.list.d', use_sudo=True)
    sudo('wget -O - %s | apt-key add -' % (apt_key_url,))
    sudo('apt-get update')
    # install required packages
    if is_icat:
        sudo('apt-get -y install postgresql odbc-postgresql')
    sudo('apt-get -y install irods-server')


@task
def create_icat_db():
    execute(create_tmpdir)
    
    # install Postgres's ODBC driver in the system /etc/odbcinst.ini
    # sed part makes sure connection logging is turned off
    sudo("cat %s | sed -e 's/^CommLog.*/CommLog\t= 0/' | odbcinst -i -d -r" % (odbc_driver_file,))

    # set up the ICAT database and user
    sudo('createuser -e -SDRl %s' % (env.db_user,), 
         user='postgres')
    sudo('psql -c "ALTER ROLE %s ENCRYPTED PASSWORD \'%s\'"' % (env.db_user, env.db_pass), 
         user='postgres')
    sudo('createdb -e -O %s %s' % (env.db_user, env.db_name),
         user='postgres')

    # set up the ODBC DSN
    odbc_ini = os.path.join(env.tmpdir, 'odbc.ini')
    upload_template(os.path.join(env.templates, 'odbc.ini.tmpl'),
                    odbc_ini, context=env)
    sudo('odbcinst -i -s -l -f %s' % (odbc_ini,))
    

@task
def create_icat_schema():
    execute(create_tmpdir)

    # prep schema files
    run('cp %s %s' % (os.path.join(irods_schema_dir, '*'), env.tmpdir))
    run('perl %s postgres %s' % (os.path.join(env.tmpdir, 'convertSql.pl'), env.tmpdir))
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
                        '/etc/irods/server.config', context=env, use_sudo=True, mode=0600)
    else:
        upload_template(os.path.join(env.templates, 'server.config.tmpl'),
                        '/etc/irods/server.config', context=env, use_sudo=True, mode=0600)
    sudo('chown rods:rods /etc/irods/server.config*')

    upload_template(os.path.join(env.templates, 'server.env.tmpl'),
                    '/etc/irods/server.env', context=env, use_sudo=True, mode=0644)
    sudo('chown rods:rods /etc/irods/server.env*')

    # set up the server's credentials
    with settings(hide('running', 'stdout', 'stderr'), warn_only=True):
        with prefix('. /etc/irods/server.env'):
            sudo('iinit %s' % (env.irods_pass,), user='rods')


@task
def start_irods():
    sudo('/usr/bin/irods start', user='rods')

    
@task
def setup_icat():
    execute(create_tmpdir)
    
    env.irods_boot_user = 'rodsBoot'

    # sets up the initial zone namespace
    upload_template(os.path.join(env.templates, 'irodsBootEnv.tmpl'),
                    '%s/.irodsBootEnv' % (env.tmpdir,), context=env)
    with prefix('. %s/.irodsBootEnv' % (env.tmpdir,)):
        run('iinit RODS')
        run('imkdir /%s' % (env.irods_zone,))
        run('imkdir /%s/home' % (env.irods_zone,))
        run('imkdir /%s/trash' % (env.irods_zone,))
        run('imkdir /%s/trash/home' % (env.irods_zone,))
        run('iadmin mkgroup public')
        run('iadmin mkuser %s rodsadmin' % (env.irods_user,))
        run('iadmin moduser irods password %s' % (env.irods_pass,))
        run('ichmod own %s /' % (env.irods_user,))
        run('ichmod own %s /%s' % (env.irods_user, env.irods_zone))
        run('ichmod own %s /%s/home' % (env.irods_user, env.irods_zone))
        run('ichmod own %s /%s/trash' % (env.irods_user, env.irods_zone))
        run('ichmod own %s /%s/trash/home' % (env.irods_user, env.irods_zone))
        run('ichmod read public /')
        run('ichmod read public /%s' % (env.irods_zone, ))
        run('iadmin moduser rodsBoot password %s' % (env.irods_pass,))


@task
def setup_root_irodsenv():
    # set up the root user to be able to act as the iRODS admin user
    sudo('mkdir -p /root/.irods')
    upload_template(os.path.join(env.templates, 'irodsEnv.tmpl'),
                    '/root/.irods/.irodsEnv', context=env, use_sudo=True)
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

