#!/usr/bin/env python3

__author__ = 'JSmith' and 'SZhang'

"""assumes usual performance test hierarchy of folders.
processes the perf logs of the following tests to get the data required
for the baseline and extra performance tests reporting spreadsheets:
DPT1, DPT2, BBT3, NTT4, MDT5, HD4_FDT6, FR_HHT7, UK_HHT8, FR_LWS9 and CHP_FDT10
Several more tests have been added since.
"""

"""Change History:
1. Updated the comments above to include new extra tests added.
2. Added code to collect data from MDT4 (MonoToDuoTest) log files
3. Added code to collect data from UK_HHT8 (UK-HipTpHipPlusTest) log files
5. Modified HHT7 to FR_HHT7
4. Added code to collect data from FR_LWS9 (FR_LayoutWithSectionsTest) log files
5. Added code to collect data from CHP_FDT10 (FR_ChapeauFramDesignTest) log files
6. Modified FDT4 to HD4_FDT4
7. Added several new tests
"""

import sys
import os.path

debug = False

def getDataFromFile(searchSpec):
    """traverses the file stream to get perf data from the tagToFind elements.
    returns as a list"""
    (filename, tagToFind) = searchSpec
    results = []
    file = None
    try:
        file = open(filename,mode="r")

        line = file.readline()
        while line:
            line = line.strip()
            if line.find(tagToFind) >= 0:
                # remove the seconds unit suffix
                line = line.replace("s "," ")
                results.append(line)

            line = file.readline()
    except IOError:
        pass
    finally:
        if file:
            file.close()

    return results

def printResults(filename, data, outfile=sys.stdout):
    print ("[%s]" % filename, file=outfile)

    for line in data:
        print (line, file=outfile)

class TimingData:
    def __init__(self):
        self.startToLogin = 0.0
        self.loginToMainForm = 0.0
        self.shutdown = 0.0
        self.selectMetalwork = None
        self.fileSize = None
        self.pamirShutdown = None
        self.sapphireReport = None
        self.sapphireShutdown = None
        self.runTimes = []

def secondsFromStopwatchLine(line):
    (a, b, milliStr) = line.rpartition(",")
    return float(milliStr.strip())/1000.0

def secondsFromPerfLine(line):
    parts = line.split("\t")
    return float(parts[4])/1000.0


def searchSecondsFromPerfLine(lines, searchString):
    for line in lines:
        if line.find(searchString) >= 0 :
            return secondsFromPerfLine(line)

    return 0.0

searchSpecs = [
    ("./DPT1/testrun.log","TC.Stopwatch"),
    ("./DPT1/data/pamir-perf.log","UI.BuildDesign"),
    ("./DPT2/testrun.log","TC.Stopwatch"),
    ("./DPT2/data/pamir-perf.log","UI.BuildDesign"),
    ("./BBT3/testrun.log","TC.Stopwatch"),
    ("./BBT3/data/pamir-perf.log","UI.Build")]

def getTotalTimeFromPerfLogRow(dataRow):
     (a,sep, timePlusSplits) = dataRow.rpartition(":")
     (timeStr,sep,b) = timePlusSplits.partition("(")
     return float(timeStr)

def collectStartupDataForTest(timingData,tcLogSpec):
    '''Collect data from the TestComplete Test logs for
    the startup and shutdown.'''

    data = getDataFromFile(tcLogSpec)
    if debug: printResults(tcLogSpec[0],data,outputfile)
    if (len(data) >= 2):
        timingData.startToLogin = secondsFromStopwatchLine(data[0])
        timingData.loginToMainForm = secondsFromStopwatchLine(data[1])
    if (len(data) == 3):
        timingData.shutdown = secondsFromStopwatchLine(data[2])

    return

def MegaByteFromFileSizeLine(line):
    (a, b, killoStr) = line.rpartition(",")
    return float(killoStr.strip())/1024.0

def collectFileSizeForTest(timingData,tcLogSpec):
    '''Collect data from the TestComplete Test logs for
    the Pamir file size'''

    data = getDataFromFile(tcLogSpec)
    if debug: printResults(tcLogSpec[0],data,outputfile)
    if (len(data) == 1):
        timingData.fileSize = MegaByteFromFileSizeLine(data[0])

    return

def collectStartupAndSelectMetalworkDataForTest(timingData,tcLogSpec):
    '''Collect data from the TestComplete Test logs for
    the startup and shutdown plus an additional operation of select Metalwork'''

    data = getDataFromFile(tcLogSpec)
    if debug: printResults(tcLogSpec[0],data,outputfile)
    if (len(data) >= 2):
        timingData.startToLogin = secondsFromStopwatchLine(data[0])
        timingData.loginToMainForm = secondsFromStopwatchLine(data[1])
    if (len(data) >= 3):
        timingData.selectMetalwork = secondsFromStopwatchLine(data[2])
    if (len(data) == 4):
        timingData.shutdown = secondsFromStopwatchLine(data[3])
    return

def collect2020StartupDataForTest(timingData,tcLogSpec):
    '''Collect data from the TestComplete Test logs for
    the startup and shutdown.'''

    data = getDataFromFile(tcLogSpec)
    if debug: printResults(tcLogSpec[0],data,outputfile)
    if (len(data) >= 2):
        timingData.startToLogin = secondsFromStopwatchLine(data[0])
        timingData.loginToMainForm = secondsFromStopwatchLine(data[1])
    if (len(data) >= 3):
        timingData.pamirShutdown = secondsFromStopwatchLine(data[2])
    if (len(data) == 4):
        timingData.shutdown = secondsFromStopwatchLine(data[3])

    return

def collectSapphireStartupAndReportDataForTest(timingData,tcLogSpec):
    '''Collect data from the TestComplete Test logs for
    the startup and shutdown.'''

    data = getDataFromFile(tcLogSpec)
    if debug: printResults(tcLogSpec[0],data,outputfile)
    if (len(data) >= 2):
        timingData.startToLogin = secondsFromStopwatchLine(data[0])
        timingData.loginToMainForm = secondsFromStopwatchLine(data[1])
    if (len(data) >= 3):
        timingData.sapphireReport = secondsFromStopwatchLine(data[2])
    if (len(data) >= 4):
        timingData.sapphireShutdown = secondsFromStopwatchLine(data[3])
    if (len(data) >= 5):
        timingData.shutdown = secondsFromStopwatchLine(data[4])

    return

def collectDataForOneTest(tcLogSpec, perfLogSpec):
    '''Collect data from the TestComplete and Pamir Performance Test logs for
    one group of test runs.'''

    timingData = TimingData()

    collectStartupDataForTest(timingData, tcLogSpec)

    data = getDataFromFile(perfLogSpec)
    if debug: printResults(perfLogSpec[0],data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    return timingData

def collectDataFromNavigationTrimTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect benchmark results
    data = getDataFromFile((tcLogFile,"BenchmarkResults"));
    if debug: printResults(tcLogFile,data,outputfile)
    timingData.runTimes.append(secondsFromStopwatchLine(data[4]))  # Paint.TotalTime
    timingData.runTimes.append(secondsFromStopwatchLine(data[6]))  # Refresh.AverageTime


    # timings for other operations
    data = getDataFromFile((perfLogFile,"Action.Execute\tComplete"))
    timingData.runTimes.append(searchSecondsFromPerfLine(data, "Toggle automatic framing zone"))
    timingData.runTimes.append(searchSecondsFromPerfLine(data, "Trim/Extend"))

    if debug: printResults(perfLogFile,data,outputfile)
    return timingData

def collectDataFromMonoToDuoTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect benchmark results
    data = getDataFromFile((tcLogFile,"BenchmarkResults"));
    if debug: printResults(tcLogFile,data,outputfile)
    timingData.runTimes.append(secondsFromStopwatchLine(data[4]))  # Paint.TotalTime
    timingData.runTimes.append(secondsFromStopwatchLine(data[6]))  # Refresh.AverageTime

    # timings for other operations
    data = getDataFromFile((perfLogFile,"Action.Execute\tComplete"))
    timingData.runTimes.append(searchSecondsFromPerfLine(data, "Delete"))

    if debug: printResults(perfLogFile,data,outputfile)
    return timingData

def collectDataFromFrameDesignTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect benchmark results
    data = getDataFromFile((tcLogFile,"BenchmarkResults"));
    if debug: printResults(tcLogFile,data,outputfile)
    timingData.runTimes.append(secondsFromStopwatchLine(data[11]))  # Design.AverageTime

    return timingData

def collectDataFromHipToHipPlusTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect the total time of building all frames from "Pamir-perf.log"
    data = getDataFromFile((perfLogFile,"BuildFrame"));
    if debug: printResults(perfLogFile,data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    # collect the total time of designing all frames from "Pamir-perf.log"
    data = getDataFromFile((perfLogFile,"BuildDesign"));
    if debug: printResults(perfLogFile,data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    # collect benchmark results
    data = getDataFromFile((tcLogFile,"BenchmarkResults"));
    if debug: printResults(tcLogFile,data,outputfile)
    timingData.runTimes.append(secondsFromStopwatchLine(data[4]))  # Paint.TotalTime
    timingData.runTimes.append(secondsFromStopwatchLine(data[6]))  # Refresh.AverageTime

    # collect file size of the saved Pamir job
    collectFileSizeForTest(timingData, (tcLogFile,"Pamir job:"))

    return timingData

def collectDataFromBenchmarkTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect benchmark results
    data = getDataFromFile((tcLogFile,"BenchmarkResults"));
    if debug: printResults(tcLogFile,data,outputfile)
    timingData.runTimes.append(secondsFromStopwatchLine(data[4]))  # Paint.TotalTime
    timingData.runTimes.append(secondsFromStopwatchLine(data[6]))  # Refresh.AverageTime

    return timingData

def collectDataFromOutputPDFTests(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect the total time of rendering all output PDF pages from "Pamir-perf.log"
    data = getDataFromFile((perfLogFile,"OutputPrintManagerOpearation"))

    if debug: printResults(perfLogFile,data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(secondsFromPerfLine(dataRow))

    # collect file size of the saved Pamir job
    collectFileSizeForTest(timingData, (tcLogFile,"Pamir job:"))

    return timingData

def collectDataFromUK_DisableHangerHipToHipTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect the total time of building all frames from "Pamir-perf.log"
    data = getDataFromFile((perfLogFile,"BuildFrame"));
    if debug: printResults(perfLogFile,data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    # collect the total time of designing all frames from "Pamir-perf.log"
    data = getDataFromFile((perfLogFile,"BuildDesign"));
    if debug: printResults(perfLogFile,data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    return timingData

def collectDataFromUK_EnableHangerHipToHipTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collectStartupAndSelectMetalworkDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect the total time of building all frames from "Pamir-perf.log"
    data = getDataFromFile((perfLogFile,"BuildFrame"));
    if debug: printResults(perfLogFile,data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    # collect the total time of designing all frames from "Pamir-perf.log"
    data = getDataFromFile((perfLogFile,"BuildDesign"));
    if debug: printResults(perfLogFile,data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    # collect file size of the saved Pamir job
    collectFileSizeForTest(timingData, (tcLogFile,"Pamir job:"))

    return timingData

def collectDataFromUK_ThousandDrawingObjectsTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"

    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect benchmark results
    data = getDataFromFile((tcLogFile,"BenchmarkResults"));
    if debug: printResults(tcLogFile,data,outputfile)

    # the first run of benchmark data
    timingData.runTimes.append(secondsFromStopwatchLine(data[4]))  # Paint.TotalTime
    timingData.runTimes.append(secondsFromStopwatchLine(data[6]))  # Refresh.AverageTime

    # the second run of benchmark data
    timingData.runTimes.append(secondsFromStopwatchLine(data[14]))  # Paint.TotalTime
    timingData.runTimes.append(secondsFromStopwatchLine(data[16]))  # Refresh.AverageTime

    return timingData

def collectDataFromFR_FileSizeTest(folderName):
    if not os.path.exists("./" + folderName):
       return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect the total time of designing all frames from "Pamir-perf.log"
    data = getDataFromFile((perfLogFile,"BuildDesign"));
    if debug: printResults(perfLogFile,data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    # collect file size of the saved Pamir job
    collectFileSizeForTest(timingData, (tcLogFile,"Pamir job:"))

    return timingData

def collectDataFromUK_OpenAndSaveTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect the time for opening project
    data = getDataFromFile((perfLogFile,"OpenProject\tComplete"))
    if debug: printResults(perfLogFile,data,outputfile)
    timingData.runTimes.append(searchSecondsFromPerfLine(data, "Complete"))

    # collect the time for saving project
    data = getDataFromFile((perfLogFile,"UI.SaveProjectOperation\tComplete"))
    if debug: printResults(perfLogFile,data,outputfile)
    timingData.runTimes.append(searchSecondsFromPerfLine(data, "Save"))

    return timingData

def collectDataFromFullSynchronisationTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collect2020StartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # timings for saving project
    data = getDataFromFile((perfLogFile,"Saving\tComplete"))
    if debug: printResults(perfLogFile,data,outputfile)
    timingData.runTimes.append(searchSecondsFromPerfLine(data, "Complete"))

    # timings for MBA Synchronise Operation
    data = getDataFromFile((perfLogFile,"UI.MBASynchroniseOperation\tComplete"))
    if debug: printResults(perfLogFile,data,outputfile)
    timingData.runTimes.append(searchSecondsFromPerfLine(data, "Complete"))

    return timingData

def collectDataFromSapphireReportTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    timingData = TimingData()

    collectSapphireStartupAndReportDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    return timingData

def collectDataFromMultipleDesignCasesTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect the total time of designing all frames from "Pamir-perf.log"
    data = getDataFromFile((perfLogFile,"BuildDesign"));
    if debug: printResults(perfLogFile,data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    return timingData
def collectDataFromFrameDesignWithScabTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect the total time of designing all frames from "Pamir-perf.log"
    data = getDataFromFile((perfLogFile,"BuildDesign"));
    if debug: printResults(perfLogFile,data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    return timingData

def outputTimingArrayToFile(timingArray):
    if debug: print ("\n===========================\n", file=outputfile)

    for td in timingArray:
        if (td == None):
            continue

        print ("%.3f\n%.3f" % (td.startToLogin, td.loginToMainForm), file=outputfile)

        if (td.selectMetalwork != None):
            print ("%.3f" % (td.selectMetalwork), file=outputfile)  ## print the time of selected Metalwork

        if (len(td.runTimes) != 0):
            for runTime in td.runTimes:
               print("%.3f" % (runTime), file = outputfile)

        if (td.sapphireReport != None):
            print ("%.3f" % (td.sapphireReport), file=outputfile)  ## print the time of generating Sapphire Report

        if (td.pamirShutdown != None):
            print ("%.3f" % (td.pamirShutdown), file=outputfile)  ## print the time of Pamir Shutdown

        if (td.sapphireShutdown != None):
            print ("%.3f" % (td.sapphireShutdown), file=outputfile)  ## print the time of Sapphire Report Viewer Shutdown

        print ("%.3f" % (td.shutdown), file=outputfile)

        if (td.fileSize != None):
            print ("%.3f" % (td.fileSize), file=outputfile)  ## print file size of the saved Pamir job

        print ("", file=outputfile)  ## new line to create a gap for next result

with open("baseline-results.txt",mode="w") as outputfile:
    timingArray = []
    for index in [0,1,2]:
        tcLogSpec = searchSpecs[index*2]
        perfLogSpec = searchSpecs[index*2+1]

        timingArray.append(collectDataForOneTest(tcLogSpec,perfLogSpec))

    outputTimingArrayToFile(timingArray)

with open("extra-results.txt",mode="w") as outputfile:
    timingArray = []

    # collect data from extra tests
    timingArray.append(collectDataFromNavigationTrimTest("NTT4"))
    timingArray.append(collectDataFromMonoToDuoTest("MDT5"))
    timingArray.append(collectDataFromFrameDesignTest("HD4_FDT6"))
    timingArray.append(collectDataFromFrameDesignTest("CHP_FDT10"))
    timingArray.append(collectDataFromHipToHipPlusTest("FR-HHT7"))
    timingArray.append(collectDataFromHipToHipPlusTest("UK-HHT8"))
    timingArray.append(collectDataFromBenchmarkTest("FR_LWS9"))
    timingArray.append(collectDataFromUK_ThousandDrawingObjectsTest("UK_TDOT17"))
    timingArray.append(collectDataFromBenchmarkTest("SW_FBMT11"))
    timingArray.append(collectDataFromBenchmarkTest("UK_HT1_FBMT12"))
    timingArray.append(collectDataFromOutputPDFTests("ISOLA_PDF13"))
    timingArray.append(collectDataFromOutputPDFTests("UK_LayoutPDF14"))
    timingArray.append(collectDataFromUK_DisableHangerHipToHipTest("UK-DISH15"))
    timingArray.append(collectDataFromUK_EnableHangerHipToHipTest("UK-ENAH16"))
    timingArray.append(collectDataFromFR_FileSizeTest("FR-MST18"))
    timingArray.append(collectDataFromFR_FileSizeTest("FR-SST19"))
    timingArray.append(collectDataFromFR_FileSizeTest("FR-DST20"))
    timingArray.append(collectDataFromUK_OpenAndSaveTest("UK-OST21"))
    timingArray.append(collectDataFromMultipleDesignCasesTest("T22-FR-MDC"))
    timingArray.append(collectDataFromFrameDesignWithScabTest("T23-FR-SCAB"))
    timingArray.append(collectDataFromFullSynchronisationTest("UK-SYNC"))
    timingArray.append(collectDataFromSapphireReportTest("UK-SAREP"))
    outputTimingArrayToFile(timingArray)
