from futu import OpenQuoteContext, RET_OK
from pprint import pprint
import os
from utils.logger import logger

FUTUOPEND_ADDRESS = '127.0.0.1'  
FUTUOPEND_PORT = 11111  

def request_history_kline(code, start=None, end=None, ktype='K_DAY', autype='qfq'):
    logger.info(f'request history kline, code: {code}, start: {start}, end: {end}, ktype: {ktype}, autype: {autype}')
    quote_ctx = OpenQuoteContext(host=FUTUOPEND_ADDRESS, port=FUTUOPEND_PORT)
    ret, data, page_req_key = quote_ctx.request_history_kline(code, start=start, end=end, ktype=ktype, autype=autype)  
    if ret == RET_OK:
        logger.info(f'get data success, name: {data['name'][0]}, code: {data['code'][0]}, count: {len(data)}')
    else:
        logger.error(f'get data error, msg: {data}')
    quote_ctx.close()
    return data

if __name__ == '__main__':
    CACHE_DIR = 'cache/futu'
    os.makedirs(CACHE_DIR, exist_ok=True)
    from utils.file import write_csv

    code_name = 'HK.09988'
    start_date = '2024-08-15'
    end_date = '2025-08-15'
    data = request_history_kline(code_name, start=start_date, end=end_date)
    pprint(data.info())
    write_csv(data, f'{CACHE_DIR}/{code_name.replace(".", "_")}_{start_date}_{end_date}.csv')
