import requests
import json


def main():
    url = "http://cscedev/Pamir/Trac/jsonrpc"
    headers = {'content-type': 'application/json'}

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
        status = decodedResponse[3]["status"]
        return (ticket_num, status)


    tnum, status = get_ticket_status(23688)
    print("{}, {}".format(tnum, status))

    tnum, status = get_ticket_status(12345)
    print("{}, {}".format(tnum, status))

    #assert response["result"] == "echome!"
    #assert response["jsonrpc"]
    #assert response["id"] == 0

if __name__ == "__main__":
    main()
