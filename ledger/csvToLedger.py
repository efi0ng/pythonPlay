#! /usr/bin/env python3

# TODO Take filename as an argument
# TODO Make sure substitutions are case insensitive
# TODO Write out proper transactions

import csv
from datetime import datetime
import json


FIELD_NAMES = ['date', 'type', 'sortcode', 'account',
               'description', 'debit', 'credit', 'balance']
DATE_FORMAT = '%d/%m/%Y'
LEDGER_INDENT = '    '


class JSonFields:
    NO_MATCH = "no match"
    MATCH = 'match'
    DEBIT = 'debit'
    CREDIT = 'credit'
    SUBSTITUTIONS = 'substitutions'
    AMOUNT = 'amount'
    ACCOUNT = 'account'
    TRANSACTIONS = 'transactions'


class LedgerEntry:
    """There are at least two of these in a valid transaction."""

    def __init__(self, account, amount):
        self.acc = account
        self.amount = amount

    def write(self, outfile):
        if self.acc == "":
            return

        output_amt = "  "+str(self.amount) if self.amount is not None else ""
        line = "{}{}{}".format(LEDGER_INDENT, self.acc, output_amt)
        print(line, file=outfile)


class LedgerTransaction:
    """A ledger-compatible transaction"""
    def __init__(self, date, payee, tags=""):
        self.date = date
        self.payee = payee
        self.tags = tags
        self.entries = []

    def add_entry(self, entry):
        self.entries.append(entry)

    def write(self, outfile):
        date_string = datetime.strftime(self.date, DATE_FORMAT)
        print(date_string, self.payee, file=outfile)
        for entry in self.entries:
            entry.write(outfile)

        print(file=outfile)


class Ledger:
    """A collection of ledger transactions"""

    def __init__(self):
        self.txs = []

    def append(self, trans):
        self.txs.append(trans)

    def append_all(self, txs):
        for trans in txs:
            self.append(trans)

    def write(self, filename):
        with open(filename, 'w') as ledger_file:
            for trans in self.txs:
                trans.write(ledger_file)


class SubstitutionEngine:
    """Performs ledger substitutions based on an input file."""
    DEF_NOM_CR_ACC = "Income:no match"
    DEF_NOM_DEB_ACC = "Expenses:no match"

    def __init__(self):
        self.substitutions = []
        self.nom_cr_entry = None
        self.nom_deb_entry = None

    def load_no_matches(self, no_match_dict):
        nom_cr_acc = SubstitutionEngine.DEF_NOM_CR_ACC
        nom_deb_acc = SubstitutionEngine.DEF_NOM_DEB_ACC

        if no_match_dict is not None:
            if JSonFields.DEBIT in no_match_dict:
                nom_deb_acc = no_match_dict[JSonFields.DEBIT]

            if JSonFields.CREDIT in no_match_dict:
                nom_cr_acc = no_match_dict[JSonFields.CREDIT]

        self.nom_cr_entry = LedgerEntry(nom_cr_acc, None)
        self.nom_deb_entry = LedgerEntry(nom_deb_acc, None)

    def load(self, subs_file_path):
        json_dict = None
        with open(subs_file_path, 'r', encoding="utf8") as subs_file:
            json_dict = json.load(subs_file)

        self.load_no_matches(json_dict.get(JSonFields.NO_MATCH, None))

        if JSonFields.SUBSTITUTIONS in json_dict:
            self.substitutions = json_dict[JSonFields.SUBSTITUTIONS]

    def subst_acc(self, acc_name):
        """Look for a substitute account name. Return substitute if found.
        Return original otherwise."""
        return acc_name

    def get_targets(self, payee, amount):
        """Look for substitutions to create a valid target for
        the transaction."""
        targets = []
        temp = self.nom_deb_entry if amount < 0 else self.nom_cr_entry
        targets.append(temp)
        return targets


class CsvTransaction:
    """A single transaction for a bank account"""

    def __init__(self):
        self.date = None
        self.category = None
        self.bank_account = None
        self.desc = None
        self.amount = 0
        self.balance = 0
        self.ledger = None

    def set_acc_from_sc_accnum(self, sort_code, acc_num):
        # Note we drop first char of sortcode 'cos Lloyds outputs a quote mark
        self.bank_account = sort_code[1:] + " " + acc_num

    def set_amt_deb_cred(self, debit, credit):
        if len(debit) > 0:
            self.amount = -float(debit)
        elif len(credit) > 0:
            self.amount = float(credit)
        else:
            self.amount = 0

    def getDate(self):
        return self.date

    def isDebit(self):
        return self.amount <= 0


def readBankingCSV(csv_path):
    transactions = []
    with open(csv_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile, fieldnames=FIELD_NAMES, delimiter=',')
        for row in reader:
            try:
                rowDate = datetime.strptime(row['date'], DATE_FORMAT)
            except ValueError:
                rowDate = 0

            if rowDate == 0:
                continue

            trans = CsvTransaction()
            trans.date = rowDate
            trans.category = row['type']
            trans.desc = row['description']
            trans.balance = float(row['balance'])
            trans.set_acc_from_sc_accnum(row['sortcode'], row['account'])
            trans.set_amt_deb_cred(row['debit'], row['credit'])

            transactions.append(trans)

    transactions.sort(key=CsvTransaction.getDate)
    return transactions


def convert_to_ledger(transactions, subs_engine):
    ledger_trans = []
    for trans in transactions:
        ledger_t = LedgerTransaction(trans.date, trans.desc)

        src_acc = subs_engine.subst_acc(trans.bank_account)
        src_entry = LedgerEntry(src_acc, trans.amount)
        ledger_t.add_entry(src_entry)

        targets = subs_engine.get_targets(trans.desc, trans.amount)
        for target in targets:
            ledger_t.add_entry(target)

        ledger_trans.append(ledger_t)

    return ledger_trans


def debug_print_transactions(transactions):
    for trans in transactions:
        dateString = datetime.strftime(trans.date, DATE_FORMAT)
        print("{} {} {} {}".format(dateString, trans.bank_account,
                                   trans.desc, trans.amount))


def format_acc_line(account, amount):
    output_amount = "  "+str(amount) if amount is not None else ""
    return "{}{}{}".format(LEDGER_INDENT, account, output_amount)


def write_csv_as_ledger(trans, out_file):
    date_string = datetime.strftime(trans.date, DATE_FORMAT)
    print(date_string, trans.desc, file=out_file)
    line = format_acc_line(trans.bank_account, trans.amount)
    print(line, file=out_file)
    print(file=out_file)


def write_csv_ledger_file(transactions, ledger_path):
    with open(ledger_path, 'w') as ledger_file:
        for trans in transactions:
            write_csv_as_ledger(trans, ledger_file)


def main(csv_path, subs_path, ledger_path):
    ledger = Ledger()
    subs = SubstitutionEngine()
    subs.load(subs_path)
    all_csv_trans = readBankingCSV(csv_path)
    ledger_trans = convert_to_ledger(all_csv_trans, subs)
    ledger.append_all(ledger_trans)
    ledger.write(ledger_path)


main("./csv/170103-170201.csv", "./substitutions.json", "./testLedger.dat")
