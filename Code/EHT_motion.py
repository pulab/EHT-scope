# EHT-motion
# 
# requires Multi-Template Match Fiji plugin  https://github.com/multi-template-matching/MultiTemplateMatching-Fiji
# 
#@PrefService prefs
import os
from ij import IJ
from ij.io import FileSaver, DirectoryChooser
from os import path
import glob
from ij.gui import GenericDialog, NonBlockingGenericDialog
from java.awt.event import ActionListener
from fiji.util.gui import GenericDialogPlus
from ij.plugin.frame import RoiManager
from ij.measure import ResultsTable
from datetime import datetime
import re
import csv

rectH = 50	# size of annotation rectangle
rectW = 50

## edit below to change default file locations

result={}	# results is a dictionary of dictionaries
	# top level of results uses each resultFolder name as the key
	# the value is a dictionary, where key=frame and value=TimePoint structure (elapsed time, x1, y1, x2, y2)

def main():
	gui = GenericDialogPlus("Choose Files for EHT-Motion")
	gui.addMessage("EHT-Motion: annotate posts on images and extract position information")
	gui.addMessage("Expected Data Folder structure: DataFolder contains VideoFolder1, VideoFolder2...")
	gui.addMessage("Each VideoFolder contains Folder Pos0 with image sequence, and metadata.txt")
	gui.addMessage("metadata.txt has format of alternating FrameKey-XYZ-0-0 and \"ElapsedTime-ms\": ABC,")
	gui.addMessage("where XYZ is the frame number and ABC is the elapsed time in ms")
	gui.addMessage("")
	gui.addDirectoryField("Post Template Folder", prefs.get("EHTTemplatePath","template(s)"))
	gui.addDirectoryField("EHT Data Folder", prefs.get("EHTImagePath","image(s)"))
	gui.addDirectoryField("Result Folder", prefs.get("EHTResultPath","result folder"))
	gui.addCheckbox("Perform initial post marking",True )
	gui.showDialog()
	if gui.wasCanceled():
		return
	templatePath=gui.getNextString()
	dirPath=gui.getNextString()
	resultPath=gui.getNextString()
	dateTimeObj = datetime.now()
	timestampStr=dateTimeObj.strftime("%d-%b-%Y_(%H-%M-%S)")
	resultFile=os.path.join(resultPath,"Results_"+timestampStr+".txt")
	performPostLabel=gui.getNextBoolean()
	dirPath = os.path.expanduser(dirPath)
	dirPath = os.path.expandvars(dirPath)
	IJ.log(resultFile)
	
	# save for persistence
	prefs.put("EHTTemplatePath",templatePath)
	prefs.put("EHTImagePath",dirPath)
	prefs.put("EHTResultPath",resultPath)

	# make list of first image in each subfolder
	contents=os.listdir(dirPath)			# contents of top folder
	imageList=[]						# list of first image in each subfolder
	for f in contents:					# build list of first image in each subfolder (sorted by creation time)
		folderPath=os.path.join(dirPath,f)
		if os.path.isdir(folderPath):	# subfolders of top folder
			subFolder=os.path.join(folderPath,"Pos0") # expect folder "Pos0" in subfolder
			if os.path.isdir(subFolder):
				os.chdir(subFolder)
				fileList=sorted(glob.glob("*.tif"))
				firstImage=fileList[0]
				firstImage=os.path.join(subFolder,firstImage)
				imageList.append(firstImage)
			else:
				IJ.log("no Pos0 -- skipping "+subFolder)

	# loop through list of first images and put initial matches on using template match
	# prompt user to adjust to center on pillars
	if performPostLabel:
		count=1
		guiX=50						# default start location of dialog box
		guiY=50
		for f in imageList:
			redo=0
			gui = NonBlockingGenericDialog("EHT-Motion")
			msg="Measure movement of EHT posts for all videos in:\n"+dirPath
			gui.addMessage(msg)
			gui.addMessage("Step One: Annotate posts for first image in each video stack.")
			gui.addMessage("For each displayed image, move ROI so that it is centered on each post.")
			gui.addMessage("  Select region by double clicking it.")
			gui.addMessage("  Move region by pointing inside it (arrow cursor) and dragging")
			gui.addMessage("When done with each image, press OK to save and move to next image.")
			gui.addMessage("To abort, press cancel.")
			gui.addMessage("Current video: "+str(count)+" of "+str(len(imageList)))
			gui.setLocation(guiX, guiY)
			# ok and cancel are shown by default
			imageName=os.path.basename(f)
			imp=IJ.openImage(f)	#show the image
			imp.show()
			IJ.run("Select None") # clear any selection rectangles
			rm = RoiManager.getInstance();
			if rm is None:
		 	   rm = RoiManager()
			rm.reset()	# clear ROIs
			overlay = imp.getOverlay()
			if (overlay):
				overlay.clear() 		# clear overlay
			IJ.run("Template Matching Folder", "template=["+templatePath+"] image=["+f+"] rectangular_search_roi=searchRoi rotate=180 matching_method=[Normalised 0-mean cross-correlation] number_of_objects=2 score_threshold=0.4 maximal_overlap=0.4 add_roi")
			# IJ.run("Template Matching Image", "template=PostTemplate.tif image="+imageName+" rotate=180 matching_method=[Normalised 0-mean cross-correlation] number_of_objects=2 score_threshold=0.4 maximal_overlap=0.4 add_roi");
			IJ.run("From ROI Manager", "") # mark overlay from ROI manager
			rm.close()
			gui.showDialog()			# prompt user to adjust ROIs
			bounds=gui.getBounds()		# remember position of the dialog box
			guiX=bounds.x
			guiY=bounds.y
			if gui.wasOKed():
				IJ.save(imp, f) 		# save image with new overlay
				imp.close()
			else:						# cancel
				return
			count=count+1

	# parse metadata.txt in each Pos0 file to extract time of each frame
	for f in contents:
		folderPath=os.path.join(dirPath,f)
		folderPath=os.path.join(folderPath,"Pos0")
		meta=os.path.join(folderPath,"metadata.txt")
		if os.path.isfile(meta):
			timeStamp=processMetadata(meta)
			IJ.log("meta on : "+f)
			result[f]=timeStamp
		else:
			IJ.log("Error--missing metadata in "+folderPath)

	# process each video folder using template matching of the two regions identified in the first image as templates.
	count=0
	for f in contents:
		folderPath=os.path.join(dirPath,f)
		if os.path.isdir(folderPath):	# subfolders of top folder
			IJ.log(f)
			count=count+1
			IJ.showProgress(count,len(contents)+1)
			subFolder=os.path.join(folderPath,"Pos0") # expect folder "Pos0" in subfolder
			if os.path.isdir(subFolder):
				result[f]=trackMotion(subFolder,result[f])	# fill in the position fields of the result dictionary for video f
			else:
				IJ.log("no Pos0 -- skipping "+subFolder)
	IJ.showProgress(1)
	# write out results to resultFile
	f=open(resultFile, "w")
	cw=csv.writer(f,delimiter="\t")
	for sample in result:
		for frame,timeStamp in result[sample].items():
			cw.writerow([sample, frame, timeStamp.time, timeStamp.x1, timeStamp.y1, timeStamp.x2, timeStamp.y2])
	f.close()

	IJ.showMessage("EHT-annotate complated successfully. Result file: "+resultFile+"\n\nPost ROIs are stored in each folder in Posts.roi")
	return

# define a class for holding information about each time point
class TimePoint:
	def __init__(self, time, x1, y1, x2, y2):
		self.time=time
		self.x1=x1
		self.y1=y1
		self.x2=x2
		self.y2=y2


# process a metadata text file to extract timing of each frame
# meta is file path to metadata.txt

def processMetadata(meta):		
	timeStamp={}	# dictionary of frame:time
	f=open(meta,"r")
	pattern="FrameKey-(\d+)-0-0"
	time=0
	for l in f:
		match=re.search(pattern,l)
		if match:
			if pattern=="FrameKey-(\d+)-0-0":
				frame=int(match.group(1))
				pattern="\"ElapsedTime-ms\": (\d+),"
			elif pattern=="\"ElapsedTime-ms\": (\d+),":
				timeStamp[frame]=TimePoint(time,0,0,0,0)
				time=int(match.group(1))
				pattern="FrameKey-(\d+)-0-0"
	f.close()
	return(timeStamp)

# track the motion of the set of images inside folder Fld, where the first image has 2 ROIs marked
#	extract the ROIs as image files, save inside templates folder within folder Fld
#	from each frame, extract (x1,y1) and (x2,y2) for the 2 ROIs and save them to timeStamp dictionary
def trackMotion(Fld,timeStamp):
	os.chdir(Fld)
	fileList=sorted(glob.glob("*.tif"))
	firstImage=fileList[0]
	imp=IJ.openImage(os.path.join(Fld,firstImage))	#show the image
	imp.show()
	IJ.run("To ROI Manager", "")
	rm = RoiManager.getInstance();
	if rm is None:
	    rm = RoiManager()
	if (rm.getCount() < 2):	# expect at least 2 ROIs
		IJ.log("error--less than 2 ROI: "+firstImage)
	else:
		templatePath=os.path.join(Fld,"templates")
		if not os.path.isdir(templatePath): # create the directory if it does not already exist
			os.mkdir(templatePath)
		roi=rm.getRoi(0)
		imp.setRoi(roi)
		IJ.run(imp,"Copy","")
		IJ.run("Internal Clipboard","")
		IJ.saveAs("Tiff",os.path.join(templatePath,"template0"))
		roi=rm.getRoi(1)
		imp.setRoi(roi)
		IJ.run(imp,"Copy","")
		IJ.run("Internal Clipboard","")
		IJ.saveAs("Tiff",os.path.join(templatePath,"template1"))
		imp.close()
	rm.reset()	# clear ROI manager
	rt = ResultsTable.getResultsTable()
	rt.reset()
	
	#IJ.run("Template Matching Folder", "template=["+templatePath+"] image=["+Fld+"] rectangular_search_roi=searchRoi rotate=180 matching_method=[Normalised 0-mean cross-correlation] number_of_objects=2 score_threshold=0.4 maximal_overlap=0.4 add_roi show_result")
	IJ.run("Image Sequence...","open=["+Fld+"] sort")
	IJ.run("Template Matching Image", "template=template1.tif image=Pos0 rotate=[] matching_method=[Normalised 0-mean cross-correlation] number_of_objects=1 score_threshold=0.4 maximal_overlap=0.4 add_roi show_result")
	IJ.run("Template Matching Image", "template=template0.tif image=Pos0 rotate=[] matching_method=[Normalised 0-mean cross-correlation] number_of_objects=1 score_threshold=0.4 maximal_overlap=0.4 add_roi show_result")

	# read results table
	# store x,y position of posts vs time
	rt.sort("Image")
	s=rt.size()
	for row in range(0,s):
		name=rt.getStringValue("Image",row)
		IJ.log(rt.getRowAsString(row))
		frame=rt.getValue("Slice",row)-1
		IJ.log(str(frame)+" "+str(timeStamp[frame].x1)+" "+str(timeStamp[frame].x2))
		if timeStamp[frame].x1==0:
			timeStamp[frame].x1=rt.getValue("Xcenter",row)
			timeStamp[frame].y1=rt.getValue("Ycenter",row)
		elif timeStamp[frame].x2==0:
			timeStamp[frame].x2=rt.getValue("Xcenter",row)
			timeStamp[frame].y2=rt.getValue("Ycenter",row)
		else:
			IJ.log("error: timeStamp[frame] x1 and x2 not zero: "+str(frame))
	rt.reset()	# clear result table
	# save ROI and clear
	rm.runCommand("Save", os.path.join(Fld, "Posts.roi"))
	rm.reset()
	closeWindow("template0.tif")
	closeWindow("template1.tif")
	closeWindow("Pos0")
	return(timeStamp)

def closeWindow(name):
	IJ.selectWindow(name)
	imp=IJ.getImage()
	imp.close()


main()
IJ.log("done")
