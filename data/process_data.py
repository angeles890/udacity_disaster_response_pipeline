import sys
import pandas as pd
import numpy as np
#import sqlite3
from sqlalchemy import create_engine


def load_data(messages_filepath, categories_filepath):
    '''
        Inputs:
            - str file path name of messages csv
            - str file path of categories csv
        Output: Returns merged dataframe of both messages and categories
            
    '''
    # read in csv
    messages = pd.read_csv(messages_filepath)
    categories = pd.read_csv(categories_filepath)
    # merge the two dataframes on id
    df = messages.merge(categories, how='inner',left_on = 'id', right_on = 'id')
    
    return df
    


def clean_data(df):
    '''
        Cleans dataframe
        Inputs:
            - Dataframe
        Output: Returns cleaned dataframe
    '''
    # create new df based on spliting of categories column from input df
    categories = df['categories'].str.split(';', expand = True)
    
    # get first row
    row = categories.loc[0:0]
    # get list of values
    category_colnames = row.values[0]
    # split each item in category_colnames and get first item 
    category_colnames = [col.split('-')[0] for col in category_colnames]
    
    # set df_categories column names
    categories.columns = category_colnames
    
    # clean values in category_colnames
    for column in categories:
        # set each value to be the last character of the string
        categories[column] = categories[column].apply(lambda col: col.split('-')[1])
        # convert column from string to numeric
        categories[column] = categories[column].astype(int)
    
    # create copy
    df_copy = df.copy()
    # on original input df, drop categories column
    df_copy.drop(columns=['categories'],inplace=True)
    # concat columnsf rom categories df
    df_copy = pd.concat([df_copy,categories],axis=1)
    # remove duplicates
    df_copy.drop_duplicates(inplace=True)
    
    # clean df to ensure only binary values
    # array to hold columns that should contain 2-values to support binary classification
    binary_columns = [c for c in df_copy.columns if c not in ['id','message','original','genre']]
    # list of allowed values
    allowed_vals = [0,1]
    # init list to hold columns that need more processesing
    require_attention_col = []
    # col that are not binary or have vals not allowed
    for col in binary_columns:
        # get set of unique vals in 'col'
        col_val_set = set(df_copy[col].unique().tolist())
        # get the difference in values found in 'col' and list of allowed values
        set_diff = col_val_set.difference(allowed_vals)
        # the difference should be 0 else, we need to clean the df based on the column
        if len(set_diff)>0:
            require_attention_col.append(col)
    # loop through each column that requires cleaning
    for col in require_attention_col:
        # call cleaning function and store result
        df_copy = filter_df_on_column(df_copy,col,allowed_vals)
    return df_copy

def filter_df_on_column(df,col,allowed_vals):
    '''
        Function will filter a dataframe based on provided column and return only rows that are in the allowed values list.
        Input:
        - df DataFrame: The dataframe to be filtered
        - col str: The name of the column that the function will review values for
        - allowed_vals List: A list containing the allowed values that can exist in col
        
        Return: 
        Dataframe consisting of records where the value in col exists within the allowed_vals list
    '''
    local_df = df.copy()
    local_df = local_df[local_df[col].isin(allowed_vals)]
    
    return local_df
    
    
def save_data(df, database_filename):
    '''
        Creates sql lite db and saves data frame to new db
        Inputs:
            - Dataframe to save to sqllite db
            - str file path of new db
        Output: None
    '''
    # create new sql engine object 'sqlite:///InsertDatabaseName.db'
    engine = create_engine(f'sqlite:///{database_filename}')
    # creates new table if not exists, and inserts all records from df_copy to new table
    # excluding index of dataframe
    df.to_sql('InsertTableName',engine,index=False,if_exists = 'replace')


def main():
    if len(sys.argv) == 4:

        messages_filepath, categories_filepath, database_filepath = sys.argv[1:]

        print('Loading data...\n    MESSAGES: {}\n    CATEGORIES: {}'
              .format(messages_filepath, categories_filepath))
        df = load_data(messages_filepath, categories_filepath)

        print('Cleaning data...')
        df = clean_data(df)
        
        print('Saving data...\n    DATABASE: {}'.format(database_filepath))
        save_data(df, database_filepath)
        
        print('Cleaned data saved to database!')
        print(database_filepath)
    else:
        print('Please provide the filepaths of the messages and categories '\
              'datasets as the first and second argument respectively, as '\
              'well as the filepath of the database to save the cleaned data '\
              'to as the third argument. \n\nExample: python process_data.py '\
              'disaster_messages.csv disaster_categories.csv '\
              'DisasterResponse.db')


if __name__ == '__main__':
    main()