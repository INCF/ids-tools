# ids-src.re
#
# Rules that implement the policies and procedures for the
# INCF Dataspace go here
#
# Once this file has been modified, ids-sync-zone-rules 
# should be called. That will upload the source rules into
# the ICAT DB for this zone, push them to the configured
# rule file (incf.re), and then push the change to all the
# data servers in the zone.
#



# 
# Turn off the "Trash Can"
#
# Generally wastes space as users forget to purge their trash.
#
acTrashPolicy {
  msiNoTrashCan;
}


#
# Strict ACL checking
#
# Make sure that ACLs are honoured when browsing the namespace. 
# Users must have at least "read" permission to icd into, and ils
# collections and see the files.
#
acAclPolicy {
  msiAclPolicy("STRICT");
}


#
# By default, acPostProcForPut is not called for bulk updates, but we
# will set the acBulkPutPostProcPolicy so that it is called for each
# file.
#
#acBulkPutPostProcPolicy {
#  msiSetBulkPutPostProcPolicy("on");
#}


# csmith - 2012-08-16
# we do want home collections for users in the incf zone, if 
# for no other reason just to have somewhere to start from
#
# We don't really want user homes for users from the incf zone,
# so override acCreateUserF1 here. Checks for usernames with #incf
# (which are users) and names like ids-* (which are groups).
#acCreateUserF1 {
#  ON ($otherUserName like "\*#incf"
#      || $otherUserName like "ids-*") {
#    msiCreateUser ::: msiRollback;
#    msiAddUserToGroup("public")  :::  msiRollback;
#    msiCommit;
#  }
#}

# csmith - 2013-03-27
# add a 5GB quota on the default resource when users
# are added to the system (acPostProcForCreateUser is a hook
# action for doing things at user creation)
acPostProcForCreateUser {
  msiSetQuota("user", $otherUserName, "org_org.incf_2", "5368709120");
}

# csmith - 2012-10-04
# we will create the /incf/home/user collection, but don't 
# need the trash, so override the default user collections
# creation/deletion rules here. 
acCreateUserZoneCollections {
  acCreateCollByAdmin("/incf/home", $otherUserName);
}
acDeleteUserZoneCollections {
  acDeleteCollByAdmin("/incf/home", $otherUserName);
}


#
# Here are the namespace rules for the zone. These will be used
# to map incoming requests to appropriate storage resources based
# either upon the path (for organizational resources) or based
# on the user name (for user resources).

# INCF Secretariat
acSetRescSchemeForCreate {
  ON ($objPath like "/incf/resources/org.incf/*") {
    msiSetDefaultResc("org_org.incf_2", "forced");   
  }
}
acSetRescSchemeForRepl {
  ON ($objPath like "/incf/resources/org.incf/*") {
    msiSetDefaultResc("org_org.incf_2", "forced");
  }
}


# sina 2013-04-16 german node resource
acSetRescSchemeForCreate {
  ON ($objPath like "/incf/resources/org.g-node/*") {
    msiSetDefaultResc("org_org.incf_3", "forced");
  }
}
acSetRescSchemeForRepl {
  ON ($objPath like "/incf/resources/org.g-node/*") {
    msiSetDefaultResc("org_org.incf_3", "forced");
  }
}

# IBIC @ UW
acSetRescSchemeForCreate {
  ON ($objPath like "/incf/resources/edu.washington.ibic/*") {
    msiSetDefaultResc("org_edu.washington.ibic_1", "forced");
  }
}
acSetRescSchemeForRepl {
  ON ($objPath like "/incf/resources/edu.washington.ibic/*") {
    msiSetDefaultResc("org_edu.washington.ibic_1", "forced");
  }
}

# allen institute
acSetRescSchemeForCreate {
  ON ($objPath like "/incf/resources/org.alleninstitute/*") {
    msiSetDefaultResc("org_org.alleninstitute_1", "forced");
  }
}
acSetRescSchemeForRepl {
  ON ($objPath like "/incf/resources/org.alleninstitute/*") {
    msiSetDefaultResc("org_org.alleninstitute_1", "forced");
  }
}

# Neuroinf french node 2014-02-26
acSetRescSchemeForCreate {
  ON ($objPath like "/incf/resources/fr.neuroinf/*") {
    msiSetDefaultResc("org_fr.neuroinf_1", "forced");
  }
}
acSetRescSchemeForRepl {
  ON ($objPath like "/incf/resources/fr.neuroinf/*") {
    msiSetDefaultResc("org_fr.neuroinf_1", "forced");
  }
}


# if a resource hasn't already been set based on path
# attempt to set the resource name to the user resource.
# rodsadmin users can set their own resource with -R.
#acSetRescSchemeForCreate {
#  ON (($rodsZoneClient == "incf") && ($privClient < "5")) {
#    msiSetDefaultResc("user_"++$userNameClient, "forced");
#  }
#}
#acSetRescSchemeForRepl {
#  ON (($rodsZoneClient == "incf") && ($privClient < "5")) {
#    msiSetDefaultResc("user_"++$userNameClient, "forced");
#  }
#}

#  *** sina: INCF has replaced the defaul resource ***
#  ***  to org_org.incf_2 *****
# if the resource hasn't been set by now set
# it to the default 'org_org.incf_2' resource
# Quotas will be turned on to encourage the
# use of other resources
acSetRescSchemeForCreate {
  msiSetDefaultResc("org_org.incf_2", "forced");
}
acSetRescSchemeForRepl {
  msiSetDefaultResc("org_org.incf_2", "forced");
}

#
# csmith 2013-03-27
#
# Don't let anybody set 'write' or 'own' permissions
# for the 'anonymous' user or 'public' group. The 
# resulting output on the client side is a bit "messy",
# but there is no other way to do this AFAIK.
acPreProcForModifyAccessControl(*recursive, *access, *user, *zone, *path) {
  on (*user == "anonymous" || *user == "public") {
    if (*access == "write" || *access == "own") {
      cut;
      msiExit("1", "Can't set 'write' or 'own' for user *user");
      fail;
    }
  }
}

#
# These rules are the entry points for taking action
# when something happens in iRODS (the 'post-action'
# rules). One application is to generate audit events.
#
acPostProcForOpen {
  acAuditEvent("acPostProcForOpen", $objPath, $rescName);
}
acPostProcForCreate {
  acAuditEvent("acPostProcForCreate", $objPath, $rescName);
}
acPostProcForPut {
  acAuditEvent("acPostProcForPut", $objPath, $rescName);
}
acPostProcForCopy {
  acAuditEvent("acPostProcForCopy", $objPath, $rescName);
}
acPostProcForRepl {
  acAuditEvent("acPostProcForRepl", $objPath, $rescName);
}
acPostProcForDelete {
  acAuditEvent("acPostProcForDelete", $objPath, $rescName);
}
acPostProcForCollCreate {
  acAuditEvent("acPostProcForCollCreate", $collName);
}
acPostProcForRmColl {
  acAuditEvent("acPostProcForRmColl", $collName);
}
acPostProcForFilePathReg {
  acAuditEvent("acPostProcForFilePathReg", $objPath, $rescName, $filePath);
}
acPostProcForObjRename(*sourceObject, *destObject) {
  acAuditEvent("acPostProcForObjRename", *sourceObject, *destObject);
}
# csmith 2013-03-27 - acPostProcForModifyAccessControl has some 
# extra logic so that if somebody adds a permission (or removes
# it) for the 'public' group, then the 'anonymous' user is
# also given the same permission
acPostProcForModifyAccessControl(*recursive, *access, *user, *zone, *path) {
  acAuditEvent("acPostProcForModifyAccessControl", *path, *user++"#"++*zone, *access, *recursive); 
  if (*user == "public") {
    if (*recursive == "1") {
      msiSetACL("recursive", *access, "anonymous#*zone", *path);
    }
    else {
      msiSetACL("default", *access, "anonymous#*zone", *path);
    }
  }
}
acPostProcForModifyAVUMetadata(*op, *type, *path, *a, *v, *u) {
  acAuditEvent("acPostProcForModifyAVUMetadata", *path, *op, *type, *a, *v, *u);
}
acPostProcForModifyAVUMetadata(*op, *type, *path, *a, *v) {
  acAuditEvent("acPostProcForModifyAVUMetadata", *path, *op, *type, *a, *v, "");
}

#
# Rules that are used to generate and log audit events.
# DO NOT CHANGE 
#
acAuditEvent(*ruleName, *target, *arg1, *arg2, *arg3, *arg4, *arg5) {
  on (*ruleName == 'acPostProcForModifyAVUMetadata') {
    *p = "target=*target";
    *p = "*p operation=*arg1";
    *p = "*p targettype=*arg2";
    *p = "*p attrname=*arg3";
    *p = "*p attrval=*arg4";
    *p = "*p attrunits=*arg5";
    acLogAuditEvent(*ruleName, *p);
  }
}

acAuditEvent(*ruleName, *target, *arg1, *arg2, *arg3) {
  on (*ruleName == 'acPostProcForModifyAccessControl') {
    *p = "target=*target";
    *p = "*p targetuser=*arg1";
    *p = "*p access=*arg2";
    *p = "*p recursive=*arg3";
    acLogAuditEvent(*ruleName, *p);
  }
}

acAuditEvent(*ruleName, *target, *arg1, *arg2) {
  on (*ruleName == 'acPostProcForFilePathReg') {
    acLogAuditEvent(*ruleName, "target=*target resource=*arg1 srcpath=*arg2");
  }
}

acAuditEvent(*ruleName, *target, *arg1) {
  on (*ruleName == 'acPostProcForOpen') {
    acLogAuditEvent(*ruleName, "target=*target resource=*arg1");
  }
  on (*ruleName == 'acPostProcForCreate') {
    acLogAuditEvent(*ruleName, "target=*target resource=*arg1");
  }
  on (*ruleName == 'acPostProcForPut') {
    acLogAuditEvent(*ruleName, "target=*target resource=*arg1");
  }
  on (*ruleName == 'acPostProcForCopy') {
    acLogAuditEvent(*ruleName, "target=*target resource=*arg1");
  }
  on (*ruleName == 'acPostProcForRepl') {
    acLogAuditEvent(*ruleName, "target=*target resource=*arg1");
  }
  on (*ruleName == 'acPostProcForDelete') {
    acLogAuditEvent(*ruleName, "target=*target resource=*arg1");
  }
  on (*ruleName == 'acPostProcForObjRename') {
    acLogAuditEvent(*ruleName, "target=*target newname=*arg1");
  }
}

acAuditEvent(*ruleName, *target) {
  acLogAuditEvent(*ruleName, "target=*target");
}

acLogAuditEvent(*ruleName, *params) {
  msiGetSystemTime(*ts, "unix");
  *u = $userNameClient++'#'++$rodsZoneClient
  *argv = "*ruleName *ts *u *params"
  if (errorcode(msiExecCmd("ids-event-logger", *argv, "null", "null", "null", *rc)) < 0) {
    writeLine("serverLog", "ERROR: running ids-log-event");
  }
  else {
    msiGetStdoutInExecCmdOut(*rc, *stdout);
    if (*stdout like regex "^ERROR") {
      writeLine("serverLog", "ERROR: running ids-log-event: "++*stdout);
    }
  }
}

# end auditing rules section

# EOF

