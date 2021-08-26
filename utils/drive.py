import gspread
import pandas as pd
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from styleframe import StyleFrame
from tqdm import tqdm

gc = gspread.service_account(filename="./sheets_secrets.json")

gauth = GoogleAuth()
if gauth.access_token_expired:
    gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)


def get_file(file_id, sheet_name):
    workbook = gc.open_by_key(file_id)
    worksheet = workbook.worksheet(sheet_name)
    return worksheet


def is_empty(cell):
    return pd.isna(cell) or pd.isnull(cell) or cell == "" or bool(cell) == False


def consolidate_push(file_id, source, identifier, sheet_name, file_name):
    cols = source.columns.to_list()
    cols_map = {cols[i]: i for i in range(len(cols))}
    master_worksheet = get_file(file_id, sheet_name)
    master_worksheet_df = pd.DataFrame(master_worksheet.get_all_records())
    for col in source.columns:
        if col not in master_worksheet_df.columns:
            master_worksheet_df[col] = ""
    for row in tqdm(zip(*source.to_dict("list").values()), "Merging Data", total=len(source)):
        if is_empty(row[cols_map[identifier]]):
            continue
        master_row: int = master_worksheet_df.index[
            master_worksheet_df[identifier] == row[cols_map[identifier]]
        ].tolist()[0]
        for col in master_worksheet_df.columns.tolist():
            if is_empty(master_worksheet_df.iloc[master_row][col]) and not is_empty(row[cols_map[col]]):
                master_worksheet_df.at[master_row, col] = row[cols_map[col]]
    StyleFrame(master_worksheet_df.fillna("")).to_excel(file_name, sheet_name="data").save()
    master_file = drive.CreateFile({"id": file_id})
    master_file.SetContentFile(file_name)
    master_file.Upload({"convert": True})
