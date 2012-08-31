idsApplyRules {
  if (*rloc == "localhost") {
    msiAdmRetrieveRulesFromDBIntoStruct(*ruleBase, "0", *struct);
    msiAdmWriteRulesFromStructIntoFile(*outFileName, *struct);
  }
  else {
    remote(*rloc, "null") {
      msiAdmRetrieveRulesFromDBIntoStruct(*ruleBase, "0", *struct);
      msiAdmWriteRulesFromStructIntoFile(*outFileName, *struct);
    }
  }
}
INPUT *ruleBase="IDSbase", *outFileName="ids", *rloc="localhost"
OUTPUT ruleExecOut
