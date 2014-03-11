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
