#!/bin/bash
# Sample batchscript to run a simple MATLAB job on HPC
#SBATCH --partition=PLACEHOLDER             # queue to be used
#SBATCH --time=00:15:00             # Running time (in hours-minutes-seconds)
#SBATCH --output=output_%j.txt          # Name of the output file
#SBATCH --nodes=1               # Number of nodes
#SBATCH --ntasks=1              # Number of devices on one node

cd $1
awk '{print>$1}' Results.txt

for file in $(find . -type f -iname '*-*'); do mv $file ${file//-/}; done
module load matlab
for f in *EHT*; do matlab -nodisplay -nosplash -nodesktop -r "addpath /Analyze_EHT_folder; analyze_EHT('$f',$2,$3); exit;" ; done

awk 'NR==1 {header=$_} FNR==1 && NR!=1 { $_ ~ $header getline; } {print}' *_result.txt > EHT_results
