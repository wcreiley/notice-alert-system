import os
import time
import shutil
import dotenv
import requests
import argparse
from bs4 import BeautifulSoup

class TCEnergy:

    providerPrefix = "TCEnergy"
    docBaseUrl = "https://ebb.anrpl.com/Notices/"
    noticesUrl = f"{docBaseUrl}Notices.asp"
    noticeTypes = ["Critical", "PlanSvcOut"]

    def fetch_data(self):

        for noticeType in self.noticeTypes:
            self.fetch_notice(noticeType)

    def fetch_notice(self, noticeType):
        params = {
            "sPipelineCode": "ANR",
            "sSubCategory": noticeType
        }
        print(f"TCEnergy Notices ({noticeType}) URL: {self.noticesUrl}")
        response = requests.get(url=self.noticesUrl, params=params)
        data = response.text

        soup = BeautifulSoup(data, 'html.parser')
        tableList = soup.find_all('table')

        if len(tableList) < 4:
            print("Error: No data found in the response.")
            return

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

        for result in parsedResults:

            noticeId = result['Notice ID']
            viewUrl = result['Notice Type Desc']

            filename = os.path.join("testData", f"{self.providerPrefix}_{noticeId}.html")

            if not os.path.exists(filename):
                docResponse = requests.get(url=self.docBaseUrl + viewUrl)
                print(f"Writing document for noticeId: {noticeId} to {filename}")
                with open(filename, "wb") as file:
                    file.write(docResponse.content)
            else:
                print(f"File already exists: {filename}")


class LngConfig:

    providerPrefix = "LngConfig"
    noticesUrl = "https://lngconnectionapi.cheniere.com/api/Notice/FilterNotices"

    docUrl = "https://lngconnectionapi.cheniere.com/api/Notice/Download"

    noticeTypes = ["9", "11"]

    def fetch_data(self):
        for noticeType in self.noticeTypes:
            self.fetch_notice(noticeType)

    def fetch_notice(self, noticeType):

        params = {
            "tspNo": "200",
            "pageId": noticeType,
            "noticeIdFrom": "-1",
            "noticeIdTo": "-1",
            "filter": "effective",
            "fromDate": "05/04/2020",
            "toDate": "05/06/2025"
        }
        print(f"LngConfig Notices ({noticeType}) URL: {self.noticesUrl}")
        response = requests.get(url=self.noticesUrl, params=params)

        data = response.json()

        for notice in data:
            noticeId = notice['noticeId']
            filename = os.path.join("testData", f"{self.providerPrefix}_{noticeId}.txt")

            if not os.path.exists(filename):
                docResponse = requests.get(url=self.docUrl, params={"tspNo": "200", "noticeId": noticeId})
                print(f"Writing document for noticeId: {noticeId} to {filename}")
                with open(filename, "wb") as file:
                    file.write(docResponse.content)
            else:
                print(f"File already exists: {filename}")

        return response.json()


class Ingest:

    def __init__(self):
        dotenv.load_dotenv()

        parser = argparse.ArgumentParser(description="Parse command-line arguments.")
        parser.add_argument("--testData", action="store_true", default=False, help="Test data flag")
        parser.add_argument("--sleep", type=int, default=10, help="Sleep time in seconds")
        args = parser.parse_args()

        self.test_data_flag = args.testData
        self.test_sleep = args.sleep

    def ingest_data(self):
        LngConfig().fetch_data()
        TCEnergy().fetch_data()


    def test_data(self):
        def interleave_arrays(arr1, arr2):
            # Interleave elements from both arrays
            interleaved = [item for pair in zip(arr1, arr2) for item in pair]

            # Add remaining elements from the longer array
            interleaved.extend(arr1[len(arr2):] if len(arr1) > len(arr2) else arr2[len(arr1):])

            return interleaved

        print("Testing data ingestion...")

        lng_files = [f for f in os.listdir("testData") if "lng" in f.lower() and os.path.isfile(os.path.join("testData", f))]
        tcenergy_files = [f for f in os.listdir("testData") if "tcenergy" in f.lower() and os.path.isfile(os.path.join("testData", f))]

        # Sort files by id
        sorted_lng_files = sorted(lng_files, key=lambda f: int(f.split("_")[1].split(".")[0]))
        sorted_tcenergy_files = sorted(tcenergy_files, key=lambda f: int(f.split("_")[1].split(".")[0]))

        for file in interleave_arrays(sorted_lng_files, sorted_tcenergy_files):
            print(f"Processing file: {file}")
            shutil.copy(f"testData/{file}", f"data/{file}")
            time.sleep(self.test_sleep)

    def run(self):
        print("Running Ingest...")

        if self.test_data_flag:
            self.test_data()
        else:
            self.ingest_data()


if __name__ == "__main__":
    Ingest().run()
