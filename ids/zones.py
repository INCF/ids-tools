"""
Utility functions for dealing with zones within the IDS.
Includes functions for retrieving zone information as
well as functions for creating and deleting zones.
"""

from ids.utils import run_iquest, run_iadmin



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

    Returns a dict of dicts, where the key of the top-level
    dict is the zone name, and the sub-dict contains the
    zone details including: type, endpoint, comment,
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
            'name': fields[0],
            'type': fields[1],
            'connection': fields[2],
            'comment': fields[3],
            'create_time': fields[4],
            'modification_time': fields[5],
            }
        zones.append(zone)

    return zones
