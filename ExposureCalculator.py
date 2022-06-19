import logging
import argparse
import matplotlib.pyplot as plt

from enum import Enum
from ExposureParser import Parser
from ExposureParser import Operations


LOGGER_NAME = "ExposureCalculator"


class Months(Enum):
    JAN = 1
    FEB = 2
    MAR = 3
    APR = 4
    MAJ = 5
    JUN = 6
    JUL = 7
    AUG = 8
    SEP = 9
    OCT = 10
    NOV = 11
    DEC = 12


class ExposureCalculator:

    def __init__(self, path: str):
        self.path = path
        self.peek_exposure_per_month = self.__init_monthly_dictionary()
        self.monthly_end_exposure = self.__init_monthly_dictionary()
        self.invoice_memory = {}
        self.exposure_parser = Parser()

        self.ignored_lines = 0
        self.current_exposure = 0

        #Variable used by matplotlib
        self.last_month = 0
        self.message_index = 0
        self.exposure_series = []
        self.month_series = []

        #String identifiers stored in variables
        self.invoice_exposure = "invoice_exposure"
        self.payed_exposure = "payed_exposure"

        self.graph_index = "graph_index"
        self.graph_month = "graph_month"

    @staticmethod
    def __init_monthly_dictionary():
        '''
        Creates a dictionary with monthly exposure intialized to 0
        :return:
        '''
        exposures = {}
        for month in Months:
            exposures[month.value] = float(0)
        return exposures

    def __invoice_register(self, exposure: float, month: int, invoice_id: str):
        '''
        Register an invoice, if the invoice already is in memory it will be discarded
        :param exposure:
        :param month:
        :param invoice_id:
        :return:
        '''

        if invoice_id in self.invoice_memory:
            return None

        self.current_exposure += exposure
        self.monthly_end_exposure[month] += exposure

        self.invoice_memory[invoice_id] = {
            self.invoice_exposure: exposure,
            self.payed_exposure: float(0)
        }

    def __late_fee_register(self, exposure: float, month: int, invoice_id: str):
        '''
        Add late fee exposure if invoice_id is available
        :param exposure:
        :param month:
        :param invoice_id:
        :return:
        '''

        if invoice_id in self.invoice_memory:
            self.current_exposure += exposure
            self.monthly_end_exposure[month] += exposure
            self.invoice_memory[invoice_id][self.invoice_exposure] += exposure

    def __payment_register(self, exposure: float, month: int, invoice_id: str):
        '''
        Register a payment if the invoice is present in the memory
        :param exposure:
        :param month:
        :param invoice_id:
        :return:
        '''
        if invoice_id in self.invoice_memory:
            self.invoice_memory[invoice_id][self.payed_exposure] += exposure
            payed = self.invoice_memory[invoice_id][self.payed_exposure]
            exposed = self.invoice_memory[invoice_id][self.invoice_exposure]

            # Depending on structure this could be a bug. If the systems allows multiple payment when
            # payed > exposed, the payment will always contribute to the current exposure
            if payed >= exposed:
                self.current_exposure -= payed
                self.monthly_end_exposure[month] -= payed

    def __updated_peek_exposure(self, month):
        '''
        Updates the peek exposure, should be called for each parased Json row
        :param month:
        :return:
        '''
        self.exposure_series.append(self.current_exposure)

        #Variables used by matplotlib
        self.message_index += 1
        if month != self.last_month:
            self.month_series.append({
                self.graph_index: self.message_index,
                self.graph_month: Months(month).name
            })
            self.last_month = month

        #Update peek-exposure
        if self.peek_exposure_per_month[month] < self.current_exposure:
            self.peek_exposure_per_month[month] = self.current_exposure

    def __parse_json_line(self, json_input):
        '''
        Parses a json dictionary, and performs action depending on operation type
        :param json_input: parsable json dictionary
        :return:
        '''
        parsed_value = self.exposure_parser.parse_fields(json_input=json_input)

        if parsed_value is not None:
            exposure, op_type, invoice_id, month = parsed_value
        else:
            self.ignored_lines += 1
            return None

        if op_type == Operations.REGISTER.value:
            self.__invoice_register(exposure=exposure,
                                    month=month,
                                    invoice_id=invoice_id)
        elif op_type == Operations.FEE_REGISTER.value:
            self.__late_fee_register(exposure=exposure,
                                     month=month,
                                     invoice_id=invoice_id)
        elif op_type == Operations.PAYMENT_REGISTER.value:
            self.__payment_register(exposure=exposure,
                                    month=month,
                                    invoice_id=invoice_id)
        else:
            logging.error("We have have some serious coding issues if this is reached...")
            exit(-1)

        self.__updated_peek_exposure(month=month)

    def __paint_graph(self):
        ticks = range(len(self.exposure_series))
        plt.plot(ticks, self.exposure_series)

        x_index = [v[self.graph_index] for v in self.month_series]
        x_label = [v[self.graph_month] for v in self.month_series]

        plt.xticks(x_index, x_label)
        plt.ylabel('Exposure amount')
        plt.xlabel('Inserts')
        plt.show()

    def parse_file(self):
        with open(self.path) as f:
            for json_line in f:
                self.__parse_json_line(json_input=json_line)

    def print_exposures(self):
        logging.info(f"Month\t Peek exposure\t End of month exposure")
        for month in Months:
            peek = round(self.peek_exposure_per_month[month.value], 2)
            end = round(self.monthly_end_exposure[month.value], 2)
            logging.info(f"{month.name}\t {peek}\t {end}")
        logging.info(f"Lines skipped: {self.ignored_lines}")
        self.__paint_graph()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger(LOGGER_NAME)

    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, help="Data path", required=True)

    args = parser.parse_args()

    calculator = ExposureCalculator(args.path)
    calculator.parse_file()
    calculator.print_exposures()
