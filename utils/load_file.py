import pandas as pd
from pathlib import Path


def load_file(file_path: str) -> pd.DataFrame:

    file_ext = Path(file_path).suffix.lower()
    
    try:
        if file_ext == '.csv':
            df = pd.read_csv(file_path, dtype=str)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path, dtype=str)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_ext}")

        return df        
    except Exception as e:
        print(f"Ошибка при загрузке файла: {e}")
        raise