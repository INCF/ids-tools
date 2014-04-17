"""
Some helpful functions for the other IDS modules and utilities
"""

import subprocess



def shell_command(command_list):
    """
    Performs a shell command using the subprocess object
    
    input list of strings that represent the argv of the process to create
    return tuple (return code, the output object from subprocess.communicate)
    """

    if not command_list:
        return None
        
    try:
        process = subprocess.Popen(command_list, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        output = process.communicate()
        return (process.returncode, output)
    except:
        return (-1, [None, None])



def run_iquest(query, format=None, zone=None, verbose=False):
    """
    Runs iquest with the given string iquest_query
    
    input string iquest command
    
    return [string, string] output in separate lines
    """

    if not query:
        return None
    
    command = ['iquest', '--no-page']

    if zone:
        command.append('-z')
        command.append(zone)
        
    if format:
        command.append(format)
        
    command.append(query)

    (rc, output) = shell_command(command)

    if 'CAT_NO_ROWS_FOUND' in output[0] or 'CAT_NO_ROWS_FOUND' in output[1]:
        return ""

    if rc != 0:
        if verbose:
            print('Error running %s, rc = %d'
                  % (' '.join(command), rc))
            print output[1]
        return None

    # get rid of 'Zone is X' first line
    if zone:
        return output[0][(output[0].find('\n')+1):]
    else:
        return output[0]



def run_iadmin(command, arglist, verbose=False):
    """
    runs the iadmin command given with the provided arguments

    returns 0 on success, or -1 on iadmin failure
    """

    if not command:
        return -1
    
    iadmin = [ 'iadmin', command ] + arglist

    (rc, output) = shell_command(iadmin)
    if rc != 0:
        if verbose:
            print('Error running %s, rc = %d'
                  % (' '.join(iadmin), rc))
            print output[1]
        return -1

    return 0
