"""
Utility functions for dealing with users within the IDS.
Includes functions for syncronizing users and groups, as
well as functions for retrieving lists of users and groups
from both iRODS and LDAP that conform to IDS naming policies.
"""

from ids.utils import run_iquest, run_iadmin, get_local_zone



# we'll implement a cache of user ids to usernames since
# there are use cases for iterating over ACLs in collections
# and we want to avoid spurious iquest commands.
#
# There needs to be a cache per zone, since user to id mapping
# is zone specific.
user_id_cache = {}



def connect_to_directory(ldap_server):

    import ldap

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

    import ldap
    
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

    import ldap
    
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
            if 'member' in results[1]:
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



def synchronize_user_db(source_groups, dest_groups, remove=False, verbose=False):
    """
    This function compares the source of users/groups to the destination
    and makes any changes to the destination iRODS instance to make them
    the same.

    Takes as input two dictionaries that are indexed by group name. Each
    dictionary entry is a list of users that are members of the group.

    The remove flag indicates that items that don't exist in the source zone
    should be removed from the destination. Make sure this is false if you
    want to make sure that local changes to the user DB are retained.

    The verbose flag causes messages to be printed to indicate what
    synchronization stage is being performed.
    """

    if not source_groups or dest_groups == None:
        return None

    # remove groups locally that don't exist in IDS
    if remove:
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
    if remove:
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
                dest_groups[group] = []
                if verbose:
                    print('\tadded new group %s' % (group,))

    # can happen on initial sync if there is an error adding ids-user above
    if 'ids-user' not in dest_groups:
        if verbose:
            print("\tCannot synchronize group 'ids-user'. It does not exist locally!")
        return None


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
        if group == 'ids-user':
            continue

        if group not in dest_groups:
            if verbose:
                print('\tCannot synchronize group %s. It does not exist locally.' % (group,))
            continue

        # remove user from group
        for user in dest_groups[group]:
            if remove and user not in source_groups[group]:
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


def irods_user_to_id(username, verbose=None):
    """
    Look up a user in the iRODS user DB and return the
    user identifier (a number). If the user isn't found,
    return an empty string. If an error occurs, return None.

    username should be in the form 'user#zone'

    Note: this also works for looking up groups.
    """
    if not username:
        return None

    user = username.split('#', 1)
    if len(user) != 2:
        if verbose:
            print('irods_user_to_id: username should be of form "user#zone"')
        return None

    id_query = "select USER_ID where USER_NAME = '%s' and USER_ZONE = '%s'" % (user[0], user[1])
    id = run_iquest(id_query, format='%s', verbose=verbose)
    if id == None:
        return None
    elif not id:
        # user not found
        return ""
    else:
        # keep in string form, as this is what iRODS mostly works with
        return id.rstrip('\n')
    


def irods_id_to_user(id, zone=None, verbose=None):
    """
    Look up a user id in the iRODS user DB and return the
    user name. If the user isn't found, return an empty string.
    If an error occurs, return None.

    the username returned is in the form 'user#zone'
    
    Note: this also works for looking up groups.
    """
    if not id:
        return None

    if not zone:
        zone = get_local_zone(verbose)
        if not zone:
            return None

    # lookup user id in the cache first
    if zone in user_id_cache:
        if id in user_id_cache[zone]:
            return user_id_cache[zone][id]

    # no cache hit ... look it up
    user_query = "select USER_NAME, USER_ZONE where USER_ID = '%s'" % (id,)
    user = run_iquest(user_query, format='%s#%s', zone=zone, verbose=verbose)
    if user == None:
        return None
    elif not user:
        # user not found
        return ""
    else:
        # keep in string form, as this is what iRODS mostly works with
        user_name = user.rstrip('\n')
        if zone not in user_id_cache:
            user_id_cache[zone] = {}
        user_id_cache[zone][id] = user_name
        return user_name



def irods_user_exists(username, verbose=False):
    """
    Check if a particular user exists in iRODS. Returns
    1 if yes, and 0 if no, and -1 if some error occurred.
    """
    if not username:
        return -1

    user = username.split('#', 1)
    if len(user) != 2:
        if verbose:
            print('irods_user_to_id: username should be of form "user#zone"')
        return -1

    user_query = "select count(USER_NAME) where USER_NAME = '%s' and USER_ZONE = '%s'"
    exists = run_iquest(user_query % (user[0], user[1]), format='%s', verbose=verbose)
    if exists == None:
        return -1
    else:
        return int(exists)


    
def get_irods_group(groupname, verbose=False):
    """
    Return the list of members of the provided group,
    or the empty list if there are no members. If an
    error occurs, return None.
    """
    if not groupname:
        return None

    group_query = "select USER_NAME, USER_ZONE where USER_GROUP_NAME = '%s'"
    output = run_iquest(group_query % (groupname,), format='%s#%s', verbose=verbose)
    if output == None:
        return None

    return output.splitlines()
