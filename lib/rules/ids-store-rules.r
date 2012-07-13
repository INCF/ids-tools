idsStoreRules {
  msiAdmReadRulesFromFileIntoStruct(*inFileName, *struct);
  msiAdmInsertRulesFromStructIntoDB(*ruleBase, *struct);
}
INPUT *ruleBase="IDSbase", *inFileName="ids-src"
OUTPUT ruleExecOut
