#!/usr/bin/env python3

import sys
import os.path
import json

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

# globals

_debug = False
_output_file = None

# ---------------------------------------------------------
'''
Information output to JSon
--------------------------
TestSuiteRun
    TODO: testSuiteLabel (something else can look up the testSuiteId)
    TODO: startDateTime
    TODO: duration: total of the test result durations. ideally elapsed time
    TODO: buildTestedId:
    IGNORED: testEnvironmentId

TestResult
    testLabel
    TODO: startDateTime
    TODO: duration: total of the test operation durations. ideally elapsed time
    ----
    IGNORED: status : assume a pass?
    IGNORED: notes
    N/A: testId: inferred by hierarchy

TestOperationResult
    TODO: startDateTime: only useful for diagonostics. Might skip?
    duration (ms)
    ---
    IGNORED: status : assume a pass
    IGNORED: varianceFromBaseline: can be supplied by the server
    N/A: testOpResultId: supplied by the server
    N/A: testOperationId: inferred by hierarchy


'''

# ---------------------------------------------------------
# TimingData and timing array output functions
# ---------------------------------------------------------


def sec_to_msec(secs):
    return int(secs*1000)


class TimingData:
    def __init__(self):
        self.startToLogin = 0.0
        self.loginToMainForm = 0.0
        self.pamirShutdown = None
        self.selectMetalwork = None
        self.fileSize = None
        self.sapphireReport = None
        self.sapphireShutdown = None
        self.twenty20Shutdown = None
        self.runTimes = []
        # for JSon support
        self.testLabel = None
        self.operationLabels = []

    def to_json_dict(self):
        test_json_dict = dict(ToLogin=sec_to_msec(self.startToLogin),
                              ToMainForm=sec_to_msec(self.loginToMainForm))

        if self.selectMetalwork is not None:
            test_json_dict['SelectMetalwork'] = sec_to_msec(self.selectMetalwork)

        if self.sapphireReport is not None:
            test_json_dict['SapphireReport'] = sec_to_msec(self.sapphireReport)

        if self.twenty20Shutdown is not None:
            test_json_dict['2020Shutdown'] = sec_to_msec(self.twenty20Shutdown)

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

        if self.twenty20Shutdown is not None:
            print("%.3f" % self.twenty20Shutdown, file=outfile)

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

_SEARCH_STRING_STOPWATCH = "TC.Stopwatch"


def debug_print_results(filename, data, outfile=sys.stdout):
    print("[%s]" % filename, file=outfile)

    for line in data:
        print(line, file=outfile)


def get_testlog_path(test_dir):
    return os.path.join(test_dir, "testrun.log")


def get_perf_log_path(test_dir):
    return os.path.join(test_dir, "data/pamir-perf.log")


def get_matching_lines_from_file(filename, tag_to_find):
    """traverses the file stream to get perf data from the tag_to_find elements.
    returns as a list"""
    results = []
    file = None
    try:
        file = open(filename, mode="r")

        line = file.readline()
        while line:
            line = line.strip()
            if line.find(tag_to_find) >= 0:
                # remove the seconds unit suffix
                line = line.replace("s ", " ")
                results.append(line)

            line = file.readline()
    except IOError:
        pass
    finally:
        if file:
            file.close()

    return results


def seconds_from_stopwatch_line(line):
    (a, b, milli_str) = line.rpartition(",")
    return float(milli_str.strip())/1000.0


def seconds_from_perf_line(line):
    parts = line.split("\t")
    return float(parts[4])/1000.0


def search_seconds_from_perf_lines(lines, search_string):
    for line in lines:
        if line.find(search_string) >= 0 :
            return seconds_from_perf_line(line)

    return 0.0


def get_total_time_from_perf_line(perf_line):
    (a, sep, time_plus_splits) = perf_line.rpartition(":")
    (time_str, sep, b) = time_plus_splits.partition("(")
    return float(time_str)


def collect_startup_data(timing_data, test_dir):
    """Collect data from the TestComplete Test logs for
    the startup and shutdown."""

    filename = get_testlog_path(test_dir)
    data = get_matching_lines_from_file(filename, _SEARCH_STRING_STOPWATCH)
    if _debug:
        debug_print_results(filename, data, _output_file)

    if len(data) >= 2:
        timing_data.startToLogin = seconds_from_stopwatch_line(data[0])
        timing_data.loginToMainForm = seconds_from_stopwatch_line(data[1])
    if len(data) == 3:
        timing_data.pamirShutdown = seconds_from_stopwatch_line(data[2])

    return


def megabytes_from_file_size_line(line):
    (a, b, kilo_str) = line.rpartition(",")
    return float(kilo_str.strip())/1024.0


def collect_file_size_for_test(timing_data, tc_log_spec):
    """Collect data from the TestComplete Test logs for
    the Pamir file size"""

    data = get_matching_lines_from_file(tc_log_spec[0].tc_log_spec[1])
    if _debug:
        debug_print_results(tc_log_spec[0], data, _output_file)
    if len(data) == 1:
        timing_data.fileSize = megabytes_from_file_size_line(data[0])

    return


def collect_basic_test_data(test_dir, test_label, perf_search_str):
    """Collect data from the TestComplete and Pamir Performance Test logs for
    one test."""

    timing_data = TimingData()
    timing_data.testLabel = test_label

    collect_startup_data(timing_data, test_dir)
    perf_filename = get_perf_log_path(test_dir)
    data = get_matching_lines_from_file(perf_filename, perf_search_str)
    if _debug:
        debug_print_results(perf_filename, data, _output_file)

    for dataRow in data:
        timing_data.runTimes.append(get_total_time_from_perf_line(dataRow))

    return timing_data

# ---------------------------------------------------------
# Basic test specifications and collection
# ---------------------------------------------------------


class TestSpec:
    def __init__(self, perf_search_str, test_label, op_labels):
        self.perf_search_str = perf_search_str
        self.testLabel = test_label
        self.operationLabels = op_labels

DPT1_TEST = TestSpec(
    test_label="DPT1",
    op_labels=["Design1", "Check1", "Design2", "Check2", "Design3", "Check3", "Design4", "Check4", "Design5", "Check5"],
    perf_search_str="UI.BuildDesign")

DPT2_TEST = TestSpec(
    test_label="DPT2",
    op_labels=["Design1", "Check1", "Design2", "Check2", "Design3", "Check3", "Design4", "Check4", "Design5", "Check5"],
    perf_search_str="UI.BuildDesign")

BBT3_TEST = TestSpec(
    test_label="BBT3",
    op_labels=["Build1", "Build2", "Build3", "Build4", "Build5", "Build6", "Build7", "Build8", "Build9", "Build10"],
    perf_search_str="UI.Build")


def collect_basic_results(test_dir, test_spec):
    data = collect_basic_test_data(test_dir, test_spec.testLabel, test_spec.perf_search_str)
    data.testLabel = test_spec.testLabel
    data.operationLabels = test_spec.operationLabels
    return data

# ---------------------------------------------------------
# Other test collection routines
# ---------------------------------------------------------


def collect_data_from_nav_trim_test(test_dir, test_label):
    if not os.path.exists(test_dir):
        return None

    timing_data = TimingData()
    timing_data.testLabel = test_label
    timing_data.operationLabels = ["LayoutPaint", "Refresh", "ChangeAutoLevel", "TrimExtend"]

    tc_log_file = get_testlog_path(test_dir)
    perf_log_file = get_perf_log_path(test_dir)
    collect_startup_data(timing_data, test_label)

    # collect benchmark results
    lines = get_matching_lines_from_file(tc_log_file, "BenchmarkResults")
    if _debug:
        debug_print_results(tc_log_file, lines, _output_file)
    timing_data.runTimes.append(seconds_from_stopwatch_line(lines[4]))  # Paint.TotalTime
    timing_data.runTimes.append(seconds_from_stopwatch_line(lines[6]))  # Refresh.AverageTime

    # timings for other operations
    lines = get_matching_lines_from_file(perf_log_file, "Action.Execute\tComplete")
    timing_data.runTimes.append(search_seconds_from_perf_lines(lines, "Toggle automatic framing zone"))
    timing_data.runTimes.append(search_seconds_from_perf_lines(lines, "Trim/Extend"))

    if _debug: 
        debug_print_results(perf_log_file, lines, _output_file)
    return timing_data


def collect_benchmark_data(test_dir, test_label):
    if not os.path.exists(test_dir):
        return None

    timing_data = TimingData()

    collect_startup_data(timing_data, test_dir)

    # collect benchmark results
    tc_log_file = get_testlog_path(test_dir)
    data = get_matching_lines_from_file(tc_log_file, "BenchmarkResults")
    if _debug:
        debug_print_results(tc_log_file, data, _output_file)

    timing_data.runTimes.append(seconds_from_stopwatch_line(data[4]))  # Paint.TotalTime
    timing_data.runTimes.append(seconds_from_stopwatch_line(data[6]))  # Refresh.AverageTime

    return timing_data

# ---------------------------------------------------------
# Main program
# ---------------------------------------------------------


def test_dir_from_label(base_path, test_label):
    return os.path.join(base_path, test_label)


def main():
    global _output_file
    base_path = "./"
    with open("baseline-results.txt", mode="w") as _output_file:
        timing_array = [collect_basic_results(test_dir_from_label(base_path, DPT1_TEST.testLabel), DPT1_TEST),
                        collect_basic_results(test_dir_from_label(base_path, DPT2_TEST.testLabel), DPT2_TEST),
                        collect_basic_results(test_dir_from_label(base_path, BBT3_TEST.testLabel), BBT3_TEST)]
        output_timings_to_txt_file(timing_array, _output_file)

    with open("extra-results.txt", mode="w") as _output_file:
        timing_array2 = [collect_data_from_nav_trim_test(test_dir_from_label(base_path, "NTT4"), "NTT4")]
        output_timings_to_txt_file(timing_array2, _output_file)

    for td in timing_array2:
        if td is not None:
            timing_array.append(td)

    output_timings_to_json_file(timing_array, "results.json")

    # collect data from extra tests
    #    timing_array.append(collectDataFromMonoToDuoTest("MDT5"))
    #    timing_array.append(collectDataFromFrameDesignTest("HD4_FDT6"))
    #    timing_array.append(collectDataFromFrameDesignTest("CHP_FDT10"))
    #    timing_array.append(collectDataFromHipToHipPlusTest("FR-HHT7"))
    #    timing_array.append(collectDataFromHipToHipPlusTest("UK-HHT8"))
    #    timing_array.append(collect_benchmark_data("FR_LWS9"))
    #    timing_array.append(collectDataFromUK_ThousandDrawingObjectsTest("UK_TDOT17"))
    #    timing_array.append(collect_benchmark_data("SW_FBMT11"))
    #    timing_array.append(collect_benchmark_data("UK_HT1_FBMT12"))
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

if __name__ == "__main__":
    main()
