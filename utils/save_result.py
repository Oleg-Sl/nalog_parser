import pandas as pd
from pathlib import Path


def save_result(df: pd.DataFrame, output_path: str):
    file_ext = Path(output_path).suffix.lower()
    
    try:
        if file_ext == '.csv':
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        elif file_ext in ['.xlsx', '.xls']:
            df.to_excel(output_path, index=False)
        else:
            raise ValueError(f"Неподдерживаемый формат для сохранения: {file_ext}")
    except Exception as e:
        print(f"Ошибка при сохранении файла: {e}")
        raise
