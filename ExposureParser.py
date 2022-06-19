import json
import logging
from enum import Enum
from datetime import datetime

LOGGER_NAME_PARSER = "ExposureParser"


class Operations(Enum):
    REGISTER = "InvoiceRegistered"
    FEE_REGISTER = "LateFeeRegistered"
    PAYMENT_REGISTER = "PaymentRegistered"


class Parser:

    def __init__(self):

        self.messages = set()

        self.invoice_string = "invoiceId"
        self.amount_string = "amount"
        self.event_type_string = "eventType"
        self.timestamp_string = "timestamp"

        self.logger = logging.getLogger(LOGGER_NAME_PARSER)

    def __parse_month(self, timestamp: str) -> int:
        '''
        Parses a timestamp into a month
        :param timestamp: timestamp
        :return: the month represented by the string or -1 if it is wrong format or year
        '''
        parts = timestamp.split("T")
        if len(parts) != 2:
            return -1

        date = datetime.strptime(parts[0], '%Y-%m-%d')
        if date.year != 2022:
            return -1

        return date.month

    def parse_fields(self, json_input):
        '''
        Parses the json_input into usable invoice fields and checks for errors in json
        :param json_input: parsable json dictionary
        :return: exposure, op_type, invoice_id, month if available, otherwise None
        '''

        try:
            json_line = json.loads(json_input)
        except Exception:
            logging.warning(f"Skip, un-parsable {json_input}")
            return None

        if json_input in self.messages:
            logging.warning(f"Skip, resend {json_input}")
            return None

        self.messages.add(json_input)

        s1 = {self.amount_string, self.event_type_string, self.timestamp_string, self.invoice_string}

        if not s1.issubset(json_line.keys()):
            logging.warning(f"Skip, missing fields {json_line}")
            return None

        op_type = json_line[self.event_type_string]
        invoice_id = json_line[self.invoice_string]

        month = self.__parse_month(json_line[self.timestamp_string])

        try:
            exposure = float(json_line[self.amount_string])
        except TypeError:
            logging.warning(f"Skip, un-parsable amount {json_line[self.amount_string]}")
            return None

        if not op_type in set(item.value for item in Operations):
            logging.warning(f"Skip, undefined type {op_type}")
            return None

        if month == -1:
            logging.warning(f"Skip, error in date {json_line[self.timestamp_string]}")
            return None

        return exposure, op_type, invoice_id, month
