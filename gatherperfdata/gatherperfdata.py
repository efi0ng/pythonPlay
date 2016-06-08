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
.
.
10. Added JSon output for the basic tests
"""

import sys
import os.path
import json

# globals

_debug = False
_output_file = None

# ---------------------------------------------------------
# TimingData and timing array output functions
# ---------------------------------------------------------


def sec_to_msec(secs):
    return int(secs*1000)


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
        test_json_dict = dict(ToLogin=sec_to_msec(self.startToLogin),
                              ToMainForm=sec_to_msec(self.loginToMainForm),
                              Shutdown=sec_to_msec(self.shutdown))

        if self.selectMetalwork is not None:
            test_json_dict['SelectMetalwork'] = sec_to_msec(self.selectMetalwork)

        if self.sapphireReport is not None:
            test_json_dict['SapphireReport'] = sec_to_msec(self.sapphireReport)

        if self.pamirShutdown is not None:
            test_json_dict['PamirShutdown'] = sec_to_msec(self.pamirShutdown)

        if self.sapphireShutdown is not None:
            test_json_dict['SapphireShutdown'] = sec_to_msec(self.sapphireShutdown)

        if self.fileSize is not None:
            test_json_dict['FileSize'] = self.fileSize

        if len(self.runTimes) != 0:
            for key, runTime in enumerate(self.runTimes):
                test_json_dict[self.operationLabels[key]] = sec_to_msec(runTime)

        return test_json_dict

    def to_file(self, outfile):
        print("%.3f\n%.3f" % (self.startToLogin, self.loginToMainForm), file=outfile)

        if self.selectMetalwork is not None:
            print ("%.3f" % self.selectMetalwork, file=outfile)  # print the time of selected Metalwork

        if len(self.runTimes) != 0:
            for runTime in self.runTimes:
                print("%.3f" % runTime, file=outfile)

        if self.sapphireReport is not None:
            print("%.3f" % self.sapphireReport, file=outfile)  # print the time of generating Sapphire Report

        if self.pamirShutdown is not None:
            print("%.3f" % self.pamirShutdown, file=outfile)  # print the time of Pamir Shutdown

        if self.sapphireShutdown is not None:
            print("%.3f" % self.sapphireShutdown, file=outfile)  # print the time of Sapphire Report Viewer Shutdown

        print("%.3f" % self.shutdown, file=outfile)

        if self.fileSize is not None:
            print("%.3f" % self.fileSize, file=outfile)  # print file size of the saved Pamir job

        print("", file=outfile)  # new line to create a gap for next result


def output_timings_to_json_file(timing_array, fileName):
    root_json_dict = {}

    for td in timing_array:
        if td is None:
            continue

        test_json_dict = td.to_json_dict()
        root_json_dict[td.testLabel] = test_json_dict

    with open(fileName, mode="w") as jsonFile:
        json.dump(root_json_dict, jsonFile, indent=3)


def output_timings_to_txt_file(timing_array, outfile):
    if _debug:
        print("\n===========================\n", file=outfile)

    for td in timing_array:
        if td is None:
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

def searchSecondsFromPerfLine(lines, searchString):
    for line in lines:
        if line.find(searchString) >= 0 :
            return secondsFromPerfLine(line)

    return 0.0


def getTotalTimeFromPerfLogRow(dataRow):
     (a,sep, timePlusSplits) = dataRow.rpartition(":")
     (timeStr,sep,b) = timePlusSplits.partition("(")
     return float(timeStr)


def collectStartupDataForTest(timing_data,tcLogSpec):
    """Collect data from the TestComplete Test logs for
    the startup and shutdown."""

    data = getDataFromFile(tcLogSpec)
    if _debug: debugPrintResults(tcLogSpec[0],data,_output_file)
    if (len(data) >= 2):
        timing_data.startToLogin = secondsFromStopwatchLine(data[0])
        timing_data.loginToMainForm = secondsFromStopwatchLine(data[1])
    if (len(data) == 3):
        timing_data.shutdown = secondsFromStopwatchLine(data[2])

    return


def MegaByteFromFileSizeLine(line):
    (a, b, killoStr) = line.rpartition(",")
    return float(killoStr.strip())/1024.0


def collectFileSizeForTest(timing_data,tcLogSpec):
    """Collect data from the TestComplete Test logs for
    the Pamir file size"""

    data = getDataFromFile(tcLogSpec)
    if _debug: debugPrintResults(tcLogSpec[0],data,_output_file)
    if (len(data) == 1):
        timing_data.fileSize = MegaByteFromFileSizeLine(data[0])

    return


def collectDataForOneTest(tcLogSpec, perfLogSpec):
    """Collect data from the TestComplete and Pamir Performance Test logs for
    one group of test runs."""

    timing_data = TimingData()

    collectStartupDataForTest(timing_data, tcLogSpec)

    data = getDataFromFile(perfLogSpec)
    if _debug: debugPrintResults(perfLogSpec[0], data, _output_file)
    for dataRow in data:
        timing_data.runTimes.append(getTotalTimeFromPerfLogRow(dataRow))

    return timing_data

# ---------------------------------------------------------
# Basic test specifications and collection
# ---------------------------------------------------------


class TestSpec:
    def __init__(self, tc_log, perf_log, test_label, op_labels):
        self.tcLogSpec = tc_log
        self.perfLogSpec = perf_log
        self.testLabel = test_label
        self.operationLabels = op_labels

DPT1_TEST = TestSpec(
    test_label="DPT1",
    op_labels=["Design1", "Check1", "Design2", "Check2", "Design3", "Check3", "Design4", "Check4", "Design5", "Check5"],
    tc_log=("./DPT1/testrun.log", "TC.Stopwatch"),
    perf_log=("./DPT1/data/pamir-perf.log", "UI.BuildDesign"))

DPT2_TEST = TestSpec(
    test_label="DPT2",
    op_labels=["Design1", "Check1", "Design2", "Check2", "Design3", "Check3", "Design4", "Check4", "Design5", "Check5"],
    tc_log=("./DPT2/testrun.log", "TC.Stopwatch"),
    perf_log=("./DPT2/data/pamir-perf.log", "UI.BuildDesign"))

BBT3_TEST = TestSpec(
    test_label="BBT3",
    op_labels=["Build1", "Build2", "Build3", "Build4", "Build5", "Build6", "Build7", "Build8", "Build9", "Build10"],
    tc_log=("./BBT3/testrun.log", "TC.Stopwatch"),
    perf_log=("./BBT3/data/pamir-perf.log", "UI.Build"))


def collect_basic_results(test_spec):
    data = collectDataForOneTest(test_spec.tcLogSpec, test_spec.perfLogSpec)
    data.testLabel = test_spec.testLabel
    data.operationLabels = test_spec.operationLabels
    return data

# ---------------------------------------------------------
# Other test collection routines
# ---------------------------------------------------------


def collectDataFromNavigationTrimTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    perfLogFile = "./" + folderName + "/data/Pamir-perf.log"
    timing_data = TimingData()

    collectStartupDataForTest(timing_data, (tcLogFile,"TC.Stopwatch"))

    # collect benchmark results
    data = getDataFromFile((tcLogFile, "BenchmarkResults"));
    if _debug: debugPrintResults(tcLogFile, data, _output_file)
    timing_data.runTimes.append(secondsFromStopwatchLine(data[4]))  # Paint.TotalTime
    timing_data.runTimes.append(secondsFromStopwatchLine(data[6]))  # Refresh.AverageTime

    # timings for other operations
    data = getDataFromFile((perfLogFile, "Action.Execute\tComplete"))
    timing_data.runTimes.append(searchSecondsFromPerfLine(data, "Toggle automatic framing zone"))
    timing_data.runTimes.append(searchSecondsFromPerfLine(data, "Trim/Extend"))

    if _debug: debugPrintResults(perfLogFile, data, _output_file)
    return timing_data


def collectDataFromBenchmarkTest(folderName):
    if not os.path.exists("./" + folderName):
        return None

    tcLogFile = "./" + folderName + "/testrun.log"
    timing_data = TimingData()

    collectStartupDataForTest(timing_data, (tcLogFile,"TC.Stopwatch"))

    # collect benchmark results
    data = getDataFromFile((tcLogFile,"BenchmarkResults"));
    if _debug: debugPrintResults(tcLogFile, data, _output_file)
    timing_data.runTimes.append(secondsFromStopwatchLine(data[4]))  # Paint.TotalTime
    timing_data.runTimes.append(secondsFromStopwatchLine(data[6]))  # Refresh.AverageTime

    return timing_data

# ---------------------------------------------------------
# Main program
# ---------------------------------------------------------


def main():
    with open("baseline-results.txt", mode="w") as _output_file:
        timing_array = [collect_basic_results(DPT1_TEST),
                        collect_basic_results(DPT2_TEST),
                        collect_basic_results(BBT3_TEST)]

        output_timings_to_txt_file(timing_array, _output_file)

    output_timings_to_json_file(timing_array, "results.json")

    # with open("extra-results.txt",mode="w") as _output_file:
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
    #    output_timings_to_txt_file(timing_array)

if __name__ == "__main__":
    main()
