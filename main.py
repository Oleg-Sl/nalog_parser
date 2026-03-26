from utils.load_file import load_file
from utils.save_result import save_result
from nalog_parser import NalogClient
from inn_service import InnService


def main():
    INPUT_FILE = "input_data.csv"
    OUTPUT_DATA_FILE = "output_data.xlsx"
    
    REQUIRED_COLUMNS = ['inn', 'bik']
    
    try:
        df = load_file(INPUT_FILE)
        
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            print(f"В файле отсутствуют необходимые столбцы: {missing_cols}")
            return
        
        client = NalogClient()
        service = InnService(client, INPUT_FILE, OUTPUT_DATA_FILE)
        service.process()

    except Exception as e:
        print(f"Ошибка в процессе обработки: {e}")
        raise


if __name__ == "__main__":
    main()
