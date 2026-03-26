import json
import time
import random
import pandas as pd
from pathlib import Path
from nalog_parser import NalogClient
from utils.save_result import save_result


class InnService:
    def __init__(self, client: NalogClient, output_result_file: str, output_data_file: str) -> None:
        self.client = client
        self.output_result_file = output_result_file
        self.output_data_file = output_data_file

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        result_df = df.copy()
        data_df = pd.DataFrame()
        
        result_df['response_status'] = None
        result_df['response_data'] = None
        result_df['error_message'] = None
        
        for idx, row in df.iterrows():            
            inn = row['inn']
            bik = row['bik']
            response = self.client.get_data(inn, bik)

            if response is not None:
                result_df.at[idx, 'response_status'] = 'success'
                result_df.at[idx, 'response_data'] = json.dumps(response, ensure_ascii=False)
                df = self.parse_data(response)
                data_df = pd.concat([data_df, df], ignore_index=True)
            else:
                result_df.at[idx, 'response_status'] = 'error'
                result_df.at[idx, 'error_message'] = 'Не удалось получить ответ от сервиса'

            save_result(data_df, self.output_data_file)
            save_result(result_df, self.output_result_file)
            time.sleep(random.randint(1, 10))

        save_result(self.format_df(data_df), self.output_data_file)
        return result_df
    
    def format_df(self, df: pd.DataFrame) -> pd.DataFrame:
        new_df = df[[
            'innPRS', 'bikPRS', 'status', 'DATABEGIN', 'NOMER', 'DATA',
            'KODOSNOV', 'SALDOENS', 'IFNS', 'BIK', 'DATABI'
        ]].fillna('')

        new_df['SALDOENS'] = new_df['SALDOENS'].apply(lambda s: s.strip())
        new_df = new_df.rename(columns={
            'INN': 'ИНН налогоплательщика',
            'NAIM': 'Наименование налогоплательщика',
            'IFNS': 'Код налогового органа',
            'DATA': 'Дата действующего приостановления операций по счетам',
            'DATABEGIN': 'Дата начала действия приостановления операций по счетам',  
            'BIK': 'БИК банка, в котором приостановлены операции',
            'NOMER': 'Номер действующего приостановления операций по счетам',
            'DATABI': 'Дата и время размещения информации в сервисе (Мск)',
            'KODOSNOV': 'Код основания',
            'SALDOENS': 'Размер отрицательного сальдо ЕНС*, руб.коп'
        })

        return new_df

    def parse_data(self, data) -> pd.DataFrame:
        if 'rows' in data:
            df = pd.DataFrame(data['rows'])
            df['status'] = 'Присутствуют'
        else:
            df = pd.DataFrame([{
                'R': '-',
                'INN': '-',
                'NAIM': '-',
                'IFNS': '-',
                'DATA': '-',
                'DATABEGIN': '-',
                'BIK': '-',
                'NOMER': '-',
                'DATABI': '-',
                'KODOSNOV': '-',
                'TOKEN': '-',
                'ID': '-'
            }])
            df['status'] = 'Отсутствуют'
    
        df['innPRS'] = data['innPRS']
        df['bikPRS'] = data['bikPRS']
        return df
