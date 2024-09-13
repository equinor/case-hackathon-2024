import pandas as pd
import numpy as np
import datetime

def load_power_curve(power_curve_file_name: str) -> np.ndarray:
    """
    Load the power curve from a CSV file and convert it to a NumPy array.

    Parameters:
    - power_curve_file_name (str): Path to the CSV file containing the power curve data.

    Returns:
    - np.ndarray: A NumPy array with power curve data.
    """
    powerCurve = pd.read_csv(power_curve_file_name, sep=";")
    return powerCurve.to_numpy(dtype=np.float32)

def calculate_power(power_curve: np.ndarray, wind_speed: float) -> float:
    """
    Calculate the power output of a wind turbine given the wind speed based on the power curve.

    Parameters:
    - power_curve (np.ndarray): A NumPy array with power curve data.
    - wind_speed (float): The wind speed at which to calculate the power output.

    Returns:
    - float: The power output corresponding to the given wind speed.
    """
    idx_foo = np.argmin(np.abs(power_curve[:, 0] - wind_speed))
    return power_curve[idx_foo, 1]

def prepare_wind_df(wind_df: pd.DataFrame, power_curve: np.ndarray) -> pd.DataFrame:
    """
    Prepares wind data frame with correct indices, duplication handling, and resampling.
    Adds 'Power (MW)' feature by applying the power curve to the 'Speed (m/s)' column.

    Parameters:
    - wind_df (pd.DataFrame): The raw wind data frame.
    - power_curve (np.ndarray): A NumPy array with power curve data.

    Returns:
    - pd.DataFrame: The processed wind data frame with 'Power (MW)' feature added.
    """
    wind_df["Timestamp (UTC)"] = pd.to_datetime(wind_df["Timestamp (UTC)"], format="%d/%m/%Y %H:%M")
    wind_df = wind_df.set_index("Timestamp (UTC)").sort_index()
    wind_df = wind_df[~wind_df.index.duplicated(keep='first')] #some duplicate timestamps in original dataset
    wind_df = wind_df.resample('1h').ffill().fillna(15)  # Assuming 15 m/s as a placeholder fill value
    wind_df["Power (MW)"] = wind_df["Speed (m/s)"].apply(lambda speed: calculate_power(power_curve, speed))
    return wind_df

def prepare_price_df(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepares price data frame with correct indices, duplication handling, and resampling.

    Parameters:
    - price_df (pd.DataFrame): The raw price data frame.

    Returns:
    - pd.DataFrame: The processed price data frame resampled to an hourly frequency.
    """
    price_df["Timestamp (UTC)"] = pd.to_datetime(price_df["Timestamp (UTC)"], format="%d/%m/%Y %H:%M")
    price_df = price_df.set_index("Timestamp (UTC)").sort_index()
    price_df = price_df.resample("1h").ffill()
    return price_df

def generate_dataframe() -> pd.DataFrame:
    """
    Loads power curve, wind data, and price data and merges them into a single data frame.
    Calculates the revenue for each hour by multiplying 'Power (MW)' and 'Price (Eur/MWh)'.

    Returns:
    - pd.DataFrame: The final merged data frame containing wind and price data along with calculated revenue.
    """
    power_curve = load_power_curve('./data/power_curve.csv')
    wind_df = pd.read_csv("./data/wind_data.csv", sep=";")
    price_df = pd.read_csv("./data/electricity_prices.csv", sep=";")

    wind_df = prepare_wind_df(wind_df, power_curve)
    price_df = prepare_price_df(price_df)
    
    wind_df = wind_df.join(price_df)
    wind_df['Revenue (Eur)'] = wind_df['Power (MW)'] * wind_df['Price (Eur/MWh)']

    return wind_df