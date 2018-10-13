import csv


class ExceptionStats:
    def __init__(self):
        self.status = None
        self.owner = None
        self.count = 0
        self.hash = None

    def inc_count(self):
        self.count += 1


class ExceptionData:
    def __init__(self, ident):
        self.ident = ident
        self.prev_stats = ExceptionStats()
        self.curr_stats = ExceptionStats()
        self.status_changed = False;



exceptions = dict()


def should_skip(row: dict):
    """ Apply same filters as the report
    """
    if row['Region'] == "IGNORE":
        return True

    if row['VersionShort'] == "1" or row['VersionShort'] == "1.0":
        return True

    if '09/2014' in row['Date']:
        return True
    return False

def read_exc_from_file(ex_dict, filename, stat_getter):
    with open(filename, 'r') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',')

        for row in reader:
            if should_skip(row):
                continue

            ident = row['Id']
            row_ex = None
            if not ident in ex_dict:
                row_ex = ExceptionData(ident)
                ex_dict[ident] = row_ex
            else:
                row_ex = ex_dict[ident]

            # just override status and owner as we go
            stats = stat_getter(row_ex)
            stats.status = row['Status']
            stats.owner = row['Owner']
            stats.hash = row['Exception Hash']
            stats.inc_count()


def get_prev_stats(row_ex):
    return row_ex.prev_stats

def get_curr_stats(row_ex):
    return row_ex.curr_stats

# do initial count of exceptions
read_exc_from_file(exceptions, '20170526.csv', get_prev_stats)

# count current status values
read_exc_from_file(exceptions, '20170620.csv', get_curr_stats)

prev_total_count = 0
curr_total_count = 0
stat_changed_count = 0

with open('20170526-0620.csv', 'w', newline='') as csv_file:
    ex_writer = csv.writer(csv_file, delimiter=',')

    ex_writer.writerow(['id', 'old_owner', 'old_status', 'old_count', 'old_hash','new_owner', 'new_status', 'new_count', 'new_hash', 'status_changed'])

    for k, ex in exceptions.items():
        ex.status_changed = not (ex.prev_stats.status == ex.curr_stats.status)
        ex_writer.writerow([
            ex.ident,
            ex.prev_stats.owner, ex.prev_stats.status, ex.prev_stats.count, ex.prev_stats.hash,
            ex.curr_stats.owner, ex.curr_stats.status, ex.curr_stats.count, ex.curr_stats.hash,
            ex.status_changed
        ])
        prev_total_count += ex.prev_stats.count
        curr_total_count += ex.curr_stats.count
        if ex.status_changed:
            stat_changed_count += ex.curr_stats.count


print("Prev total count:",prev_total_count)
print("Curr total count:",curr_total_count)
print("Changed total count:",stat_changed_count)
