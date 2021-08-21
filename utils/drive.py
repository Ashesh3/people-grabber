import gspread
import pandas as pd

gc = gspread.service_account(filename="./client_secrets.json")


def get_file(file_id, sheet_name):
    workbook = gc.open_by_key(file_id)
    worksheet = workbook.worksheet(sheet_name)
    return worksheet


def is_empty(cell):
    return pd.isna(cell) or pd.isnull(cell) or cell == "" or bool(cell) == False


def consolidate_push(file_id, source, identifier, sheet_name):
    master_worksheet = get_file(file_id, sheet_name)
    master_worksheet_df = pd.DataFrame(master_worksheet.get_all_records())
    for _, row in source.iterrows():
        master_row: int = master_worksheet_df.index[master_worksheet_df[identifier] == row[identifier]].tolist()[0]
        for col in master_worksheet_df.columns.tolist():
            if is_empty(master_worksheet_df.iloc[master_row][col]) and not is_empty(row[col]):
                master_worksheet_df.at[master_row, col] = row[col]
    master_worksheet.update([master_worksheet_df.columns.values.tolist()] + master_worksheet_df.values.tolist())
