# Exploiting Variable Implications in Presolve for Mixed Integer Programming
## Authors: Wei-Kun Chen, Chang-Long Li, Zhao-Wei Wang, Yu-Hong Dai, Zi-Shuo Li, Meng Lu


## Project Overview
This project provides a version of the HiGHS solver (https://github.com/ERGO-Code/HiGHS) containing an implementation of the two presolve techniques proposed in the paper [Exploiting Variable Implications in Presolve for Mixed Integer Programming](https://arxiv.org/abs/2607.04313) by Wei-Kun Chen, Chang-Long Li, Zhao-Wei Wang, Yu-Hong Dai, Zi-Shuo Li, and Meng Lu.


## Repository Organization
* ```highs-1.12.0/```: the HiGHS solver with the two proposed presolve techniques.
    We modified the code based on the release [HiGHS 1.12.0](https://github.com/ERGO-Code/HiGHS/releases/tag/v1.12.0).
    The new presolve techniques are mainly implemented in ```highs-1.12.0/highs/presolve/HPresolve.cpp``` and ```highs-1.12.0/highs/mip/HighsCliqueTable.{h,cpp}```.
* ```paper-settings/```: settings files containing parameters to enable the presolve techniques.


## Installation
* Simply install HiGHS as usual:
```shell
cd highs-1.12.0/
cmake -S . -B build
cmake --build build
```
* More details about the installation of HiGHS can be found at the [official installation page](https://github.com/ERGO-Code/HiGHS#installation).


## Testset
 * The MIPLIB 2017 benchmark is used as the testset.
 * We use 5 random seeds for each of the 240 problems, and each problem and seed combination is treated as an individual observation, referred to as an "instance".

## Running experiments
* To solve an instance with different settings, use
```shell
# run Default
./build/bin/highs /path/to/your/instance --options_file ../paper-settings/Default.setting
# run LCPVI
./build/bin/highs /path/to/your/instance --options_file ../paper-settings/LCPVI.setting
# run LCPVI'
./build/bin/highs /path/to/your/instance --options_file ../paper-settings/LCPVI-prime.setting
# run AVIC
./build/bin/highs /path/to/your/instance --options_file ../paper-settings/AVIC.setting
# run All
./build/bin/highs /path/to/your/instance --options_file ../paper-settings/All.setting
# run Achterberg2013a
./build/bin/highs /path/to/your/instance --options_file ../paper-settings/Achterberg2013a.setting
```
