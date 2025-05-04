import asyncio
import os
from pprint import pprint
import dotenv
import requests

from bs4 import BeautifulSoup

class TCEnergy:

    providerPrefix = "TCEnergy"
    docBaseUrl = "https://ebb.anrpl.com/Notices/"
    noticesUrl = f"{docBaseUrl}Notices.asp"

    def fetch_data(self):
        params = {
            "sPipelineCode": "ANR",
            "sSubCategory": "Critical"
        }
        response = requests.get(url=self.noticesUrl, params=params)
        data = response.text
        print(f"TCEnergy Notices URL: {self.noticesUrl}")

        soup = BeautifulSoup(data, 'html.parser')
        tableList = soup.find_all('table')
        # Likely a better way to find the right table than the 4th one
        table = tableList[3]

        headers = [header.text for header in table.find_all('th')]
        results = [{headers[i]: cell for i, cell in enumerate(row.find_all('td'))}
                   for row in table.find_all('tr')]

        parsedResults = []
        for result in results:
            parsedResult = {}
            for key, value in result.items():
                link = value.find('a')
                if link is not None:
                    parsedResult[key] = link.attrs['href']
                else:
                    parsedResult[key] = value.text

            parsedResults.append(parsedResult) if len(parsedResult) > 1 else None

        # https://ebb.anrpl.com/Notices/NoticeView.asp?sPipelineCode=ANR&sSubCategory=Critical&sNoticeId=12347
        for result in parsedResults:

            noticeId = result['Notice ID']
            viewUrl = result['Notice Type Desc']

            filename = os.path.join("..", "data", f"{self.providerPrefix}_{noticeId}.html")

            if not os.path.exists(filename):
                docResponse = requests.get(url=self.docBaseUrl + viewUrl)
                print(f"Writing document for noticeId: {noticeId} to {filename}")
                with open(filename, "wb") as file:
                    file.write(docResponse.content)
            else:
                print(f"File already exists: {filename}")


class LngConfig:

    providerPrefix = "LngConfig"
    # url = "https://lngconnectionapi.cheniere.com/api/Notice/FilterNotices?tspNo=200&pageId=9&noticeIdFrom=-1&noticeIdTo=-1&filter=effective&fromDate=05/04/2024&toDate=05/04/2025"
    noticesUrl = "https://lngconnectionapi.cheniere.com/api/Notice/FilterNotices"
    # docUrl = "https://lngconnectionapi.cheniere.com/api/Notice/GetNoticeById?tspNo=200&noticeId=1475"
    # docUrl = "https://lngconnectionapi.cheniere.com/api/Notice/GetNoticeById"
    docUrl = "https://lngconnectionapi.cheniere.com/api/Notice/Download"

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
    }

    def fetch_data(self):

        params = {
            "tspNo": "200",
            "pageId": "9",
            "noticeIdFrom": "-1",
            "noticeIdTo": "-1",
            "filter": "effective",
            "fromDate": "05/04/2024",
            "toDate": "05/04/2025"
        }
        response = requests.get(url=self.noticesUrl, headers=self.headers, params=params)

        data = response.json()
        pprint(data[0]['noticeId'])

        for notice in data:
            noticeId = notice['noticeId']
            filename = os.path.join("..", "data", f"{self.providerPrefix}_{noticeId}.txt")

            if not os.path.exists(filename):
                docResponse = requests.get(url=self.docUrl, headers=self.headers, params={"tspNo": "200", "noticeId": noticeId})
                print(f"Writing document for noticeId: {noticeId} to {filename}")
                with open(filename, "wb") as file:
                    file.write(docResponse.content)
            else:
                print(f"File already exists: {filename}")

        return response.json()


class Ingest:

    def __init__(self):
        dotenv.load_dotenv()

    def run(self):
        print("Running Ingest...")
        data = LngConfig().fetch_data()
        data = TCEnergy().fetch_data()


if __name__ == "__main__":
    Ingest().run()
