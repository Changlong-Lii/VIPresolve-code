#include "interfaces/highs_c_api.h"
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <math.h>
#include <string.h>

// gcc call_highs_from_c_minimal.c -o highstest -L ../build/lib64/ -I ../highs/ -lhighs

void minimal_api_mps() {
  // Illustrate the minimal interface for reading an mps file. Assumes
  // that the model file is check/instances/avgas.mps
  
  const char* filename = "/share/home/cmipinstances/collection/comp07-2idx.mps.gz";
  // Create a Highs instance
  void* highs = Highs_create();
  int run_status;
  run_status = Highs_readModel(highs, filename);
  assert(run_status == kHighsStatusOk);
  run_status = Highs_setIntOptionValue(highs, "random_seed", 1);
  run_status = Highs_setBoolOptionValue(highs, "processing_clique", 1);
//   run_status = Highs_setBoolOptionValue(highs, "variable_bound_tightening_obj", 1);
//   run_status = Highs_setBoolOptionValue(highs, "variable_bound_tightening_two", 1);
  run_status = Highs_presolve(highs);
  int model_status = Highs_getModelStatus(highs);

  printf("\nRun status = %d; Model status = %d\n", run_status, model_status);
  Highs_writePresolvedModel(highs, "Presolved-comp07-2idx-1.mps");

  // double objective_function_value;
  // Highs_getDoubleInfoValue(highs, "objective_function_value", &objective_function_value);
  // printf("Optimal objective value = %g\n", objective_function_value);
  // assert(fabs(objective_function_value+7.75)<1e-5);
}


int main(int argc, char** argv) {
  minimal_api_mps();
  return 0;
}