"""
Utility functions for dealing with resources within a zone.
Includes functions for retrieving resource information as
well as functions for creating and deleting resources.
"""

from ids.utils import run_iquest, run_iadmin



def get_resource_list(verbose=False):
    """
    This function retrieves a list of all the resources
    within the local zone.

    Returns a list sorted by resource name, or None if
    some error occurred.
    """

    output = run_iquest('select order(RESC_NAME)',
                        format='%s', verbose=verbose)
    if not output:
        return None

    return [resource.rstrip('\n') for resource in output.splitlines()]



def get_resource_details(resource_name=None, verbose=False):
    """
    This function will retrieve the details of all
    the resources defined within the local zone.
    If resource_name is provided, only the details 
    for that resource will be returned.

    Returns a dict of dicts, where the key of the top-level
    dict is the resource name, and the sub-dict contains the
    resource details including: type, endpoint, comment,
    and creation and modification timestamps. Will return
    None if some error occurred.
    """

    sep = '~_~'
    query_fields = [
        'RESC_NAME',
        'RESC_ZONE_NAME',
        'RESC_TYPE_NAME',
        'RESC_CLASS_NAME',
        'RESC_LOC',
        'RESC_VAULT_PATH',
        'RESC_STATUS',
        'RESC_INFO',
        'RESC_COMMENT',
        'RESC_CREATE_TIME',
        'RESC_MODIFY_TIME',
        ]
    query_format = sep.join(['%s'] * len(query_fields))
    
    query = 'select %s' % (','.join(query_fields))
    if resource_name:
        query = query + " where RESC_NAME = '%s'" % (resource_name,)

    output = run_iquest(query, format=query_format, verbose=verbose)
    if not output:
        return None

    resources = {}
    for line in output.splitlines():
        fields = line.split(sep)
        resource = {
            'zone_name': fields[1],
            'type': fields[2],
            'class': fields[3],
            'server': fields[4],
            'vault_path': fields[5],
            'status': fields[6],
            'info': fields[7],
            'comment': fields[8],
            'create_time': fields[9],
            'modification_time': fields[10],
            }
        resources[fields[0]] = resource

    return resources
