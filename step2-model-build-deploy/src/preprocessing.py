"""
Preprocessing functions for customer segmentation model.
Extracted from the original notebook for reusability.
"""

import pandas as pd
import numpy as np


def calculate_derived_features(df):
    """
    Calculate specific derived features for customer segmentation.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with columns: Customer_ID, Age, Income, Purchases, Gender

    Returns:
    --------
    pandas.DataFrame
        DataFrame with original columns plus derived features
    """
    # Create a copy
    df_derived = df.copy()

    # AGE-BASED DERIVED FEATURES
    df_derived['Is_Young_Adult'] = (df_derived['Age'] <= 30).astype(int)
    df_derived['Is_Middle_Aged'] = ((df_derived['Age'] > 30) & (df_derived['Age'] <= 50)).astype(int)
    df_derived['Is_Senior'] = (df_derived['Age'] > 50).astype(int)

    # GENDER-BASED DERIVED FEATURES
    df_derived['IS_MALE'] = (df_derived['Gender'] == 'Male').astype(int)

    # INCOME-BASED DERIVED FEATURES
    income_quartile_temp = pd.qcut(
        df_derived['Income'],
        q=4,
        labels=['Q1_Low', 'Q2_Medium_Low', 'Q3_Medium_High', 'Q4_High']
    )

    # One-hot encode Income_Quartile (drop_first=True to avoid multicollinearity)
    income_quartile_dummies = pd.get_dummies(income_quartile_temp, prefix='Income_Quartile', drop_first=True, dtype=int)
    df_derived = pd.concat([df_derived, income_quartile_dummies], axis=1)

    # Income_Age_Ratio: Income divided by age
    df_derived['Income_Age_Ratio'] = df_derived['Income'] / df_derived['Age']

    # PURCHASE-BASED DERIVED FEATURES
    purchase_quartile_temp = pd.qcut(
        df_derived['Purchases'],
        q=4,
        labels=['Q1_Low', 'Q2_Medium_Low', 'Q3_Medium_High', 'Q4_High']
    )

    # One-hot encode Purchase_Quartile (drop_first=True to avoid multicollinearity)
    purchase_quartile_dummies = pd.get_dummies(purchase_quartile_temp, prefix='Purchase_Quartile', drop_first=True, dtype=int)
    df_derived = pd.concat([df_derived, purchase_quartile_dummies], axis=1)

    # Purchase_Intensity: Normalized purchase frequency (0-1 scale)
    max_purchases = df_derived['Purchases'].max()
    df_derived['Purchase_Intensity'] = df_derived['Purchases'] / max_purchases

    # INTERACTION/RATIO FEATURES
    df_derived['Age_Income_Ratio'] = df_derived['Age'] / (df_derived['Income'] / 1000)
    df_derived['Purchase_Age_Ratio'] = df_derived['Purchases'] / df_derived['Age']

    # GENDER-RELATIVE FEATURES
    male_avg_income = df_derived[df_derived['Gender'] == 'Male']['Income'].mean()
    female_avg_income = df_derived[df_derived['Gender'] == 'Female']['Income'].mean()

    male_avg_purchases = df_derived[df_derived['Gender'] == 'Male']['Purchases'].mean()
    female_avg_purchases = df_derived[df_derived['Gender'] == 'Female']['Purchases'].mean()

    # Income_Relative_To_Gender_Avg: Income relative to same-gender average
    df_derived['Income_Relative_To_Gender_Avg'] = np.where(
        df_derived['Gender'] == 'Male',
        df_derived['Income'] / male_avg_income,
        df_derived['Income'] / female_avg_income
    )

    # Purchases_Relative_To_Gender_Avg: Purchases relative to same-gender average
    df_derived['Purchases_Relative_To_Gender_Avg'] = np.where(
        df_derived['Gender'] == 'Male',
        df_derived['Purchases'] / male_avg_purchases,
        df_derived['Purchases'] / female_avg_purchases
    )

    # Drop original categorical columns
    df_derived = df_derived.drop(['Gender', 'Customer_ID'], axis=1)
    
    return df_derived


def get_numerical_features():
    """Return list of numerical features used for scaling."""
    return [
        'Age', 'Income', 'Purchases', 'Income_Age_Ratio', 'Purchase_Intensity',
        'Age_Income_Ratio', 'Purchase_Age_Ratio', 'Income_Relative_To_Gender_Avg',
        'Purchases_Relative_To_Gender_Avg'
    ]


def prepare_features_for_training(df):
    """
    Full preprocessing pipeline for training.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Raw customer data
        
    Returns:
    --------
    tuple: (continuous_features_df, binary_features_df)
    """
    # Apply feature engineering
    df_derived = calculate_derived_features(df)
    
    # Get feature lists
    numerical_features = get_numerical_features()
    
    # Separate continuous and binary features
    df_continuous = df_derived[numerical_features]
    df_binary = df_derived.drop(numerical_features, axis=1)
    
    return df_continuous, df_binary


def get_cluster_names():
    """Return cluster name mapping."""
    return {
        0: 'Old',
        1: 'Middle Aged', 
        2: 'Young'
    }