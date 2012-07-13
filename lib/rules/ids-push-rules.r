idsPushRules {
  *ContInxOld = 1;
  msiMakeGenQuery("RESC_LOC", "RESC_LOC != 'localhost'", *GenQInp);
  msiExecGenQuery(*GenQInp, *GenQOut);
  msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);
  while (*ContInxOld > 0) {
    foreach (*GenQOut) {
      msiGetValByKey(*GenQOut, "RESC_LOC", *rloc);
      writeLine("stdout", "Pushing rule base *ruleBase to *rloc");
      remote(*rloc, "null") {
        msiAdmRetrieveRulesFromDBIntoStruct(*ruleBase, "0", *struct);
        msiAdmWriteRulesFromStructIntoFile(*outFileName, *struct);
      }
    }
    *ContInxOld = *ContInxNew;
    if (*ContInxOld > 0) {
      msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
    }
  }
}
INPUT *ruleBase="IDSbase", *outFileName="ids"
OUTPUT ruleExecOut
