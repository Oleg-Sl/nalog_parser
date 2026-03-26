from utils.load_file import load_file
from utils.save_result import save_result
from nalog_parser import NalogClient
from inn_service import InnService


def main():
    INPUT_FILE = "input_data.csv"
    OUTPUT_RESULT_FILE = "output_results.xlsx"
    OUTPUT_DATA_FILE = "output_data.xlsx"
    
    REQUIRED_COLUMNS = ['inn', 'bik']
    
    try:
        df = load_file(INPUT_FILE)
        
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            print(f"В файле отсутствуют необходимые столбцы: {missing_cols}")
            return
        
        client = NalogClient()
        service = InnService(client, OUTPUT_RESULT_FILE, OUTPUT_DATA_FILE)
        result_df = service.process(df)

        success_count = result_df[result_df['response_status'] == 'success'].shape[0]
        error_count = result_df[result_df['response_status'] == 'error'].shape[0]

        print(f"Обработка завершена!")
        print(f"Успешно: {success_count}")
        print(f"С ошибками: {error_count}")
    except Exception as e:
        print(f"Ошибка в процессе обработки: {e}")
        raise


if __name__ == "__main__":
    main()