import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from abc import ABC, abstractmethod
import datetime
import pandas as pd
import numpy as np

sns.set()

#vessel params
MAX_WIND_SPEED=5
MAINTENANCE_DURATION=1 # in days
VESSEL_COST=50000

#cooling system params
INIT_PRES=2 #bars
MIN_PRES=0.5 #bars
DECLINE_RATE=0.0001 #bars per 30 min interval

class MaintenanceStrategy(ABC):
    """
    Abstract base class representing a maintenance strategy for wind turbines.
    """
    def __init__(self) -> None:
        """
        Initializes the maintenance strategy.
        """
        self.n_visits=0

    @abstractmethod
    def fix_pressure(self, current_pressure: float, current_time: datetime, current_wind_speed: float, current_price: float) -> bool:
        """
        Abstract method that determines whether to send a vessel for maintenance based on the current pressure.

        Parameters:
        - current_pressure (float): The current pressure in the cooling system.
        - current_time (datetime): The current timestamp.
        - current_wind_speed (float): The current wind speed.
        - current_price (float): The current electricity price.

        Returns:
        - bool: True if the current pressure is less than or equal to the threshold, False otherwise.
        """
        pass
        
    def add_downtimes(self, wind_df: pd.DataFrame,verbose:bool=False) -> pd.DataFrame:
        """
        Adds downtime to the wind data frame based on the maintenance strategy.

        Parameters:
        wind_df (pd.DataFrame): The wind data frame that contains wind turbine data.

        Returns:
        pd.DataFrame: The wind data frame with the applied downtimes.
        """

        wind_df["pressure"]=np.nan
        wind_df["visit"]=0
        current_pressure=INIT_PRES
        end_visit_ts=wind_df.index[-1]+datetime.timedelta(days=1)
        pending_visit=False

        for ind,row in wind_df.iterrows():

            current_pressure-=DECLINE_RATE

            send_vessel=self.fix_pressure(current_pressure,ind,row["Speed (m/s)"],row["Price (Eur/MWh)"])
            if pending_visit==False and send_vessel:
                
                #Extract info for chosen vessel
                max_wind_speed=MAX_WIND_SPEED
                maintenance_duration=MAINTENANCE_DURATION

                # No maintenance if constraints not satisfied
                if row["Speed (m/s)"]>max_wind_speed: 
                    continue

                if verbose:
                    print(f'Vessel sent, pressure: {current_pressure} bars, wind speed:{row["Speed (m/s)"]} m/s, price:{row["Price (Eur/MWh)"]} Eur/MWh')

                # Record visit
                wind_df.loc[ind,"visit"]=1
                self.n_visits+=1

                # set end date for the visit , has to be within the dataset
                if ind+datetime.timedelta(days=maintenance_duration)<wind_df.index[-1]:
                    end_visit_ts=wind_df[wind_df.index>=ind+datetime.timedelta(days=maintenance_duration)].index[0] 
                else:
                    end_visit_ts=wind_df.index[-1]

                pending_visit=True

            # ongoing visit flag
            if pending_visit==True:
                wind_df.loc[ind,"visit"]=1

            # if the visit is over , remove the flag and put pressure to initial value
            if ind==end_visit_ts:
                current_pressure=INIT_PRES
                pending_visit=False

            wind_df.loc[ind,"pressure"]=current_pressure

        return wind_df
    
           
    def calculate_revenue(self, wind_df: pd.DataFrame) -> float:
        """
        Calculate the total revenue after accounting for maintenance costs.

        Parameters:
        wind_df (pd.DataFrame): The wind data frame that contains wind turbine data.

        Returns:
        float: The total calculated revenue.
        """

        cost_visits=self.n_visits*VESSEL_COST
        total_revenue=wind_df.loc[(wind_df["pressure"]>=MIN_PRES)&(wind_df["visit"]==0),"Revenue (Eur)"].sum()-cost_visits

        return total_revenue

    def plot_profiles(self, wind_df: pd.DataFrame) -> None:
        """
        Plot the wind speed, price, and pressure profiles over time.

        Parameters:
        wind_df (pd.DataFrame): The wind data frame to plot.
        """

        fig, ax = plt.subplots(3, 1, figsize=(10, 5), sharex=True)

        # Speed subplot
        wind_df[["Speed (m/s)"]].rolling("7D").mean().plot(y="Speed (m/s)", ax=ax[0], color='dodgerblue')
        ax[0].set_title('Wind Speed Over Time')
        ax[0].set_ylabel('Speed (m/s)')
        ax[0].grid(True)

        # Price subplot
        wind_df.plot(y="Price (Eur/MWh)", ax=ax[1], color='green')
        ax[1].set_title('Price Over Time')
        ax[1].set_ylabel('Price (EUR/MWhe)')
        ax[1].grid(True)

        # Pressure subplot
        wind_df.plot(y="pressure", ax=ax[2], color='purple')
        ax[2].set_title('Pressure Over Time')
        ax[2].set_ylabel('Pressure (bars)')
        ax[2].grid(True)

        # Fill areas for pressure subplot
        ax[2].fill_between(wind_df.index, wind_df['pressure'], where=(wind_df['pressure'] < MIN_PRES), 
                        facecolor='red', alpha=0.3, interpolate=True, label="Low Pressure")

                            # Iterate through the DataFrame and draw horizontal bars for visit periods
        # Plot a cross where visit is 1
        visits = wind_df[wind_df['visit'] == 1]
        if len(visits)>0:
            ax[2].scatter(visits.index, visits['pressure'], color='black', marker='x', label='Visit')


        for label in ax[2].get_xticklabels():
            label.set_rotation(45)
            label.set_horizontalalignment('right')

        ax[2].legend()
        fig.tight_layout()
        plt.show()
 
class ScheduledMaintenance(MaintenanceStrategy):
    """
    Represents a scheduled maintenance strategy for wind turbines,
    where maintenance is scheduled for a specific day of the month.
    """
    def __init__(self, day: int, month: int) -> None:
        """
        Initializes the ScheduledMaintenance strategy.

        Parameters:
        - day (int): The day of the month on which maintenance is scheduled.
        - month (int): The month on which maintenance is scheduled.
        """
        super().__init__()
        self.name = "Scheduled Maintenance"
        self.month = month
        self.day = day

    def fix_pressure(self, current_pressure: float, current_time: datetime, current_wind_speed: float, current_price: float) -> bool:
        """
        Determines whether to send a vessel for maintenance based on the current pressure.
        """
        return current_time.month == self.month and current_time.day == self.day


class ConditionMonitoring(MaintenanceStrategy):
    """
    Represents a condition-based monitoring maintenance strategy for wind turbines,
    where maintenance is triggered by pressure falling below a threshold.
    """
    def __init__(self, pressure_threshold: float) -> None:
        """
        Initializes the ConditionMonitoring strategy.

        Parameters:
        - pressure_threshold (float): The pressure threshold below which maintenance is triggered.
        """
        super().__init__()
        self.name = "Condition Monitoring"
        self.pressure_threshold = pressure_threshold

    def fix_pressure(self, current_pressure: float, current_time: datetime, current_wind_speed: float, current_price: float) -> bool:
        """
        Determines whether to send a vessel for maintenance based on the current pressure.
        """
        return current_pressure <= self.pressure_threshold
        
