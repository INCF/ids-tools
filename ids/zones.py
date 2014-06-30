"""
Utility functions for dealing with zones within the IDS.
Includes functions for retrieving zone information as
well as functions for creating and deleting zones.
"""
import os

from ids.utils import run_iquest, run_iadmin, shell_command



def get_local_zone(verbose=False):
    """
    This function retrieves the name of the local
    zone using an iquest query.

    Returns the name of the local zone, or None if
    some error occurred.
    """

    zname = run_iquest("select ZONE_NAME where ZONE_TYPE = 'local'",
                       format='%s', verbose=verbose)
    if zname == None:
        return None

    return zname.rstrip('\n')



def get_zone_list(verbose=False):
    """
    This function retrieves a list of all the zones
    within the IDS.

    Returns a list sorted by zone name, or None if
    some error occurred.
    """

    output = run_iquest('select order(ZONE_NAME)',
                        format='%s', verbose=verbose)
    if not output:
        return None

    return [zone.rstrip('\n') for zone in output.splitlines()]


def get_zone_details(zone_name=None, verbose=False):
    """
    This function will retrieve the details of all
    the zones defined within the IDS. If zone_name
    is provided, only the details for that zone will
    be returned.

    Returns a array of dicts with each array element
    representing a zone, and the dict contains the
    zone details including: name, type, endpoint, comment,
    and creation and modification timestamps. Will return
    None if some error occurred.
    """

    sep = '~_~'
    query_fields = [
        'ZONE_NAME',
        'ZONE_TYPE',
        'ZONE_CONNECTION',
        'ZONE_COMMENT',
        'ZONE_CREATE_TIME',
        'ZONE_MODIFY_TIME',
        ]
    query_format = sep.join(['%s'] * len(query_fields))

    query = 'select %s' % (','.join(query_fields))
    if zone_name:
        query = query + " where ZONE_NAME = '%s'" % (zone_name,)

    output = run_iquest(query, format=query_format, verbose=verbose)
    if output is None:
        return None

    zones = []
    for line in output.splitlines():
        fields = line.split(sep)
        zone = {
            'zone_name': fields[0],
            'type': fields[1],
            'connection': fields[2],
            'comment': fields[3],
            'create_time': fields[4],
            'modification_time': fields[5],
            }
        zones.append(zone)

    return zones


def make_zone(zone_name, endpoint, comment=None):
    """
    This function calls iadmin mkzone to create a new
    remote zone definition. The endpoint is of the
    form hostname:port.

    On success make_zone will return a dict representing
    the new zone details. On failure, None will be returned.
    """

    if not zone_name or not endpoint:
        return None

    # TODO: validity check endpoint
    mkzone_args = [ zone_name, 'remote', endpoint ]
    if comment:
        mkzone_args.append(comment)
    if run_iadmin('mkzone', mkzone_args):
        return None

    newzone = get_zone_details(zone_name)

    return newzone[0]



def modify_zone(zone_name, endpoint=None, comment=None):
    """
    This function calls iadmin modzone to update a
    remote zone definition (endpoint or comment). The
    endpoint is of the form hostname:port. At this
    time, mod_zone will not support changing the zone name.

    On success mod_zone will return a dict representing
    the new zone details. On failure, None will be returned.
    """

    if not zone_name:
        return None

    if comment and run_iadmin('modzone', [zone_name, 'comment', comment]):
        return None

    if endpoint and run_iadmin('modzone', [zone_name, 'conn', endpoint]):
        return None

    zone = get_zone_details(zone_name)

    return zone[0]



def remove_zone(zone_name):
    """
    This function will remove a zone definition from icat.

    Returns 0 on success and -1 on error.
    """
    if not zone_name:
        return 0

    return run_iadmin('rmzone', [zone_name,])



def check_zone_endpoint(zone_name, endpoint):
    """
    This function will check if the iRODS service is
    available at the provided endpoint, and if the zone
    name is accurate.

    Returns a tuple with the first element being True if
    the check was successful (and None in the second element),
    or False with a string reason as the second tuple element.
    """

    if not zone_name or not endpoint:
        return (False, 'zone_name and endpoint must be specified')

    if endpoint.count(':') != 1:
        return (False, 'malformed endpoint. Should be host:port')

    host, port = endpoint.split(':')

    env_dict = dict(os.environ)
    env_dict['irodsHost'] = host
    env_dict['irodsPort'] = port

    (rc, output) = shell_command(['imiscsvrinfo',], environment=env_dict)
    if rc:
        if ('SYS_PACK_INSTRUCT_FORMAT_ERR' in output[1]
            or 'SYS_SOCK_READ_TIMEDOUT' in output[1]
            or 'SYS_HEADER_READ_LEN_ERR' in output[1]):
            reason = 'a service other than iRODS is running on port %s' % port
        elif 'USER_SOCK_CONNECT_ERR' in output[1]:
            if 'Connection timed out' in output[1]:
                reason = 'timed out connecting to port %s. Is there a firewall in place?' % port
            else:
                reason = 'no service is running on port %s' % port
        elif 'USER_RODS_HOSTNAME_ERR' in output[1]:
            reason = 'could not resolve hostname %s' % host
        else:
            reason = 'error running imiscsvrinfo'
        return (False, reason)

    for line in output[0].splitlines():
        if line.startswith('rodsZone='):
            k, v = line.split('=')
            if v == zone_name:
                return (True, None)
            else:
                return (False, 'zone name %s did not match remote zone %s' % (zone_name, v))

    # could connect to server, but zone name didn't match
    return (False, 'could not determine remote zone name')
