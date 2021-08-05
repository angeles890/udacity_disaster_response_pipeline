# import libraries
import sys
import pandas as pd
import numpy as np
import sqlite3
from sqlalchemy import create_engine
import nltk
import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem.wordnet import WordNetLemmatizer
from sklearn.model_selection import train_test_split
#from sklearn.metrics import accuracy_score
#from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
#from sklearn import model_selection
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.ensemble import RandomForestClassifier 
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import VotingClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import fbeta_score, make_scorer
from sklearn.pipeline import Pipeline
import joblib
import pickle
nltk.download(['punkt', 'wordnet', 'averaged_perceptron_tagger','stopwords'])
#!conda install scikit-learn=0.20
# in terminal pip install --upgrade scikit-learn


def load_data(database_filepath):
    """
        Loads data from sqllite db 
        Args:
        database_filepath str: path to db
        Returns:
        X dataframe: The independent variables for model development
        Y dataframe: Class labels
        y_category list: list of str, representing the unique columns from the Y dataframe
    """
    # load data from database 'sqlite:///InsertDatabaseName.db'
    engine = create_engine(f'sqlite:///{database_filepath}')
    # read from SQL table with conn = engine
    df = pd.read_sql("Select * From InsertTableName",engine)
    # create copy
    df_copy = df.copy()
    # set X to message column
    X = df_copy['message']
    # drop unused columns
    Y = df_copy.drop(columns=['message', 'genre', 'id', 'original'],axis=1)
    # convert columns of Y to list
    y_category = Y.columns.tolist()
    
    return X, Y,y_category


def tokenize(text):
    """
    Tokenizes text data
    Args:
    text str: Messages as text data
    Returns:
    words list: Processed text after normalizing, tokenizing and lemmatizing
    """
    # Normalize text
    text = re.sub(r"[^a-zA-Z0-9]", " ", text.lower())
    
    # tokenize text
    words = word_tokenize(text)
    
    # remove stop words
    stop_words = stopwords.words("english")
    words = [word for word in words if word not in stop_words]
    
    # extract root form of words
    words = [WordNetLemmatizer().lemmatize(word) for word in words]

    return words


def build_model():
    """
        Creates Pipeline obj to support model development, and tunes model via GridSearchCV
        Args:
        None
        Returns:
        cv GridSearchCV: GridSearchCV object
    """
    # init RandomForest classifier with 'balanced' class weight to control for class inbalances
    rf = RandomForestClassifier(class_weight='balanced')
    # define pipeline
    pipeline = Pipeline([
        ('vect',CountVectorizer(tokenizer=tokenize,min_df=0.05)),
        ('tfidf',TfidfTransformer()),
        ('clf',MultiOutputClassifier(rf))
    ])
    
    # test different values for hyper params
    parameters = {  'vect__max_df': (0.90, .95),
                  'vect__ngram_range': [(1,2)],
                  'clf__estimator__min_samples_split': [2, 5]
      }
    # fbeta_score scoring object using make_scorer()
    scorer = make_scorer (f1_scorer_eval)
    cv = GridSearchCV (pipeline, param_grid= parameters, scoring = scorer, verbose =5,cv=4 )

    return cv


def f1_scorer_eval (y_true, y_pred):
    """A function that measures mean of F1 for all classes
       Returns an average value of F1 for sake of evaluation whether model predicts better or worse in GridSearchCV
    """
    #converting y_pred from np.array to pd.dataframe
    #keep in mind that y_pred should a pd.dataframe rather than np.array
    y_pred = pd.DataFrame (y_pred, columns = y_true.columns)


    #instantiating a dataframe
    report = pd.DataFrame ()

    for col in y_true.columns:
        #returning dictionary from classification report
        class_dict = classification_report (output_dict = True, y_true = y_true.loc [:,col], y_pred = y_pred.loc [:,col])

        #converting from dictionary to dataframe
        eval_df = pd.DataFrame (pd.DataFrame.from_dict (class_dict))

        #dropping unnecessary columns
        eval_df.drop(['macro avg', 'weighted avg'], axis =1, inplace = True)

        #dropping unnecessary row "support"
        eval_df.drop(index = 'support', inplace = True)

        #calculating mean values
        av_eval_df = pd.DataFrame (eval_df.transpose ().mean ())

        #transposing columns to rows and vice versa
        av_eval_df = av_eval_df.transpose ()

        #appending result to report df
        report = report.append (av_eval_df, ignore_index = True)

    #returining mean value for all classes. since it's used for GridSearch we may use mean
    #as the overall value of F1 should grow.
    return report ['f1-score'].mean ()



def evaluate_model(y_test,y_pred):
    '''
        Creates an easy to read report of model performance
        Args: 
        - y_test DataFrame 
        - y_pred DataFrame
        Returns:
        report DataFrame: Easy to read dataframe showing model classification results
    '''
    # init empty dataFrame
    report = pd.DataFrame ()
    # loop through each column in Y matrix
    for col in y_test.columns.tolist():
        # create classifcation report for each y in Y
        class_report_dict = classification_report(y_true = y_test.loc[:,col],y_pred = y_pred.loc[:,col],output_dict = True)
        # convert dict to df
        df_eval = pd.DataFrame.from_dict(class_report_dict)
        # remove unused columns
        df_eval.drop(columns = ['macro avg', 'weighted avg'], inplace=True)
        df_eval.drop(index='support',inplace=True)
        # get avg scores
        avg_df_eval = pd.DataFrame(df_eval.transpose().mean())
        # tranpose
        avg_df_eval = avg_df_eval.transpose()
        # append new item
        report = report.append(avg_df_eval, ignore_index=True)
    # set index of new df to columns in Y
    report.index = y_test.columns
    return report 


def save_model(model, model_filepath):
    """
        Saves the model to a Python pickle file    
        Args:
        model: Trained model
        model_filepath: Filepath to save the model
    """
    # save model to pickle file
    #pickle.dump(model, open(model_filepath, 'wb',encoding='UTF-8'))
    with open(model_filepath, 'wb') as f:
        pickle.dump(model.best_estimator_, f)


def main():
    if len(sys.argv) == 3:
        database_filepath, model_filepath = sys.argv[1:]
        print('Loading data...\n    DATABASE: {}'.format(database_filepath))
        X, Y, category_names = load_data(database_filepath)
        # remove Y columns that are all 0
        Y = Y.loc[:,(Y!=0).any(axis=0)]
        category_names = [y for y in category_names if y in Y.columns]
        # split data into training and testing
        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2)
        
        print('Building model...')
        model = build_model()
        
        print('Training model...')
        # fit model
        model.fit(X_train, Y_train)
        # use fitted model to test predictions on testing data
        y_pred = model.predict(X_test)
        print('Evaluating model...')
        # eval model
        evaluate_model(Y_test,pd.DataFrame(y_pred,columns=category_names))

        print('Saving model...\n    MODEL: {}'.format(model_filepath))
        # save model
        save_model(model, model_filepath)

        print('Trained model saved!')

    else:
        print('Please provide the filepath of the disaster messages database '\
              'as the first argument and the filepath of the pickle file to '\
              'save the model to as the second argument. \n\nExample: python '\
              'train_classifier.py ../data/DisasterResponse.db classifier.pkl')


if __name__ == '__main__':
    main()