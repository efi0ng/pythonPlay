#!/usr/bin/env python3

import sys
import os.path
import json
import re
from datetime import datetime
from typing import Dict
from enum import Enum

__author__ = 'JSmith' and 'SZhang'

"""assumes usual performance test hierarchy of folders.
processes the perf logs of the following tests to get the data required
for the baseline and extra performance tests reporting spreadsheets:
DPT1, DPT2, BBT3, NTT4, MDT5, HD4_FDT6, FR_HHT7, UK_HHT8, FR_LWS9 and CHP_FDT10
Several more tests have been added since.
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
    startDateTime - uses the start time of the first test. if no tests were run, it uses the folder modified time.
    duration: total of the test result durations. ideally elapsed time
    buildTested
    notes
    testSuiteLabel
    testEnvironmentId - currently hardcoded. might be supplied as an argument.
    testResults - array of TestResult

TestResult
    label: label identifying the test
    startDateTime : time stamp when the test started.
    duration: total of the test operation durations. ideally elapsed time
    operationResults: array of TestOperationResult
    status: currently always "pass" as failures are not recorded.

TestOperationResult
    label: operation label
    duration: duration in ms or zero if no time registered
    fileSize: size in kilobytes or zero if no size recorded

Added:

TestMachine
BuildInfo

'''

# ---------------------------------------------------------
# General parsing and conversion functions
# Methods here should not have knowledge of test folder structure
# ---------------------------------------------------------


def get_matching_lines_from_file(filename, tag_to_find):
    """traverses the file stream to get perf data from the tag_to_find elements.
    returns as a list"""
    results = []
    file = None
    try:
        file = open(filename, mode="r", errors="ignore")

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


def parse_start_and_duration_from_pamir_log(filename):
    """Use first and last long entry in the Pamir log as a guide for when test started and how long it ran.
    Return tuple (start, duration) where start is a datetime and duration is milliseconds (integer).
    If collection fails, start_time may be set to file date time or current time but duration is always set to 0."""

    # We want to capture timestamps from lines like:
    #   2016-05-26 12:28:19,929 Serializer.ArchiveTypeResolver INFO : Processing assemblies on thread 5
    _TIMESTAMP_REGEX = r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"

    file = None
    first_valid_stamp = None
    last_valid_stamp = None
    try:
        file = open(filename, mode="r", encoding="iso_8859_1", errors="ignore")  # latin-1 encoding

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

    except IOError:
        pass
    finally:
        if file:
            file.close()

    if first_valid_stamp is None:
        start_time = get_file_datetime(filename)
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


def get_pamir_version_from_log(filename):
    """Get Pamir version information from log with given filename.
    Returns (version_short, version_full, revision) a tuple of strings."""
    # capture Pamir version information from lines like:
    # 2016-05-26 12:43:28,262 MiTek.Pamir INFO : Pamir 5.1.0 (Internal WIP 5.1.0.3149 (r70160)) starting
    # 2016-06-14 12:06:11,298 MiTek.Pamir INFO : Pamir 5.1.2 (5.1.2.38 (r70761)) starting
    # 2015-06-18 13:49:35,348 MiTek.Pamir INFO : Pamir 4.0.3 (56480) starting
    # 2017-02-18 04:46:49,967 MiTek.Pamir INFO : Pamir 5.3.11 (Internal WIP 5.3.11.34844 (r79586)) starting
 
    _PAMIR_VERSION_LINE_REGEX = r"Pamir (\d+.\d+.\d+) \((.+)\) start"

    version_short = ""
    version_full = ""
    revision = 0

    file = None
    try:
        file = open(filename, mode="r", encoding="utf8", errors="ignore")

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
        try:
            match = re.search(r"\((.+)\)", version_full)
            if match:
                revision = int(re.sub("r", "", match.group(1)))
            else:
                revision = int(version_full)
        except ValueError:
            print("Error: failed to parse revision number from '{}'".format(version_full))
            revision = 0

    return version_short, version_full, revision


# ---------------------------------------------------------
# Model classes inc. TestResult
# ---------------------------------------------------------


class JSonLabels:
    """Magic strings for JSon export"""
    LABEL = "label"
    VALUE = "value"
    TYPE = "type"
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
    FILE_SIZE = "fileSize"
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
    AVERAGE_DESIGN = "AverageDesign"
    AVERAGE_CHECK = "AverageCheck"
    AVERAGE_BUILD = "AverageBuild"


class OpResultType(Enum):
    Unknown = 0
    Duration = 1
    FileSize = 2


class OpResult:
    """Result of an operation"""
    def __init__(self, label: str, value: int, type: OpResultType, source_line: str = ""):
        self.label = label
        self.value = value
        self.type = type
        self.source_line = source_line

    def to_seconds(self):
        """Assuming value is a duration in ms, returns value in seconds."""
        return self.value/1000.0

    def to_megabytes(self):
        """Assuming file_size is kilobytes, return value in megabytes"""
        if self.type != OpResultType.FileSize:
            print("to_megabytes called on an OpResult of type " + self.type)
        return self.value / 1024.0

    def to_json_object(self):
        """Convert this OpResult into an object tailored for json serialization."""
        json_dict = {
            JSonLabels.LABEL: self.label,
            JSonLabels.VALUE: self.value,
            JSonLabels.TYPE: self.type.name
        }
        return json_dict


class DurationOpResult(OpResult):
    def __init__(self, label: str, duration: int, source_line: str = ""):
        OpResult.__init__(self, label, duration, OpResultType.Duration, source_line)


class FileSizeOpResult(OpResult):
    def __init__(self, label: str, file_size: int, source_line: str = ""):
        OpResult.__init__(self, label, file_size, OpResultType.FileSize, source_line)


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
    """Get test machine data.
    Requires psutil and py-cpuinfo packages from PyPy:
    python -m pip install psutil
    python -m pip install py-cpuinfo"""
    # check if dependencies have been installed before running. give advice
    import importlib.util
    if not importlib.util.find_spec("psutil") or not importlib.util.find_spec("cpuinfo"):
        raise Exception(test_machine_from_host.__doc__)

    import platform
    from psutil import cpu_count, virtual_memory
    from cpuinfo import cpuinfo

    machine = TestMachine()
    machine.name = platform.node()
    machine.processor = cpuinfo.get_cpu_info()["brand"]
    machine.logical_cores = cpu_count()
    machine.operating_system = "{} {} ({})".format(platform.system(), platform.release(), platform.version())
    machine.memory = int(virtual_memory().total / (1024 * 1024))

    return machine


class TestResult:
    """Collected timing information for a test"""
    def __init__(self, test_label: str):
        self.op_results = {}  # type: Dict[str, OpResult]
        self.run_times = []
        # for JSon support
        self.label = test_label
        self.run_labels = []
        self.start_time = None  # datetime
        self.duration = 0  # milliseconds
        self.status = "pass"

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
            JSonLabels.STATUS: self.status,
        }

        for _, op in sorted(self.op_results.items(), key=lambda i: i[0]):
            json_op_results.append(op.to_json_object())

        if len(self.run_times) != 0:
            for key, runTime in enumerate(self.run_times):
                op = DurationOpResult(self.run_labels[key], sec_to_ms(runTime))
                json_op_results.append(op.to_json_object())

        return json_dict

    def sum_op_durations(self):
        """Return total ms for all contained operations (and run times)"""
        total_ms = 0

        for op_result in self.op_results.values():
            if op_result.type == OpResultType.Duration:
                total_ms += op_result.value

        for run_time in self.run_times:
            total_ms += run_time

        return total_ms

    def optional_timed_op_to_file(self, op_label, outfile):
        if op_label in self.op_results:
            print("{:.3f}".format(self.op_results[op_label].to_seconds()), file=outfile)

    def to_file(self, outfile):
        if _debug:
            print("{}".format(self.label), file=outfile)

        to_login = self.op_results[OpLabels.TO_LOGIN].to_seconds()
        to_main_form = self.op_results[OpLabels.TO_MAIN_FORM].to_seconds()
        print("{:.3f}\n{:.3f}".format(to_login, to_main_form), file=outfile)

        self.optional_timed_op_to_file(OpLabels.SELECT_METALWORK, outfile)

        if len(self.run_times) != 0:
            for runTime in self.run_times:
                print("{:.3f}".format(runTime), file=outfile)

        for op_label in [OpLabels.SAPPHIRE_REPORT,  # generating Sapphire Report
                         OpLabels.PAMIR_SHUTDOWN,
                         OpLabels.SAPPHIRE_SHUTDOWN,  # Sapphire reports viewer shutdown
                         OpLabels.TWENTY20_SHUTDOWN]:
            self.optional_timed_op_to_file(op_label, outfile)

        if OpLabels.FILE_SIZE in self.op_results:
            print("{:.3f}".format(self.op_results[OpLabels.FILE_SIZE].to_megabytes()), file=outfile)

        print("", file=outfile)  # new line to create a gap for next result


class TestSuiteRun:
    def __init__(self, suite_label: str, machine: TestMachine):
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
            if next_result.start_time is not None and next_result.start_time < self.start_time:
                self.start_time = next_result.start_time

            self.duration += next_result.duration

    def to_json_object(self):
        test_result_json = [r.to_json_object() for r in self.test_results]

        result = {
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
# These methods can have knowledge of the test folder structures
# ---------------------------------------------------------


def get_test_log_path(test_dir):
    return os.path.join(test_dir, "testrun.log")


def get_perf_log_path(test_dir):
    return os.path.join(test_dir, "data/pamir-perf.log")


def get_pamir_log_path(test_dir):
    return os.path.join(test_dir, "data/pamir.log")


def collect_tc_stopwatch_data(test_result, test_dir, stopwatch_ops=None):
    """Collect timing from the TestComplete Test logs for
    the startup and shutdown."""

    if stopwatch_ops is None:
        stopwatch_ops = {
            0: OpLabels.TO_LOGIN,
            1: OpLabels.TO_MAIN_FORM,
            2: OpLabels.PAMIR_SHUTDOWN,
        }

    filename = get_test_log_path(test_dir)
    lines = get_matching_lines_from_file(filename, "TC.Stopwatch")

    for idx, line in enumerate(lines):
        if idx in stopwatch_ops:
            op_result = DurationOpResult(stopwatch_ops[idx], milliseconds_from_stopwatch_line(line), line)
            test_result.add_op_result(op_result)

    return


def collect_pamir_start_and_duration(test_result, test_dir):
    """Use Pamir start and runtime to determine test duration."""
    start, duration = parse_start_and_duration_from_pamir_log(get_pamir_log_path(test_dir))
    test_result.start_time = start
    test_result.duration = duration
    return


def collect_file_size_for_test(test_result, filename):
    """Collect data from the TestComplete Test logs for
    the Pamir file size"""

    lines = get_matching_lines_from_file(filename, "Pamir job:")
    if len(lines) > 0:
        file_size = kilobytes_from_file_size_line(lines[0])
        result = FileSizeOpResult(OpLabels.FILE_SIZE, file_size, lines[0])
        test_result.add_op_result(result)

    return


def collect_build_info_from_test(base_path, test_label):
    """For test with given label under base_path, extract build information from Pamir log"""
    test_dir = test_dir_from_label(base_path, test_label)
    version_info = get_pamir_version_from_log(get_pamir_log_path(test_dir))
    return BuildInfo(version_info[0], version_info[1], version_info[2])


def collect_test_suite_run_data(test_suite_run: TestSuiteRun, base_path: str):
    """Collect information to populate a TestSuiteRun object. Call this after you've added all the test results."""
    normed_dir = os.path.normpath(base_path)
    test_suite_run.notes = "Test folder: {}".format(os.path.basename(normed_dir))

    if len(test_suite_run.test_results) > 0:
        test_suite_run.build_info = collect_build_info_from_test(base_path, test_suite_run.test_results[0].label)

    if not test_suite_run.calc_start_duration_from_tests():
        test_suite_run.startDateTime = get_file_datetime(base_path)

    pass

# ---------------------------------------------------------
#  Test collection routines and close support methods
# ---------------------------------------------------------


def single_perf_op_test_collector(test_dir, test_label, search_string, run_labels):
    test_result = TestResult(test_label)
    test_result.run_labels = run_labels

    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir)

    perf_log_file = get_perf_log_path(test_dir)

    lines = get_matching_lines_from_file(perf_log_file, search_string)
    for line in lines:
        test_result.run_times.append(get_total_time_from_perf_line(line))

    return test_result


def design_only_test_collector(test_dir, test_label, run_labels):
    return single_perf_op_test_collector(test_dir, test_label, "BuildDesign", run_labels)


def build_only_test_collector(test_dir, test_label, run_labels):
    return single_perf_op_test_collector(test_dir, test_label, "BuildFrame", run_labels)


def add_benchmark_run_times(test_result, tc_log_file, lines_to_parse=None):
    """Parse times from TC stopwatch lines relating to Benchmark Results.
    Default lines to parse are:
        * 4 = Paint.TotalTime
        * 6 = Refresh.AverageTime"""

    if lines_to_parse is None:
        lines_to_parse = [4, 6]

    lines = get_matching_lines_from_file(tc_log_file, "BenchmarkResults")

    for line_idx in lines_to_parse:
        test_result.run_times.append(seconds_from_stopwatch_line(lines[line_idx]))  #


def add_build_and_design_run_times(test_result, perf_log_file):
    """Collects build and design times, assuming these operations have been run successively from layout"""
    # total time of building all frames
    lines = get_matching_lines_from_file(perf_log_file, "BuildFrame")
    test_result.run_times.append(get_total_time_from_perf_line(lines[0]))

    # total time of designing all frames
    lines = get_matching_lines_from_file(perf_log_file, "BuildDesign")
    test_result.run_times.append(get_total_time_from_perf_line(lines[0]))


def calculate_average_run_time_minus_first(test_run: TestResult, label_to_match):
    '''Calculate the average run time of a set of operations with label matching <label_to_match>.
    Excludes first run which is assumed to have label <label_to_match>1'''

    run_time_to_ignore = label_to_match + "1"

    total_time = 0
    total_count = 0
    for i, time in enumerate(test_run.run_times):
        cur_label = test_run.run_labels[i]
        if cur_label == run_time_to_ignore:
            continue

        if label_to_match in cur_label:
            total_time += test_run.run_times[i]
            total_count += 1

    return round(total_time/total_count, 3) if total_count > 0 else 0


def add_average_result(test_run: TestResult, label_to_match, op_label):
    average_result = calculate_average_run_time_minus_first(test_run, label_to_match)
    test_run.add_op_result(DurationOpResult(op_label, sec_to_ms(average_result)))


def basic_design_test_collector(test_dir, test_label):
    run_labels = ["Design1", "Check1",
                  "Design2", "Check2",
                  "Design3", "Check3",
                  "Design4", "Check4",
                  "Design5", "Check5"]
    test_run = design_only_test_collector(test_dir, test_label, run_labels)

    add_average_result(test_run, "Design", OpLabels.AVERAGE_DESIGN)
    add_average_result(test_run, "Check", OpLabels.AVERAGE_CHECK)

    return test_run


def basic_build_test_collector(test_dir, test_label):
    run_labels = ["Build1", "Build2", "Build3", "Build4", "Build5",
                  "Build6", "Build7", "Build8", "Build9", "Build10"]
    test_run = build_only_test_collector(test_dir, test_label, run_labels)

    add_average_result(test_run, "Build", OpLabels.AVERAGE_BUILD)

    return test_run


def nav_trim_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["LayoutPaint", "Refresh", "ChangeAutoLevel", "TrimExtend"]

    perf_log_file = get_perf_log_path(test_dir)
    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir)

    # collect benchmark results
    tc_log_file = get_test_log_path(test_dir)
    add_benchmark_run_times(test_result, tc_log_file)

    # timings for other operations
    lines = get_matching_lines_from_file(perf_log_file, "Action.Execute\tComplete")
    test_result.run_times.append(search_seconds_from_perf_lines(lines, "Toggle automatic framing zone"))
    trim_time = search_seconds_from_perf_lines(lines, "Trim/Extend")
    if trim_time == 0.0:
        # format changed some time in V6.0
        trim_time = search_seconds_from_perf_lines(lines, "TrimExtendCommand")
    test_result.run_times.append(trim_time)

    return test_result


def benchmark_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["LayoutPaint", "Refresh"]

    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir)

    tc_log_file = get_test_log_path(test_dir)
    add_benchmark_run_times(test_result, tc_log_file)

    return test_result


def fr_file_size_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["Design"]

    tc_log_file = get_test_log_path(test_dir)
    perf_log_file = get_perf_log_path(test_dir)
    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir)

    # collect the total time of designing all frames from "Pamir-perf.log"
    lines = get_matching_lines_from_file(perf_log_file, "BuildDesign")
    test_result.run_times.append(get_total_time_from_perf_line(lines[0]))

    # collect file size of the saved Pamir job
    collect_file_size_for_test(test_result, tc_log_file)

    return test_result


def mono_to_duo_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["LayoutPaint", "Refresh", "Delete"]

    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir)

    # collect benchmark results
    tc_log_file = get_test_log_path(test_dir)
    add_benchmark_run_times(test_result, tc_log_file)

    # timings for other operations
    perf_log_file = get_perf_log_path(test_dir)
    lines = get_matching_lines_from_file(perf_log_file, "Action.Execute\tComplete")
    test_result.run_times.append(search_seconds_from_perf_lines(lines, "Delete"))

    return test_result


def frame_design_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["Design"]

    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir)

    # collect benchmark results - but only take design
    tc_log_file = get_test_log_path(test_dir)
    lines = get_matching_lines_from_file(tc_log_file, "BenchmarkResults")

    test_result.run_times.append(seconds_from_stopwatch_line(lines[11]))  # Design.AverageTime

    return test_result


def hip_to_hip_plus_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["Build", "Design", "LayoutPaint", "Refresh"]

    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir)

    perf_log_file = get_perf_log_path(test_dir)

    add_build_and_design_run_times(test_result, perf_log_file)

    # collect benchmark results
    tc_log_file = get_test_log_path(test_dir)
    add_benchmark_run_times(test_result, tc_log_file)

    # collect file size of the saved Pamir job
    collect_file_size_for_test(test_result, tc_log_file)

    return test_result


def uk_thousand_objects_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["LayoutPaint", "Refresh", "PaintZoomed", "RefreshZoomed"]

    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir)

    # collect benchmark results
    tc_log_file = get_test_log_path(test_dir)
    add_benchmark_run_times(test_result, tc_log_file, [4, 6, 14, 16])  # two runs

    return test_result


def output_pdf_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["PDFOutput", "FileSize"]

    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir)

    # collect the total time of rendering all output PDF pages from "Pamir-perf.log"
    perf_log_file = get_perf_log_path(test_dir)
    lines = get_matching_lines_from_file(perf_log_file, "Operation.OutputPrintManagerOp")
    test_result.run_times.append(seconds_from_perf_line(lines[0]))

    # collect file size of the saved Pamir job
    tc_log_file = get_test_log_path(test_dir)
    collect_file_size_for_test(test_result, tc_log_file)

    return test_result


def uk_disable_hanger_hip_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["Build", "Design"]

    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir)

    perf_log_file = get_perf_log_path(test_dir)
    add_build_and_design_run_times(test_result, perf_log_file)

    return test_result


def uk_enable_hanger_hip_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["Build", "Design"]

    metalwork_stopwatch_ops = {
        0: OpLabels.TO_LOGIN,
        1: OpLabels.TO_MAIN_FORM,
        2: OpLabels.SELECT_METALWORK,
        3: OpLabels.PAMIR_SHUTDOWN,
    }

    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir, metalwork_stopwatch_ops)

    perf_log_file = get_perf_log_path(test_dir)
    add_build_and_design_run_times(test_result, perf_log_file)

    tc_log_file = get_test_log_path(test_dir)
    collect_file_size_for_test(test_result, tc_log_file)

    return test_result


def multiple_design_case_test_collector(test_dir, test_label):
    run_labels = ["DesignUnlockedPlatesAllCases", "DesignUnlockedPlatesSingleCase",
                  "DesignLockedPlatesAllCases", "DesignLockedPlatesSingleCase"]
    return design_only_test_collector(test_dir, test_label, run_labels)


def frame_design_with_scab_test_collector(test_dir, test_label):
    run_labels = ["Design"]

    return design_only_test_collector(test_dir, test_label, run_labels)


def uk_open_and_save_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["Open", "Save"]

    collect_pamir_start_and_duration(test_result, test_dir)
    collect_tc_stopwatch_data(test_result, test_dir)

    perf_log_file = get_perf_log_path(test_dir)

    # collect the time for opening project
    lines = get_matching_lines_from_file(perf_log_file, "OpenProject\tComplete")
    test_result.run_times.append(seconds_from_perf_line(lines[0]))

    # collect the time for saving project
    lines = get_matching_lines_from_file(perf_log_file, "UI.SaveProjectOperation\tComplete")
    test_result.run_times.append(seconds_from_perf_line(lines[0]))

    return test_result


def full_sync_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)
    test_result.run_labels = ["Save", "FullSync"]

    collect_pamir_start_and_duration(test_result, test_dir)

    _twenty20_stopwatch_ops = {
        0: OpLabels.TO_LOGIN,
        1: OpLabels.TO_MAIN_FORM,
        2: OpLabels.PAMIR_SHUTDOWN,
        3: OpLabels.TWENTY20_SHUTDOWN,
    }

    collect_tc_stopwatch_data(test_result, test_dir, _twenty20_stopwatch_ops)

    perf_log_file = get_perf_log_path(test_dir)

    # timings for saving project
    lines = get_matching_lines_from_file(perf_log_file, "Saving\tComplete")
    test_result.run_times.append(seconds_from_perf_line(lines[0]))

    # timings for MBA Synchronise Operation
    lines = get_matching_lines_from_file(perf_log_file, "UI.MBASynchroniseOperation\tComplete")
    test_result.run_times.append(seconds_from_perf_line(lines[0]))

    return test_result


def sapphire_report_test_collector(test_dir, test_label):
    test_result = TestResult(test_label)

    _sapphire_stopwatch_ops = {
        0: OpLabels.TO_LOGIN,
        1: OpLabels.TO_MAIN_FORM,
        2: OpLabels.SAPPHIRE_REPORT,
        3: OpLabels.SAPPHIRE_SHUTDOWN,
        4: OpLabels.TWENTY20_SHUTDOWN,
    }

    collect_tc_stopwatch_data(test_result, test_dir, _sapphire_stopwatch_ops)

    # for Sapphire test we have no Pamir log so calculate start and duration from TC log
    tc_log_file = get_test_log_path(test_dir)
    test_result.start_time = get_file_datetime(tc_log_file)
    test_result.duration = test_result.sum_op_durations()

    return test_result


# ---------------------------------------------------------
# Main program
# ---------------------------------------------------------


def test_dir_from_label(base_path, test_label):
    return os.path.join(base_path, test_label)


def output_timings_to_txt_file(test_results, outfile):
    for td in test_results:
        if td is None:
            continue

        td.to_file(outfile)


def scrape_test_run(base_path, collector, test_label):
    """Collect data from extra test run"""
    test_dir = test_dir_from_label(base_path, test_label)

    if not os.path.exists(test_dir):
        return None

    return collector(test_dir, test_label)


def scrape_test_runs(base_path, out_filename, tests_to_scrape):
    global _output_file
    test_runs = []
    with open(os.path.join(base_path, out_filename), mode="w") as _output_file:
        for collector, label in tests_to_scrape:
            result = scrape_test_run(base_path, collector, label)
            if result is not None:
                test_runs.append(result)
        output_timings_to_txt_file(test_runs, _output_file)

    return test_runs


def main(base_path):
    # It might be worth checking file structure at this point and bailing out if we dont recognise test data.
    global _output_file
    machine = test_machine_from_host()

    test_suite_run = TestSuiteRun(_TEST_SUITE_LABEL, machine)

    basic_tests = [
        (basic_design_test_collector, "DPT1"),
        (basic_design_test_collector, "DPT2"),
        (basic_build_test_collector, "BBT3"),
    ]
    timing_array = scrape_test_runs(base_path, "baseline-results2.txt", basic_tests)

    extra_tests = [
        (nav_trim_test_collector, "NTT4"),
        (mono_to_duo_test_collector, "MDT5"),
        (frame_design_test_collector, "HD4_FDT6"),
        (frame_design_test_collector, "CHP_FDT10"),
        (hip_to_hip_plus_test_collector, "FR-HHT7"),
        (hip_to_hip_plus_test_collector, "UK-HHT8"),
        (benchmark_test_collector, "FR_LWS9"),
        (uk_thousand_objects_test_collector, "UK_TDOT17"),
        (benchmark_test_collector, "SW_FBMT11"),
        (benchmark_test_collector, "UK_HT1_FBMT12"),
        (output_pdf_test_collector, "ISOLA_PDF13"),
        (output_pdf_test_collector, "UK_LayoutPDF14"),
        (uk_disable_hanger_hip_test_collector, "UK-DISH15"),
        (uk_enable_hanger_hip_test_collector, "UK-ENAH16"),
        (fr_file_size_collector, "FR-MST18"),
        (fr_file_size_collector, "FR-SST19"),
        (fr_file_size_collector, "FR-DST20"),
        (uk_open_and_save_test_collector, "UK-OST21"),
        (multiple_design_case_test_collector, "T22-FR-MDC"),
        (frame_design_with_scab_test_collector, "T23-FR-SCAB"),
        (full_sync_test_collector, "UK-SYNC"),
        (sapphire_report_test_collector, "UK-SAREP"),
    ]
    timing_array2 = scrape_test_runs(base_path, "extra-results2.txt", extra_tests)

    timing_array.extend(timing_array2)
    for td in timing_array:
        test_suite_run.append_result(td)

    collect_test_suite_run_data(test_suite_run, base_path)
    test_suite_run.to_json_file(os.path.join(base_path, "results.json"))

if __name__ == "__main__":
    _base_path = os.getcwd()
    if len(sys.argv) > 1:
        _base_path = sys.argv[1]

    main(_base_path)
