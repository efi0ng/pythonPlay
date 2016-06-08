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
.
.
10. Added JSon output for the basic tests
"""

import sys
import os.path
import json

debug = False

# ---------------------------------------------------------
# TimingData and timing array output functions
# ---------------------------------------------------------


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
        # for JSon support
        self.testLabel = None
        self.operationLabels = []

    def to_json_dict(self):
        testJsonDict = {}
        testJsonDict['ToLogin'] = secondsToMilliseconds(self.startToLogin)
        testJsonDict['ToMainForm'] = secondsToMilliseconds(self.loginToMainForm)
        testJsonDict['Shutdown'] = secondsToMilliseconds(self.shutdown)

        if (self.selectMetalwork != None):
            testJsonDict['SelectMetalwork'] = secondsToMilliseconds(self.selectMetalwork)

        if (self.sapphireReport != None):
            testJsonDict['SapphireReport'] = secondsToMilliseconds(self.sapphireReport)

        if (self.pamirShutdown != None):
            testJsonDict['PamirShutdown'] = secondsToMilliseconds(self.pamirShutdown)

        if (self.sapphireShutdown != None):
            testJsonDict['SapphireShutdown'] = secondsToMilliseconds(self.sapphireShutdown)

        if (self.fileSize != None):
            testJsonDict['FileSize'] = self.fileSize

        if (len(self.runTimes) != 0):
            key = 0
            for runTime in self.runTimes:
                testJsonDict[self.operationLabels[key]] = runTime
                key = key+1

        return testJsonDict

    def to_file(self, outfile):
        print("%.3f\n%.3f" % (self.startToLogin, self.loginToMainForm), file=outfile)

        if (self.selectMetalwork != None):
            print ("%.3f" % (self.selectMetalwork), file=outfile)  ## print the time of selected Metalwork

        if (len(self.runTimes) != 0):
            for runTime in self.runTimes:
                print("%.3f" % (runTime), file=outfile)

        if (self.sapphireReport != None):
            print("%.3f" % (self.sapphireReport), file=outfile)  ## print the time of generating Sapphire Report

        if (self.pamirShutdown != None):
            print("%.3f" % (self.pamirShutdown), file=outfile)  ## print the time of Pamir Shutdown

        if (self.sapphireShutdown != None):
            print("%.3f" % (self.sapphireShutdown), file=outfile)  ## print the time of Sapphire Report Viewer Shutdown

        print("%.3f" % (self.shutdown), file=outfile)

        if (self.fileSize != None):
            print("%.3f" % (self.fileSize), file=outfile)  ## print file size of the saved Pamir job

        print("", file=outfile)  ## new line to create a gap for next result


def outputTimingArrayToJSonFile(timing_array, fileName):
    rootJsonDict = {}

    for td in timing_array:

        if (td == None):
            continue

        testJsonDict = td.to_json_dict()

        rootJsonDict[td.testLabel] = testJsonDict

    with open(fileName, mode="w") as jsonFile:
        json.dump(rootJsonDict, jsonFile, indent=3)


def outputTimingArrayToFile(timing_array, outfile):
    if debug: print ("\n===========================\n", file=outfile)

    for td in timing_array:
        if (td == None):
            continue

        td.to_file(outfile)


# ---------------------------------------------------------
# Data collection - general
# ---------------------------------------------------------

def debugPrintResults(filename, data, outfile=sys.stdout):
    print ("[%s]" % filename, file=outfile)

    for line in data:
        print (line, file=outfile)


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


def secondsFromStopwatchLine(line):
    (a, b, milliStr) = line.rpartition(",")
    return float(milliStr.strip())/1000.0


def secondsFromPerfLine(line):
    parts = line.split("\t")
    return float(parts[4])/1000.0


def secondsToMilliseconds(secs):
    return int(secs*1000)


def searchSecondsFromPerfLine(lines, searchString):
    for line in lines:
        if line.find(searchString) >= 0 :
            return secondsFromPerfLine(line)

    return 0.0


def getTotalTimeFromPerfLogRow(dataRow):
     (a,sep, timePlusSplits) = dataRow.rpartition(":")
     (timeStr,sep,b) = timePlusSplits.partition("(")
     return float(timeStr)


def collectStartupDataForTest(timingData,tcLogSpec):
    '''Collect data from the TestComplete Test logs for
    the startup and shutdown.'''

    data = getDataFromFile(tcLogSpec)
    if debug: debugPrintResults(tcLogSpec[0],data,outputfile)
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
    if debug: debugPrintResults(tcLogSpec[0],data,outputfile)
    if (len(data) == 1):
        timingData.fileSize = MegaByteFromFileSizeLine(data[0])

    return


def collectDataForOneTest(tcLogSpec, perfLogSpec):
    '''Collect data from the TestComplete and Pamir Performance Test logs for
    one group of test runs.'''

    timingData = TimingData()

    collectStartupDataForTest(timingData, tcLogSpec)

    data = getDataFromFile(perfLogSpec)
    if debug: debugPrintResults(perfLogSpec[0],data,outputfile)
    for dataRow in data:
        timingData.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    return timingData

# ---------------------------------------------------------
# Basic test specifications and collection
# ---------------------------------------------------------

KEY_TEST_LABEL = "label"
KEY_OPLABEL = "operationLabel"
KEY_TCLOGSPEC = "tcLogSpec"
KEY_PERFLOGSPEC = "perfLogSpec"

dpt1dict = {
    KEY_TEST_LABEL: "DPT1",
    KEY_OPLABEL: ["Design1", "Check1", "Design2", "Check2", "Design3", "Check3", "Design4", "Check4", "Design5", "Check5"],
    KEY_TCLOGSPEC: ("./DPT1/testrun.log","TC.Stopwatch"),
    KEY_PERFLOGSPEC: ("./DPT1/data/pamir-perf.log","UI.BuildDesign")}

dpt2dict = {
    KEY_TEST_LABEL: "DPT2",
    KEY_OPLABEL: ["Design1", "Check1", "Design2", "Check2", "Design3", "Check3", "Design4", "Check4", "Design5", "Check5"],
    KEY_TCLOGSPEC: ("./DPT2/testrun.log","TC.Stopwatch"),
    KEY_PERFLOGSPEC: ("./DPT2/data/pamir-perf.log","UI.BuildDesign")}

bbt3dict = {
    KEY_TEST_LABEL: "BBT3",
    KEY_OPLABEL: ["Build1", "Build2", "Build3", "Build4", "Build5", "Build6", "Build7", "Build8", "Build9", "Build10" ],
    KEY_TCLOGSPEC: ("./BBT3/testrun.log","TC.Stopwatch"),
    KEY_PERFLOGSPEC: ("./BBT3/data/pamir-perf.log","UI.Build")}


class TestSpec:
    def __init__(self):
        self.tcLogSpec = None
        self.perfLogSpec = None
        self.testLabel = ""
        self.operationLabels = []


def getSpecFromDict(specDict):
  result = TestSpec()
  result.tcLogSpec = specDict[KEY_TCLOGSPEC]
  result.perfLogSpec = specDict[KEY_PERFLOGSPEC]
  result.testLabel = specDict[KEY_TEST_LABEL]
  result.operationLabels = specDict[KEY_OPLABEL]
  return result


def collectBasicTestResults(testSpecDict):
    testSpec = getSpecFromDict(testSpecDict)
    data = collectDataForOneTest(testSpec.tcLogSpec, testSpec.perfLogSpec)
    data.testLabel = testSpec.testLabel
    data.operationLabels = testSpec.operationLabels
    return data

# ---------------------------------------------------------
# Other test collection routines
# ---------------------------------------------------------


def collectDataFromNavigationTrimTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect benchmark results
    data = getDataFromFile((tcLogFile, "BenchmarkResults"));
    if debug: debugPrintResults(tcLogFile, data, outputfile)
    timingData.runTimes.append(secondsFromStopwatchLine(data[4]))  # Paint.TotalTime
    timingData.runTimes.append(secondsFromStopwatchLine(data[6]))  # Refresh.AverageTime

    # timings for other operations
    data = getDataFromFile((perfLogFile, "Action.Execute\tComplete"))
    timingData.runTimes.append(searchSecondsFromPerfLine(data, "Toggle automatic framing zone"))
    timingData.runTimes.append(searchSecondsFromPerfLine(data, "Trim/Extend"))

    if debug: debugPrintResults(perfLogFile, data, outputfile)
    return timingData


def collectDataFromBenchmarkTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    timingData = TimingData()

    collectStartupDataForTest(timingData, (tcLogFile,"TC.Stopwatch"))

    # collect benchmark results
    data = getDataFromFile((tcLogFile,"BenchmarkResults"));
    if debug: debugPrintResults(tcLogFile,data,outputfile)
    timingData.runTimes.append(secondsFromStopwatchLine(data[4]))  # Paint.TotalTime
    timingData.runTimes.append(secondsFromStopwatchLine(data[6]))  # Refresh.AverageTime

    return timingData

# ---------------------------------------------------------
# Main program
# ---------------------------------------------------------


def main():
    with open("baseline-results.txt", mode="w") as outputFile:
        timing_array = [collectBasicTestResults(dpt1dict),
                        collectBasicTestResults(dpt2dict),
                        collectBasicTestResults(bbt3dict)]

        outputTimingArrayToFile(timing_array, outputFile)

    outputTimingArrayToJSonFile(timing_array, "results.json")

    # with open("extra-results.txt",mode="w") as outputFile:
    #    timing_array = []

    # collect data from extra tests
    #    timing_array.append(collectDataFromNavigationTrimTest("NTT4"))
    #    timing_array.append(collectDataFromMonoToDuoTest("MDT5"))
    #    timing_array.append(collectDataFromFrameDesignTest("HD4_FDT6"))
    #    timing_array.append(collectDataFromFrameDesignTest("CHP_FDT10"))
    #    timing_array.append(collectDataFromHipToHipPlusTest("FR-HHT7"))
    #    timing_array.append(collectDataFromHipToHipPlusTest("UK-HHT8"))
    #    timing_array.append(collectDataFromBenchmarkTest("FR_LWS9"))
    #    timing_array.append(collectDataFromUK_ThousandDrawingObjectsTest("UK_TDOT17"))
    #    timing_array.append(collectDataFromBenchmarkTest("SW_FBMT11"))
    #    timing_array.append(collectDataFromBenchmarkTest("UK_HT1_FBMT12"))
    #    timing_array.append(collectDataFromOutputPDFTests("ISOLA_PDF13"))
    #    timing_array.append(collectDataFromOutputPDFTests("UK_LayoutPDF14"))
    #    timing_array.append(collectDataFromUK_DisableHangerHipToHipTest("UK-DISH15"))
    #    timing_array.append(collectDataFromUK_EnableHangerHipToHipTest("UK-ENAH16"))
    #    timing_array.append(collectDataFromFR_FileSizeTest("FR-MST18"))
    #    timing_array.append(collectDataFromFR_FileSizeTest("FR-SST19"))
    #    timing_array.append(collectDataFromFR_FileSizeTest("FR-DST20"))
    #    timing_array.append(collectDataFromUK_OpenAndSaveTest("UK-OST21"))
    #    timing_array.append(collectDataFromMultipleDesignCasesTest("T22-FR-MDC"))
    #    timing_array.append(collectDataFromFrameDesignWithScabTest("T23-FR-SCAB"))
    #    timing_array.append(collectDataFromFullSynchronisationTest("UK-SYNC"))
    #    timing_array.append(collectDataFromSapphireReportTest("UK-SAREP"))
    #    outputTimingArrayToFile(timing_array)

if __name__ == "__main__":
    main()
