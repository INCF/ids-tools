"""
Utility functions for managing users within the IDS. Includes
functions for syncronizing users and groups, as well as
functions for retrieving lists of users and groups from
both iRODS and LDAP that conform to IDS naming policies.
"""

import ldap

from ids.utils import run_iquest, run_iadmin


def connect_to_directory(ldap_server):

    if not ldap_server:
        return None
    
    try:
        con = ldap.initialize(ldap_server)
        con.start_tls_s()
        con.simple_bind_s('', '')
    except ldap.LDAPError, e:
        print 'Error binding to LDAP server %s' % (ldap_server,)
        print e
        return None

    return con



def do_ldap_search(connection, search_base, filter, attributes):
    """
    Wraps up the call to the search_s method of an ldap connection

    returns a list of search results, or None if some error
    """
    try:
        results = connection.search_s(search_base,
                                      ldap.SCOPE_SUBTREE,
                                      filter,
                                      attributes)
    except ldap.LDAPError, e:
        print 'Error doing an LDAP search:'
        print e
        return None

    return results



def get_ldap_group_membership():

    ldap_server = 'ldap://ldap.incf.org'
    search_base = 'ou=groups,dc=incf,dc=org'
    
    con = connect_to_directory(ldap_server)
    if con == None:
        return None

    search_results = do_ldap_search(con, search_base, '(cn=ids-*)', ['cn',])
    if not search_results:
        return None

    group_list = {}
    for results in search_results:
        group_list[results[1]['cn'][0]] = []

    for group in group_list:
        search_results = do_ldap_search(con, search_base,
                                        '(cn=%s)' % (group,), ['member',])
        if search_results == None:
            return None
        for results in search_results:
            for dn in results[1]['member']:
                group_list[group].append(ldap.dn.str2dn(dn)[0][0][1])
        
    return group_list



def get_irods_group_membership(zone):
    """
    Retrieves the IDS users and groups from iRODS. Only group names starting
    with 'ids-' are retrieved.

    Input: if 'zone' is provided, its the name of the remote zone for iquest.

    Returns: a dict where the key is the group name, and the value is a list
    of users who are members of the group.
    """

    query = "select USER_GROUP_NAME, USER_NAME where USER_GROUP_NAME like 'ids-%'"

    output = run_iquest(query, format='%s:%s', zone=zone)
    if output == None:
        # some error occurred
        return None

    group_list = {}

    for line in output.splitlines():
        if line.startswith('Zone is'):
            continue
        group, user = line.split(':')
        if not group == user:
            if group in group_list:
                group_list[group].append(user)
            else:
                group_list[group] = [ user, ]
        elif group not in group_list:
            group_list[group] = []  # empty group
        
    return group_list



def synchronize_user_db(source_groups, dest_groups, verbose=False):
    """
    This function compares the source of users/groups to the destination
    and makes any changes to the destination iRODS instance to make them
    the same.

    Takes as input two dictionaries that are indexed by group name. Each
    dictionary entry is a list of users that are members of the group.

    The verbose flag causes messages to be printed to indicate what
    synchronization stage is being performed.
    """

    if not source_groups or not dest_groups:
        return None

    # remove groups locally that don't exist in IDS
    if verbose:
        print('Removing groups no longer defined in the source zone...')
    for group in dest_groups:
        if group not in source_groups:
            if run_iadmin('rmgroup', [ group, ], verbose=verbose):
                if verbose:
                    print('\terror removing group %s' % (group,))
            else:
                if verbose:
                    print('\tremoved group %s' % (group,))

    # remove users that don't exist in IDS's ids-user group
    if verbose:
        print('Removing users that have been removed from \'ids-user\'...')
    if 'ids-user' in dest_groups:
        for user in dest_groups['ids-user']:
            if user not in source_groups['ids-user']:
                zone_user = user + '#incf'
                if run_iadmin('rmuser', [ zone_user, ], verbose=verbose):
                    if verbose:
                        print('\terror removing user %s' % (zone_user,))
                        print('\tThey might still own files in iRODS.')
                else:
                    if verbose:
                        print('\tremoved user %s' % (zone_user,))


    # Additions

    # add groups from IDS that don't exist locally
    if verbose:
        print('Adding new source zone groups...')
    for group in source_groups:
        if group not in dest_groups:
            if run_iadmin('mkgroup', [ group, ], verbose=verbose):
                if verbose:
                    print('\terror adding new group %s' % (group,))
            else:
                if verbose:
                    print('\tadded new group %s' % (group,))

    # add users from ids-user that don't exist locally
    if verbose:
        print('Adding new users from \'ids-user\'...')
    for user in source_groups['ids-user']:
        if user not in dest_groups['ids-user']:
            zone_user = user + '#incf'
            if run_iadmin('mkuser', [ zone_user, 'rodsuser' ], verbose=verbose):
                if verbose:
                    print('\terror adding new user %s' % (zone_user,))
            else:
                if verbose:
                    print('\tadded new user %s' % (zone_user,))
                if run_iadmin('atg', [ 'ids-user', zone_user ], verbose=verbose):
                    if verbose:
                        print('\terror adding %s to \'ids-user\' group' % (zone_user,))
                else:
                    if verbose:
                        print('\tadded %s to group \'ids-user\'' % (zone_user,))



    # Synchronize group membership (except for ids-user which has
    # already been processed)
    if verbose:
        print('Synchronizing group membership...')
    for group in source_groups:
        if group == 'ids-user': continue

        # remove user from group
        for user in dest_groups[group]:
            if user not in source_groups[group]:
                zone_user = user + '#incf'
                if run_iadmin('rfg', [group, zone_user], verbose=verbose):
                    if verbose:
                        print('\terror removing %s from group %s' % (zone_user, group))
                else:
                    if verbose:
                        print('\tremoved user %s from group %s' % (zone_user, group))
                    
        # add users to group
        for user in source_groups[group]:
            if user not in dest_groups[group]:
                zone_user = user + '#incf'
                if run_iadmin('atg', [ group, zone_user], verbose=verbose):
                    if verbose:
                        print('\terror adding %s to group %s' % (zone_user, group))
                else:
                    if verbose:
                        print('\tadded user %s to group %s' % (zone_user, group))

    return 1
