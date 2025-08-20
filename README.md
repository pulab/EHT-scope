# EHT-scope
**Engineered heart tissue imaging platform with acquisition and analysis software**

The platform is designed to image engineered heart tissues suspended on flexible posts in a 24 well dish. 

* EHT-scope: instructions and schematics to build the imaging platform and install software.  
* Code: EHT-controller: code for arduino, which runs the imaging platform focus and lights.  
  * EHT-acquire: the BeanShell script that runs in micromanager to automate acquisition.  
  * EHT-motion: ImageJ or Fiji plugin to convert videos into time vs post position.  
  * EHT-analyze: Matlab script to analyze the time vs post position file to calculate physiological parameters.  

