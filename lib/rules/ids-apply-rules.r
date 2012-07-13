idsApplyRules {
  msiAdmRetrieveRulesFromDBIntoStruct(*ruleBase, "0", *struct);
  msiAdmWriteRulesFromStructIntoFile(*outFileName, *struct);
}
INPUT *ruleBase="IDSbase", *outFileName="ids"
OUTPUT ruleExecOut
