import os
import json
import time
import random
import pandas as pd
from pathlib import Path
from nalog_parser import NalogClient
from utils.save_result import save_result


class InnService:
    def __init__(self, client: NalogClient, input_file: str, output_data_file: str) -> None:
        self.client = client
        self.input_file = input_file
        self.output_data_file = output_data_file

    def process(self):
        if self.input_file.endswith('.csv'):
            df = pd.read_csv(self.input_file, dtype=str)
        else:
            df = pd.read_excel(self.input_file, dtype=str)

        for col in ['status', 'message', 'data']:
            if col not in df.columns:
                df[col] = None

        data_buffer = []
        processed_count = 0 
        save_interval = 20

        try:
            for idx, row in df.iterrows():
                if pd.notna(row['status']) and str(row['status']).strip() != "":
                    continue

                inn = str(row['inn']).strip()
                bik = str(row['bik']).strip()
                inn = inn.zfill(10) if len(inn) <= 10 else inn.zfill(12)

                status = None
                try:
                    response = self.client.get_data(inn, bik)
                    
                    df.at[idx, 'status'] = response['status']
                    df.at[idx, 'message'] = response['message']
                    df.at[idx, 'data'] = str(response['data'])
                    status = response['status']

                    if response['status'] == 'success':
                        raw_parsed = self.parse_data(response['data'])
                        formatted_data = self.format_df(raw_parsed)
                        data_buffer.append(formatted_data)
                        # self._update_file(formatted_data, self.output_data_file)

                except Exception as e:
                    df.at[idx, 'status'] = 'error'
                    df.at[idx, 'message'] = str(e)
                    df.at[idx, 'data'] = ''

                processed_count += 1
                print(f"[{idx+1}/{len(df)}] {inn} -> {status}")

                if processed_count % save_interval == 0:
                    self._save_input_file(df)
                    if data_buffer:
                        combined_new_data = pd.concat(data_buffer, ignore_index=True)
                        self._update_file(combined_new_data, self.output_data_file)
                        data_buffer = []
                
                time.sleep(random.randint(4, 15))

        finally:
            self._save_input_file(df)
            if data_buffer:
                combined_new_data = pd.concat(data_buffer, ignore_index=True)
                self._update_file(combined_new_data, self.output_data_file)

    def _save_input_file(self, df: pd.DataFrame):
        if self.input_file.endswith('.csv'):
            df.to_csv(self.input_file, index=False, encoding='utf-8-sig')
        else:
            df.to_excel(self.input_file, index=False)

    def _update_file(self, new_data: pd.DataFrame, file_path: str):
        if new_data.empty:
            return

        if os.path.exists(file_path):
            try:
                if file_path.endswith('.csv'):
                    existing_df = pd.read_csv(file_path, dtype=str)
                else:
                    existing_df = pd.read_excel(file_path, dtype=str)
                
                updated_df = pd.concat([existing_df, new_data], ignore_index=True)
            except Exception as e:
                updated_df = new_data
        else:
            updated_df = new_data

        if file_path.endswith('.csv'):
            updated_df.to_csv(file_path, index=False, encoding='utf-8-sig')
        else:
            updated_df.to_excel(file_path, index=False)

    def parse_data(self, data: dict) -> pd.DataFrame:
        inn_prs = data.get('innPRS', '')
        bik_prs = data.get('bikPRS', '')
        
        if 'rows' in data and data['rows']:
            df = pd.DataFrame(data['rows'])
            df['status'] = 'Присутствуют'
        else:
            df = pd.DataFrame([{
                'INN': inn_prs,
                'NAIM': '-',
                'IFNS': '-',
                'DATA': '-',
                'DATABEGIN': '-',
                'BIK': '-',
                'NOMER': '-',
                'DATABI': '-',
                'KODOSNOV': '-',
                'SALDOENS': '-'
            }])
            df['status'] = 'Отсутствуют'
    
        df['innPRS'] = inn_prs
        df['bikPRS'] = bik_prs
        return df

    def format_df(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = [
            'innPRS', 'bikPRS', 'status', 'DATABEGIN', 'NOMER', 'DATA',
            'KODOSNOV', 'SALDOENS', 'IFNS', 'BIK', 'DATABI'
        ]

        new_df = df[required_cols].fillna('')

        new_df['SALDOENS'] = new_df['SALDOENS'].astype(str).str.strip()
        
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
