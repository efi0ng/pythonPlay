#!/usr/bin/env python3

import sys
import os.path
import json
import re
from datetime import datetime

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
_TEST_SUITE_LABEL = "TestComplete"

# ---------------------------------------------------------
'''
Information output to JSon
--------------------------
TestSuiteRun
    label - theoretically unique to this test run but may be a duplicate as we only use the folder name
    startDateTime - uses the start time of the first test. if no tests were run, it uses the folder modified time.
    duration: total of the test result durations. ideally elapsed time
    buildTested
    TODO: notes
    testSuiteLabel
    testEnvironmentId - currently hardcoded. might be supplied as an argument.
    testResults - array of TestResult

TestResult
    label: label identifying the test
    startDateTime : time stamp when the test started.
    duration: total of the test operation durations. ideally elapsed time
    operationResults: array of TestOperationResult

TestOperationResult
    label: operation label
    value: typically duration in ms but could be kilobytes for file size

Added:

TestMachine
BuildInfo

'''

# ---------------------------------------------------------
# General parsing and conversion functions
# ---------------------------------------------------------


def debug_print_results(filename, data, outfile=sys.stdout):
    print("[%s]" % filename, file=outfile)

    for line in data:
        print(line, file=outfile)


def get_testlog_path(test_dir):
    return os.path.join(test_dir, "testrun.log")


def get_perf_log_path(test_dir):
    return os.path.join(test_dir, "data/pamir-perf.log")


def get_pamir_log_path(test_dir):
    return os.path.join(test_dir, "data/pamir.log")


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
                # remove the to_seconds unit suffix
                line = line.replace("s ", " ")
                results.append(line)

            line = file.readline()
    except IOError:
        pass
    finally:
        if file:
            file.close()

    return results


_TIMESTAMP_PAMIR_FORMAT = "%Y-%m-%d %H:%M:%S,%f"
_TIMESTAMP_JSON_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def collect_start_and_duration_from_pamir_log(test_dir):
    """Use first and last long entry in the Pamir log as a guide for when test started and how long it ran.
    Return tuple (start, duration) where start is a datetime and duration is milliseconds (integer).
    If collection fails, start_time may be set to file date time or current time but duration is always set to 0."""

    # We want to capture timestamps from lines like:
    #   2016-05-26 12:28:19,929 Serializer.ArchiveTypeResolver INFO : Processing assemblies on thread 5
    _TIMESTAMP_REGEX = r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"

    log_file = get_pamir_log_path(test_dir)

    file = None
    first_valid_stamp = None
    last_valid_stamp = None
    try:
        file = open(log_file, mode="r")

        line = file.readline()
        while line:
            # decide if current line is worthy
            match = re.search(_TIMESTAMP_REGEX, line)
            if match:
                if first_valid_stamp is None:
                    first_valid_stamp = match.group(1)
                else:
                    last_valid_stamp = match.group(1)
            line = file.readline()

        if _debug:
            print("Search results were: {} {}".format(first_valid_stamp, last_valid_stamp))
    except IOError:
        pass
    finally:
        if file:
            file.close()

    if first_valid_stamp is None:
        start_time = get_file_datetime(log_file)
    else:
        start_time = datetime.strptime(first_valid_stamp, _TIMESTAMP_PAMIR_FORMAT)

    if last_valid_stamp is None:
        duration = 0
    else:
        end_time = datetime.strptime(last_valid_stamp, _TIMESTAMP_PAMIR_FORMAT)
        duration_delta = end_time - start_time
        duration = int(duration_delta.total_seconds() * 1000)

    return start_time, duration


def get_file_datetime(filename: str) -> datetime:
    mod_time = os.path.getmtime(filename)
    return datetime.fromtimestamp(mod_time)


def datetime_in_utc_format(value: datetime) -> str:
    """Convert a datetime to the UTC format we are using in JSon files"""
    if value is None:
        return ""

    return value.strftime(_TIMESTAMP_JSON_FORMAT)


def get_total_time_from_perf_line(perf_line: str):
    (a, sep, time_plus_splits) = perf_line.rpartition(":")
    (time_str, sep, b) = time_plus_splits.partition("(")
    return float(time_str)


def kilobytes_from_file_size_line(line):
    (a, b, kilo_str) = line.rpartition(",")
    return int(float(kilo_str.strip()))


def milliseconds_from_stopwatch_line(line):
    (a, b, milli_str) = line.rpartition(",")
    return int(float(milli_str.strip()))


def ms_to_sec(ms):
    return float(ms/1000.0)


def sec_to_ms(secs):
    return int(secs*1000)


def seconds_from_stopwatch_line(line):
    return milliseconds_from_stopwatch_line(line)/1000.0


def seconds_from_perf_line(line):
    parts = line.split("\t")
    return float(parts[4])/1000.0


def search_seconds_from_perf_lines(lines, search_string):
    for line in lines:
        if line.find(search_string) >= 0:
            return seconds_from_perf_line(line)

    return 0.0


def get_pamir_version_from_log(test_dir):
    """Get Pamir version information from log in given test dir.
    Returns (version_short, version_full, revision) a tuple of strings."""
    # capture Pamir version information from lines like:
    # 2016-05-26 12:43:28,262 MiTek.Pamir INFO : Pamir 5.1.0 (Internal WIP 5.1.0.3149 (r70160)) starting
    # 2016-06-14 12:06:11,298 MiTek.Pamir INFO : Pamir 5.1.2 (5.1.2.38 (r70761)) starting
    # 2015-06-18 13:49:35,348 MiTek.Pamir INFO : Pamir 4.0.3 (56480) starting

    _PAMIR_VERSION_LINE_REGEX = r"Pamir (\d{1}.\d{1}.\d{1}) \((.+)\) start"

    log_file = get_pamir_log_path(test_dir)
    version_short = ""
    version_full = ""
    revision = 0

    file = None
    try:
        file = open(log_file, mode="r")

        line = file.readline()
        while line:
            match = re.search(_PAMIR_VERSION_LINE_REGEX, line)
            if match:
                version_short = match.group(1)
                version_full = match.group(2)
                break

            line = file.readline()

    except IOError:
        pass
    finally:
        if file:
            file.close()

    if version_full != "":
        # look for bracketed revision within the full version string
        match = re.search(r"\((.+)\)", version_full)
        if match:
            revision = int(re.sub("r", "", match.group(1)))

    if _debug:
        print("Version search results were: {}, {}, {}".format(version_short, version_full, revision))

    return version_short, version_full, revision


# ---------------------------------------------------------
# Model classes inc. TestResult
# ---------------------------------------------------------


class JSonLabels:
    """Magic strings for JSon export"""
    LABEL = "label"
    VALUE = "value"
    NOTES = "notes"
    DURATION = "duration"
    START_TIME = "startDateTime"
    STATUS = "status"
    OP_RESULTS = "operationResults"
    TEST_SUITE_LABEL = "testSuiteLabel"
    TEST_RESULTS = "testResults"
    MACHINE = "machine"
    NAME = "name"
    PROCESSOR = "processor"
    CPU_COUNT = "logicalCores"
    MEMORY = "memory"
    OPERATING_SYSTEM = "operatingSystem"
    VERSION_SHORT = "versionShort"
    VERSION_LONG = "versionLong"
    REVISION = "revision"
    BUILD_TESTED = "buildTested"


class OpLabels:
    """Holds all the magic strings for operation labels"""
    TO_LOGIN = "ToLogin"
    TO_MAIN_FORM = "ToMainForm"
    PAMIR_SHUTDOWN = "PamirShutdown"
    SELECT_METALWORK = "SelectMetalwork"
    SAPPHIRE_REPORT = "SapphireReport"
    TWENTY20_SHUTDOWN = "2020Shutdown"
    SAPPHIRE_SHUTDOWN = "SapphireShutdown"
    FILE_SIZE = "FileSize"


class OpResult:
    """Result of an operation"""
    def __init__(self, label: str, value: int, source_line: str = ""):
        self.label = label
        self.value = value
        self.source_line = source_line

    def to_seconds(self):
        """Assuming value is a duration in ms, returns value in seconds."""
        return self.value/1000.0

    def to_megabytes(self):
        """Assuming value is kilobytes, return value in megabytes"""
        return self.value/1024.0

    def to_json_object(self):
        """Convert this OpResult into an object tailored for json serialization."""
        json_dict = {
            JSonLabels.LABEL: self.label,
            JSonLabels.VALUE: self.value,
        }
        return json_dict


class TestMachine:
    """Encapsulates information describing a test machine and the methods to gather that
    information for the machine this code is running on.

    Requires psutil which can be installed via  python.exe -m pip install psutil"""
    def __init__(self):
        self.name = ""
        self.processor = ""
        self.logical_cores = 0
        self.memory = 0
        self.operating_system = ""

    def to_json_object(self):
        return {
            JSonLabels.NAME: self.name,
            JSonLabels.PROCESSOR: self.processor,
            JSonLabels.OPERATING_SYSTEM: self.operating_system,
            JSonLabels.CPU_COUNT: self.logical_cores,
            JSonLabels.MEMORY: self.memory
        }


class BuildInfo:
    def __init__(self, ver_short, ver_long, rev):
        self.version_short = ver_short
        self.version_long = ver_long
        self.revision = rev

    def to_json_object(self):
        return {
            JSonLabels.VERSION_SHORT: self.version_short,
            JSonLabels.VERSION_LONG: self.version_long,
            JSonLabels.REVISION: self.revision,
        }


def test_machine_from_host():
    import platform
    from psutil import cpu_count, virtual_memory

    machine = TestMachine()
    machine.name = platform.node()
    machine.processor = platform.processor()
    machine.logical_cores = cpu_count()
    machine.operating_system = "{} {} {}".format(platform.system(), platform.release(), platform.version())
    machine.memory = int(virtual_memory().total / (1024*1024))
    return machine


class TestResult:
    """Collected timing information for a test"""
    def __init__(self, test_label: str):
        self.selectMetalwork = None
        self.sapphireReport = None
        self.sapphireShutdown = None
        self.twenty20Shutdown = None
        self.op_results = {}
        self.runTimes = []
        # for JSon support
        self.label = test_label
        self.op_labels = []
        self.start_time = None  # datetime
        self.duration = 0  # milliseconds

    def add_op_result(self, op_result: OpResult):
        self.op_results[op_result.label] = op_result

    def to_json_object(self):
        """Convert this TestResult into an object tailored for json serialization."""
        json_op_results = []

        json_dict = {
            JSonLabels.LABEL: self.label,
            JSonLabels.OP_RESULTS: json_op_results,
            JSonLabels.START_TIME: datetime_in_utc_format(self.start_time),
            JSonLabels.DURATION: self.duration,
        }

        for op in self.op_results.values():
            json_op_results.append(op.to_json_object())

        if self.selectMetalwork is not None:
            op = OpResult(OpLabels.SELECT_METALWORK, sec_to_ms(self.selectMetalwork))
            json_op_results.append(op.to_json_object())

        if self.sapphireReport is not None:
            op = OpResult(OpLabels.SAPPHIRE_REPORT, sec_to_ms(self.sapphireReport))
            json_op_results.append(op.to_json_object())

        if self.twenty20Shutdown is not None:
            op = OpResult(OpLabels.TWENTY20_SHUTDOWN, self.twenty20Shutdown)
            json_op_results.append(op.to_json_object())

        if self.sapphireShutdown is not None:
            op = OpResult(OpLabels.SAPPHIRE_SHUTDOWN, sec_to_ms(self.sapphireShutdown))
            json_op_results.append(op.to_json_object())

        if len(self.runTimes) != 0:
            for key, runTime in enumerate(self.runTimes):
                op = OpResult(self.op_labels[key], sec_to_ms(runTime))
                json_op_results.append(op.to_json_object())

        return json_dict

    def to_file(self, outfile):
        to_login = self.op_results[OpLabels.TO_LOGIN].to_seconds()
        to_main_form = self.op_results[OpLabels.TO_MAIN_FORM].to_seconds()
        print("{:.3f}\n{:.3f}".format(to_login, to_main_form), file=outfile)

        if self.selectMetalwork is not None:
            print("{:.3f}".format(self.selectMetalwork), file=outfile)

        if len(self.runTimes) != 0:
            for runTime in self.runTimes:
                print("{:.3f}".format(runTime), file=outfile)

        if self.sapphireReport is not None:
            print("{:.3f}".format(self.sapphireReport), file=outfile)  # generating Sapphire Report

        if OpLabels.PAMIR_SHUTDOWN in self.op_results:
            print("{:.3f}".format(self.op_results[OpLabels.PAMIR_SHUTDOWN].to_seconds()), file=outfile)

        if self.sapphireShutdown is not None:
            print("{:.3f}".format(self.sapphireShutdown), file=outfile)  # Sapphire Report Viewer Shutdown

        if self.twenty20Shutdown is not None:
            print("{:.3f}".format(self.twenty20Shutdown), file=outfile)

        if OpLabels.FILE_SIZE in self.op_results:
            print("{:.3f}".format(self.op_results[OpLabels.FILE_SIZE].to_megabytes()), file=outfile)

        print("", file=outfile)  # new line to create a gap for next result


class TestSuiteRun:
    def __init__(self, suite_label: str, machine: TestMachine):
        self.label = ""
        self.suite_label = suite_label
        self.test_results = []
        self.notes = ""
        self.machine = machine
        self.start_time = datetime.today()
        self.duration = 0
        self.build_info = BuildInfo("", "", 0)

    def append_result(self, result: TestResult):
        self.test_results.append(result)

    def calc_start_duration_from_tests(self):
        if self.test_results.count == 0:
            return False

        self.start_time = self.test_results[0].start_time
        self.duration = self.test_results[0].duration

        for i in range(1, len(self.test_results)):
            next_result = self.test_results[i]
            if next_result.start_time < self.start_time:
                self.start_time = next_result.start_time

            self.duration += next_result.duration

    def to_json_object(self):
        test_result_json = [r.to_json_object() for r in self.test_results]

        result = {
            JSonLabels.LABEL: self.label,
            JSonLabels.TEST_SUITE_LABEL: self.suite_label,
            JSonLabels.TEST_RESULTS: test_result_json,
            JSonLabels.NOTES: self.notes,
            JSonLabels.MACHINE: self.machine.to_json_object(),
            JSonLabels.DURATION: self.duration,
            JSonLabels.START_TIME: datetime_in_utc_format(self.start_time),
            JSonLabels.BUILD_TESTED: self.build_info.to_json_object(),
        }
        return result

    def to_json_file(self, filename: str):
        with open(filename, mode="w") as jsonFile:
            json.dump(self.to_json_object(), jsonFile, indent=3, sort_keys=True)


# ---------------------------------------------------------
# Data collection - general
# ---------------------------------------------------------

_SEARCH_STRING_STOPWATCH = "TC.Stopwatch"


def collect_startup_data(test_result, test_dir):
    """Collect timing from the TestComplete Test logs for
    the startup and shutdown."""

    filename = get_testlog_path(test_dir)
    lines = get_matching_lines_from_file(filename, _SEARCH_STRING_STOPWATCH)

    if len(lines) >= 2:
        test_result.add_op_result(OpResult(
            OpLabels.TO_LOGIN,
            milliseconds_from_stopwatch_line(lines[0]),
            lines[0]))
        test_result.add_op_result(OpResult(
            OpLabels.TO_MAIN_FORM,
            milliseconds_from_stopwatch_line(lines[1]),
            lines[1]))

    if len(lines) == 3:
        test_result.add_op_result(OpResult(
            OpLabels.PAMIR_SHUTDOWN,
            milliseconds_from_stopwatch_line(lines[2]),
            lines[2]))

    return


def collect_pamir_start_and_duration(test_result, test_dir):
    start, duration = collect_start_and_duration_from_pamir_log(test_dir)
    test_result.start_time = start
    test_result.duration = duration
    return


def collect_file_size_for_test(test_result, filename, search_string):
    """Collect data from the TestComplete Test logs for
    the Pamir file size"""

    lines = get_matching_lines_from_file(filename, search_string)
    if _debug:
        debug_print_results(filename, lines, _output_file)
    if len(lines) > 0:
        file_size = kilobytes_from_file_size_line(lines[0])
        result = OpResult(OpLabels.FILE_SIZE, file_size, lines[0])
        test_result.add_op_result(result)

    return


def collect_basic_test_data(test_dir: str, test_label: str, perf_search_str: str):
    """Collect data from the TestComplete and Pamir Performance Test logs for
    one test."""

    test_result = TestResult(test_label)

    collect_startup_data(test_result, test_dir)
    collect_pamir_start_and_duration(test_result, test_dir)
    perf_filename = get_perf_log_path(test_dir)
    data = get_matching_lines_from_file(perf_filename, perf_search_str)
    if _debug:
        debug_print_results(perf_filename, data, _output_file)

    for dataRow in data:
        test_result.runTimes.append(get_total_time_from_perf_line(dataRow))

    return test_result


def collect_build_info_from_test(base_path, test_label):
    version_info = get_pamir_version_from_log(test_dir_from_label(base_path, test_label))
    return BuildInfo(version_info[0], version_info[1], version_info[2])


def collect_test_suite_run_data(test_suite_run: TestSuiteRun, base_path: str):
    """Collect information to populate a TestSuiteRun object. Call this after you've added all the test results."""
    normed_dir = os.path.normpath(base_path)
    test_suite_run.label = os.path.basename(normed_dir)

    if len(test_suite_run.test_results) > 0:
        test_suite_run.build_info = collect_build_info_from_test(base_path, test_suite_run.test_results[0].label)

    if not test_suite_run.calc_start_duration_from_tests():
        test_suite_run.startDateTime = get_file_datetime(base_path)

    pass


# ---------------------------------------------------------
# Basic test specifications and collection
# ---------------------------------------------------------


class TestSpec:
    def __init__(self, perf_search_str, test_label, op_labels):
        self.perf_search_str = perf_search_str
        self.test_label = test_label
        self.op_labels = op_labels

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
    data = collect_basic_test_data(test_dir, test_spec.test_label, test_spec.perf_search_str)
    data.label = test_spec.test_label
    data.op_labels = test_spec.op_labels
    return data

# ---------------------------------------------------------
# Other test collection routines
# ---------------------------------------------------------


def collect_data_from_nav_trim_test(test_dir, test_label):
    if not os.path.exists(test_dir):
        return None

    test_result = TestResult(test_label)
    test_result.op_labels = ["LayoutPaint", "Refresh", "ChangeAutoLevel", "TrimExtend"]

    tc_log_file = get_testlog_path(test_dir)
    perf_log_file = get_perf_log_path(test_dir)
    collect_startup_data(test_result, test_dir)
    collect_pamir_start_and_duration(test_result, test_dir)

    # collect benchmark results
    lines = get_matching_lines_from_file(tc_log_file, "BenchmarkResults")
    if _debug:
        debug_print_results(tc_log_file, lines, _output_file)
    test_result.runTimes.append(seconds_from_stopwatch_line(lines[4]))  # Paint.TotalTime
    test_result.runTimes.append(seconds_from_stopwatch_line(lines[6]))  # Refresh.AverageTime

    # timings for other operations
    lines = get_matching_lines_from_file(perf_log_file, "Action.Execute\tComplete")
    test_result.runTimes.append(search_seconds_from_perf_lines(lines, "Toggle automatic framing zone"))
    test_result.runTimes.append(search_seconds_from_perf_lines(lines, "Trim/Extend"))

    if _debug: 
        debug_print_results(perf_log_file, lines, _output_file)
    return test_result


def collect_benchmark_data(test_dir, test_label):
    if not os.path.exists(test_dir):
        return None

    test_result = TestResult(test_label)

    collect_startup_data(test_result, test_dir)

    # collect benchmark results
    tc_log_file = get_testlog_path(test_dir)
    data = get_matching_lines_from_file(tc_log_file, "BenchmarkResults")
    if _debug:
        debug_print_results(tc_log_file, data, _output_file)

    test_result.runTimes.append(seconds_from_stopwatch_line(data[4]))  # Paint.TotalTime
    test_result.runTimes.append(seconds_from_stopwatch_line(data[6]))  # Refresh.AverageTime

    return test_result


def collect_fr_filesize_data(test_dir, test_label):
    if not os.path.exists(test_dir):
        return None

    test_result = TestResult(test_label)
    test_result.op_labels = ["BuildDesign"]

    tc_log_file = get_testlog_path(test_dir)
    perf_log_file = get_perf_log_path(test_dir)
    collect_startup_data(test_result, test_dir)
    collect_pamir_start_and_duration(test_result, test_dir)

    # collect the total time of designing all frames from "Pamir-perf.log"
    lines = get_matching_lines_from_file(perf_log_file, "BuildDesign")
    for line in lines:
        test_result.runTimes.append(get_total_time_from_perf_line(line))

    # collect file size of the saved Pamir job
    collect_file_size_for_test(test_result, tc_log_file, "Pamir job:")

    return test_result


# ---------------------------------------------------------
# Main program
# ---------------------------------------------------------


def test_dir_from_label(base_path, test_label):
    return os.path.join(base_path, test_label)


def output_timings_to_txt_file(test_results, outfile):
    if _debug:
        print("\n===========================\n", file=outfile)

    for td in test_results:
        if td is None:
            continue

        td.to_file(outfile)


def main(base_path):
    global _output_file
    machine = test_machine_from_host()

    test_suite_run = TestSuiteRun(_TEST_SUITE_LABEL, machine)

    with open(os.path.join(base_path, "baseline-results.txt"), mode="w") as _output_file:
        timing_array = [collect_basic_results(test_dir_from_label(base_path, DPT1_TEST.test_label), DPT1_TEST),
                        collect_basic_results(test_dir_from_label(base_path, DPT2_TEST.test_label), DPT2_TEST),
                        collect_basic_results(test_dir_from_label(base_path, BBT3_TEST.test_label), BBT3_TEST)]
        output_timings_to_txt_file(timing_array, _output_file)

    with open(os.path.join(base_path, "extra-results.txt"), mode="w") as _output_file:
        timing_array2 = [collect_data_from_nav_trim_test(test_dir_from_label(base_path, "NTT4"), "NTT4"),
                         collect_fr_filesize_data(test_dir_from_label(base_path, "FR-MST18"), "FR-MST18"),
                         collect_fr_filesize_data(test_dir_from_label(base_path, "FR-SST19"), "FR-SST19"),
                         collect_fr_filesize_data(test_dir_from_label(base_path, "FR-DST20"), "FR-DST20"),
                         ]
        output_timings_to_txt_file(timing_array2, _output_file)

    timing_array.extend(timing_array2)
    for td in timing_array:
        if td is not None:
            test_suite_run.append_result(td)

    collect_test_suite_run_data(test_suite_run, base_path)
    test_suite_run.to_json_file(os.path.join(base_path, "results.json"))

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
    #    timing_array.append(collectDataFromUK_OpenAndSaveTest("UK-OST21"))
    #    timing_array.append(collectDataFromMultipleDesignCasesTest("T22-FR-MDC"))
    #    timing_array.append(collectDataFromFrameDesignWithScabTest("T23-FR-SCAB"))
    #    timing_array.append(collectDataFromFullSynchronisationTest("UK-SYNC"))
    #    timing_array.append(collectDataFromSapphireReportTest("UK-SAREP"))

if __name__ == "__main__":
    _base_path = os.getcwd()
    if len(sys.argv) > 1:
        _base_path = sys.argv[1]

    main(_base_path)
