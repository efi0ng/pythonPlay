import requests
import json
import csv

def main():
    url = "http://cscedev/Pamir/Trac/jsonrpc"
    headers = {'content-type': 'application/json'}
    TI_STATUS = "status"
    TI_TEAM = "team"
    TI_MILESTONE = "milestone"
    TI_ORDER = "order"
    TI_OWNER = "owner"
    TI_RESOLUTION = "resolution"

    payload = {
        "method": "ticket.get",
        "params": ["23688"],
        "jsonrpc": "2.0",
        "id": 0,
    }

    def get_ticket_status(ticket_num):
        payload["params"][0] = str(ticket_num)
        response = requests.post(
            url, data=json.dumps(payload), headers=headers, auth=('WebPerf', 'WebPerf'))

        decodedResponse = response.json()["result" ]
        ticket_num = decodedResponse[0]
        ticket_info = decodedResponse[3]

        sel_info = {}
        sel_info[TI_STATUS] = ticket_info["status"]
        sel_info[TI_TEAM] = ticket_info["scrum_team"]
        sel_info[TI_MILESTONE] = ticket_info["milestone"]
        sel_info[TI_ORDER] = ticket_info["scrum_prio"]
        sel_info[TI_OWNER] = ticket_info["owner"]
        sel_info[TI_RESOLUTION] = ticket_info["resolution"]

        return sel_info

    with open('RaisedTicketStatus.csv', 'w', newline='') as out_file:
        writer = csv.writer(out_file, delimiter=',')

        writer.writerow(['ex_id', 'ticket', 'status', 'team', 'owner', 'milestone', 'order', 'resolution'])

        with open("TicketsRaisedIds.csv", 'r') as csv_file:
            reader = csv.DictReader(csv_file, delimiter=',')

            for row in reader:
                ex_id = row['Id']
                ex_ticket = row['Ticket']

                ti = get_ticket_status(ex_ticket)
                writer.writerow([
                    ex_id, 
                    ex_ticket, 
                    ti[TI_STATUS], 
                    ti[TI_TEAM], 
                    ti[TI_MILESTONE],
                    ti[TI_ORDER], 
                    ti[TI_OWNER], 
                    ti[TI_RESOLUTION]])



if __name__ == "__main__":
    main()
