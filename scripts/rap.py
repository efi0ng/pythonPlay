#!/usr/bin/env python3
# Python script to autocomplete file copy.

# COULD DO: Bring download discovery into the app
# COULD DO: Loop until a specific key press (pick->copy->pick...)
# COULD DO: Refactor cursor stuff into class
# COULD DO: Package and compile

import argparse
import re
import getch
import os

CURSOR_UP_CMD = '\033[%sA'
CURSOR_DOWN_CMD = '\033[%sB'
CURSOR_FWD_CMD = '\033[%sC'
CURSOR_BACK_CMD = '\033[%sD'

def move_cursor_up(lines):
    print(CURSOR_UP_CMD % lines,end='',flush=True)

def move_cursor_down(lines):
    print(CURSOR_DOWN_CMD % lines,end='',flush=True)

def move_cursor_fwd(chars):
    print(CURSOR_FWD_CMD % chars,end='',flush=True)

def move_cursor_back(chars):
    print(CURSOR_BACK_CMD % chars,end='',flush=True)

def strip_date_candidate(parts):
    date = None
    matchLen = 0
    for i in range(0,len(parts)):
        if re.match(r'\d\d$', parts[i]):
            matchLen += 1
            if matchLen == 3:
                matched_slice = slice(i-2,i+1)
                date = "%s%s%s" % (parts[i-2],parts[i-1],parts[i])
                del parts[matched_slice]
                return (date, parts)
        else:
            matchLen = 0

    return (date, parts)


parser = argparse.ArgumentParser()
parser.add_argument('path',help='path to the file to copy')
parser.add_argument('extension',help='file extension',default='mp4',nargs="?")

args = parser.parse_args()

print("Path: " + args.path)
print("Extension: " + args.extension)

from pathlib import Path

srcPath = Path(args.path)
if not srcPath.is_dir():
    print("Path must point to a directory.")
    exit()

copyCandidates = list(srcPath.glob('*.'+args.extension))
if len(copyCandidates) > 1:
    print("Found %d possible files to copy. Can only copy one" % len(copyCandidates))
    exit()

fileToCopy = copyCandidates[0]

nameParts = srcPath.name.split(".")

(dateCandidate, autoCompleteParts) = strip_date_candidate(nameParts)

file_extension = args.extension
autoCompleteParts.insert(0,dateCandidate)
print(autoCompleteParts)
print(fileToCopy)

class InputState:
    def __init__(self):
        self.prompt="Filename >"
        self.suggested_completion = ""
        self.accepted_input = ""
        self.current_input = ""
        self.file_extension = ".mp4"

    def print_proposal(self):
        move_cursor_up(1)
        print("\r                                                 ", flush=True)
        print("\r                                                 ", end='',flush=True)
        move_cursor_up(1)
        print("\r[%s => %s]" % (self.current_input, self.suggested_completion))
        print("\r%s %s%s" % (self.prompt,self.accepted_input,self.suggested_completion), end='',flush=True)
        extra_chars = len(self.suggested_completion) - len(self.current_input)
        if extra_chars > 0:
            move_cursor_back(extra_chars)

    def accept_suggestion(self):
        self.accepted_input += self.suggested_completion
        self.current_input = ""
        self.suggested_completion = ""
        self.print_proposal()

    def delete_char(self):
        if len(self.current_input) > 0:
            self.current_input = self.current_input[:-1]
            self.suggested_completion = self.current_input
            self.print_proposal()
        elif len(self.accepted_input) > 0:
            self.accepted_input = self.accepted_input[:-1]
            self.print_proposal()


def add_hd(state):
    if "-HD." in state.accepted_input:
        return

    for part in autoCompleteParts:
        if "1080" in part:
            state.accepted_input += "-HD"
            break

def get_autocomplete(input):
    lcinput = input.lower();
    for part in autoCompleteParts:
        if part.lower().startswith(lcinput):
            return part
    return input

def execute_command(state):
    cmd = "rsync -ah --progress " + str(fileToCopy) + " " + state.accepted_input+state.file_extension;
    print(cmd)
    if input("Proceed? (y/_)> ") == "y":
        os.system(cmd)

def on_input(state, key):
    state.current_input += key
    state.suggested_completion = get_autocomplete(state.current_input)
    state.print_proposal()

def on_return(state):
    state.accepted_input += state.current_input
    add_hd(state)
    state.print_proposal()
    print("")

def on_separator(state, key):
    if len(state.suggested_completion) > 0:
        state.accept_suggestion()

    state.accepted_input += key
    state.print_proposal()

def on_tab(state):
    # accept suggestion
    state.accept_suggestion()

def on_delete(state):
    state.delete_char()

state = InputState()
state.file_extension = ".%s" % (file_extension)
state.print_proposal()
while True:
    ch = getch.getch()
    if ord(ch) == 27:
        # swallow arrow keys
        getch.getch()
        getch.getch()
    elif ord(ch) == 10:
        on_return(state)
        break;
    elif ord(ch) == 9 or ch == ' ':
        on_tab(state)
    elif ord(ch) == 127:
        on_delete(state)
    elif ch == '-' or ch=='.' or ch == '_':
        on_separator(state, ch)
    else:
        on_input(state, ch)

execute_command(state)
