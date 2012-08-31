"""
Functions that are used to get information about, and manipulate,
the iRODS namespace. Anything you might want to do with collections
and data objects in ICAT that doesn't actually change bits on disk
go in this module.
"""

from ids.utils import run_iquest, shell_command
from ids.users import irods_id_to_user



def irods_coll_exists(coll, verbose=False):
    """
    This function checks whether the provided
    collection name 'coll' exists in the iRODS
    namespace. Returns 1 if yes, and 0 if not,
    and -1 if some error occurred during the lookup.

    Note: a 0 return just means the path isn't a
    collection. There could still be a data object
    with the same path name.
    """

    if not coll:
        return -1

    coll_query = "select count(COLL_NAME) where COLL_NAME = '%s'" % (coll,)
    exists = run_iquest(coll_query, format='%s', verbose=verbose)
    if exists == None:
        return -1

    return int(exists)



def irods_obj_exists(obj, verbose=False):
    """
    This function checks whether the provided
    data object name 'obj' exists in the iRODS
    namespace. Returns 1 if yes, and 0 if not,
    and -1 if some error occurred during the lookup.

    Note: a 0 return just means the path isn't a
    data object. There could still be a collection
    with the same path name.
    """

    if not obj:
        return -1

    obj_query = "select count(DATA_NAME) where DATA_NAME = '%s'" % (obj,)
    exists = run_iquest(obj_query, format='%s', verbose=verbose)
    if exists == None:
        return -1

    return int(exists)



def irods_coll_getacls(path, verbose=False):
    """
    This function returns a list of ACLs associated
    with the input iRODS collection. Each ACL consists of
    a 'user:access' pair, where access is the same
    as that used in the ichmod command.

    None is returned if an error occurred.
    """
    if not path:
        return None

    acl_list = []
    
    acl_query = "select COLL_ACCESS_NAME, COLL_ACCESS_USER_ID where COLL_NAME = '%s'"

    output = run_iquest(acl_query % (path,), format='%s:%s', verbose=verbose)
    if output == None:
        return None

    for line in output.splitlines():
        access, user_id = line.split(':')
        if access.startswith('read'):
            access = 'read'
        elif access.startswith('modify'):
            access = 'write'
        user_name = irods_id_to_user(user_id, verbose=verbose)
        acl_list.append([user_name, access])

    return acl_list



def irods_obj_getacls(path, verbose=False):
    """
    This function returns a list of ACLs associated
    with the input iRODS data object. Each ACL consists of
    a 'user:access' pair, where access is the same
    as that used in the ichmod command.

    None is returned if an error occurred.
    """
    if not path:
        return None

    acl_list = []
    
    acl_query = "select DATA_ACCESS_NAME, DATA_ACCESS_USER_ID where DATA_NAME = '%s'"

    output = run_iquest(acl_query % (path,), format='%s:%s', verbose=verbose)
    if output == None:
        return None

    for line in output.splitlines():
        access, user_id = line.split(':')
        if access.startswith('read'):
            access = 'read'
        elif access.startswith('modify'):
            access = 'write'
        user_name = irods_id_to_user(user_id, verbose=verbose)
        acl_list.append([user_name, access])

    return acl_list



def irods_mkdir(coll, verbose=False):
    """
    This function will create the iRODS collection
    named by the 'coll' argument, and all necessary
    parent collections (using 'imkdir -p').

    Returns 0 on success, non-zero on error.
    """
    if not coll:
        return 1

    (rc, output) = shell_command(['imkdir', '-p', coll])

    if rc != 0 and verbose:
        print("Error running 'imkdir -p %s': rc = %d:"
              % (coll, rc))
        print output[1]

    return rc



def irods_setacls(path, acl_list, verbose=False):
    """
    This function will add the ACLs listed in 'acl_list'
    to the collection or data object at 'path'.

    'acl_list' is a list where each element itself is
    a list consisting of the username in name#zone format,
    and the access level ('read', 'write', 'own', or 'null').
    Access type 'null' removes all ACLs for that user/group.

    Note. On an error return, some of the ACLs might have
    been applied. The function does not "roll back" on error.
    
    Returns 0 on success, non-zero on error.
    """
    
    if not path or not acl_list:
        return 1

    for acl in acl_list:
        (rc, output) = shell_command(['ichmod', acl[1], acl[0], path])
        if rc:
            if verbose:
                print("Error running 'ichmod %s %s %s': rc = %d:"
                      % (acl[1], acl[0], path, rc))
                print output[1]
            return rc

    return 0



def irods_setavus(path, avu_list, verbose=False):
    """
    This function will add the AVUs listed in 'avu_list'
    to the collection or data object at 'path'.

    'avu_list' is a list where each element itself is
    a list consisting of the type ('-C' for collection
    and '-d' for data object), attribute name, value
    and optional units. 

    Note. On an error return, some of the AVUs might have
    been applied. The function does not "roll back" on error.
    
    Returns 0 on success, non-zero on error.
    """
    
    if not path or not avu_list:
        return 1

    for avu in avu_list:
        imeta_cmd = ['imeta', 'add']
        imeta_cmd.append(avu[0])     # type ... -d or -C
        imeta_cmd.append(path)       # target collection or object
        imeta_cmd.append(avu[1])     # attribute name
        imeta_cmd.append(avu[2])     # attribute value
        if avu[3]:
            imeta_cmd.append(avu[3]) # units (if provided)
        (rc, output) = shell_command(imeta_cmd)
        if rc and 'Operation now in progress' not in output[1]:
            if verbose:
                print('Error running imeta add on %s: rc = %d:'
                      % (path, rc))
                print output[1]
            return rc

    return 0
