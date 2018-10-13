#!/usr/bin/env python3
import sys
import os.path

""" boqXpander
eXpands a BOQ file into a human readable form.
"""

def proc_verbatim(parts, xboq_out):
    print(":".join(parts), file=xboq_out)


def proc_chamfer(parts, num, cham_start, xboq_out):
    print("    [Chamfer {}] From->To: {} -> {} | Front angle: {} | Back angle: {} | Dim active: {} | Dim from centre: {}"
        .format(num, parts[cham_start], parts[cham_start+1], parts[cham_start+2], parts[cham_start+3], parts[cham_start+4], parts[cham_start+5]),
        file=xboq_out)

MEMBER_MARK = 29
TRUSS_MARKS = 56

def proc_kap(parts, xboq_out):
    print("\nKAP for {}:{}".format(parts[TRUSS_MARKS], parts[MEMBER_MARK]), file=xboq_out)
    print("  CutID: {} | Joints: {} -> {} | Series: {} | Grade: {} | Size: {}x{}"
        .format(parts[1], parts[2], parts[3], parts[4], parts[5], parts[6], parts[7]), 
        file=xboq_out)
    print("  Total length: {} | Centre length: {} | Area: {}"
        .format(parts[8], parts[9], parts[10]),
        file=xboq_out)
    print("  Points 1-4: ({}, {}) ({}, {}) ({}, {}) ({}, {}) "
        .format(parts[11], parts[12], parts[13], parts[14], parts[15], parts[16], parts[17], parts[18]),
        file=xboq_out)
    print("  Points 5-8: ({}, {}) ({}, {}) ({}, {}) ({}, {}) "
        .format(parts[19], parts[20], parts[21], parts[22], parts[23], parts[24], parts[25], parts[26]),
        file=xboq_out)
    print("  Name: {} | Pieces: {} | Mark: {} | Gross length: {}"
        .format(parts[27], parts[28], parts[MEMBER_MARK], parts[30]),
        file=xboq_out)
    print("  No of Chamfers: {}"
        .format(parts[31]),
        file=xboq_out)

    num_chamfers = int(parts[31])

    for i in range(0, num_chamfers, 1):
        proc_chamfer(parts, i+1, 32+(i*6), xboq_out)

    print("  Trussmarks: {} | Pieces L: {} | Pieces R: {}"
        .format(parts[TRUSS_MARKS], parts[57], parts[58]),
        file=xboq_out)

    if (len(parts) < 61):
        return

    # Upper side help
    upperSideHelp = "(n/a)"
    if parts[59] == "1":
        upperSideHelp = "(4-5)"
    elif parts[59] == "2":
        upperSideHelp = "(8-1)"

    print("  Upper side: {} {} | Treatment: {}"
        .format(parts[59], upperSideHelp, parts[60]),
        file=xboq_out)

    if (len(parts) < 63):
        return

    print("  Reduce height => Offset 4-5: {} | Offset 8-1: {}"
        .format(parts[61],parts[62]),
       file=xboq_out)


def process_line_parts(parts, xboq_out, lineno):
    part_name_procs = {
        "VERSION" : proc_verbatim,
        "PRO_SIGN" : proc_verbatim,
        "PRO_ID" : proc_verbatim,
        "KAP" : proc_kap,
    }

    #TODO Check for error and report line number.
    if parts[0] in part_name_procs:
        part_name_procs[parts[0]](parts, xboq_out)
    else:
        proc_verbatim(parts, xboq_out)


def xpand_boq(boq_file, out_file):
    strip_str = lambda s: s.strip()

    with open(out_file, 'w',encoding='utf8') as xboq_out:
        with open(boq_file, 'r',encoding='latin_1') as boq_in:
            line = boq_in.readline()
            lineno = 1

            while line:
                parts = list(map(strip_str, line.split(":")))
                if len(parts) > 0:
                    process_line_parts(parts, xboq_out, lineno)
                else:
                    print("",file=boq_out)

                line = boq_in.readline()
                ++lineno


def main(boq_file, out_file):
    print("Using {} to create Xpanded file {}".format(boq_file, out_file))

    if not os.path.exists(boq_file):
        print("File '{}' does not exist.".format(boq_file))
        return

    xpand_boq(boq_file, out_file)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: {} <boq_file> <out_file>".format(sys.argv[0]))
        exit()

    boq_file = sys.argv[1] if sys.argv[1] != "-" else "CUTBILL.BOQ"
    out_file = sys.argv[2] if sys.argv[2] != "-" else "CUTBILL.XBOQ.TXT"
    main(boq_file, out_file)
