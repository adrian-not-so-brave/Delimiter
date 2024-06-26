from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import os
import csv

app = Flask(__name__)

def load_us_data(year):
    if year:
        filename = os.path.join("Raw Data", f"{year}.csv")
        data = pd.read_csv(filename, thousands=',', skiprows=1, header=0)
    else:
        filenames = [os.path.join("Raw Data", f"{yr}.csv") for yr in [2016, 2017, 2018, 2019, 2020, 2022]]  # Add 2022 to the list
        data_frames = []
        for filename in filenames:
            df = pd.read_csv(filename, thousands=',', skiprows=1, header=0)
            data_frames.append(df)
        data = pd.concat(data_frames)
        data = data.groupby('State').sum().reset_index()

    return data

def load_state_mapping():
    filename = os.path.join("Raw Data", "state_mapping.csv")
    mapping = pd.read_csv(filename)
    return mapping

def load_emissions_data():
    filename = os.path.join("Raw Data", "emissions_by_car_type.csv")
    data = pd.read_csv(filename)
    return data

def load_charging_data(year):
    filename = os.path.join("Raw Data", "us_total_charging.csv")
    data = pd.read_csv(filename, quotechar='"', skipinitialspace=True)
    data.columns = data.columns.str.strip()  # Remove leading/trailing whitespace from column names
    data = data.applymap(lambda x: int(str(x).replace(',', '')))  # Convert values to integers
    if year:
        data = data[data['Year'] == int(year)].iloc[0]
    else:
        data = data.sum(numeric_only=True).to_dict()
        data['Year'] = 'All Years'
    return data

def load_eu_data(year):
    if year:
        filename = os.path.join("Raw Data", f"{year}_registrationEU.csv")
        data = pd.read_csv(filename, sep='\t', thousands=',', skiprows=1)
        data = data.iloc[:, :-1]  # Remove the last column
        data = data.melt(id_vars=[data.columns[0]], var_name='Month', value_name='Registrations')
        data.columns = ['Country', 'Month', 'Registrations']
        data['Registrations'] = pd.to_numeric(data['Registrations'], errors='coerce')
        data = data.groupby('Country')['Registrations'].sum().reset_index()
    else:
        filenames = [os.path.join("Raw Data", f"{yr}_registrationEU.csv") for yr in [2016, 2017, 2018, 2019, 2020]]
        data_frames = []
        for filename in filenames:
            df = pd.read_csv(filename, sep='\t', thousands=',', skiprows=1)
            df = df.iloc[:, :-1]  # Remove the last column
            df = df.melt(id_vars=[df.columns[0]], var_name='Month', value_name='Registrations')
            df.columns = ['Country', 'Month', 'Registrations']
            df['Registrations'] = pd.to_numeric(df['Registrations'], errors='coerce')
            data_frames.append(df)
        data = pd.concat(data_frames)
        data = data.groupby('Country')['Registrations'].sum().reset_index()

    return data

def load_eu_ev_data():
    filename = os.path.join("Raw Data", "new-electric-vehicles-by-country-3.csv")
    data = pd.read_csv(filename)
    return data

def load_total_cars_data():
    total_cars_data = {}
    file_path = os.path.join("Raw Data", "total_cars_us.csv")
    with open(file_path, 'r') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Skip the header row
        for row in csv_reader:
            state = row[0].strip()
            total_cars_str = row[-1].replace(',', '')
            if total_cars_str:
                try:
                    total_cars = int(total_cars_str)
                    total_cars_data[state] = total_cars
                except ValueError:
                    print(f"Invalid value for state: {state}")
            else:
                print(f"Empty value for state: {state}")
    return total_cars_data

def calculate_co2_reduction(state, ev_increase_pct, phev_increase_pct, hev_increase_pct, us_data, emissions_data):
    try:
        state_data = us_data[us_data['State'] == state].iloc[0]
        ev_count = state_data['Electric (EV)']
        phev_count = state_data['Plug-In Hybrid Electric (PHEV)']
        hev_count = state_data['Hybrid Electric (HEV)']
        gasoline_count = state_data['Gasoline']

        total_vehicles = ev_count + phev_count + hev_count + gasoline_count

        new_ev_count = int(ev_count * (1 + ev_increase_pct / 100))
        new_phev_count = int(phev_count * (1 + phev_increase_pct / 100))
        new_hev_count = int(hev_count * (1 + hev_increase_pct / 100))
        new_gasoline_count = int(total_vehicles - new_ev_count - new_phev_count - new_hev_count)

        ev_emissions = emissions_data[emissions_data['Car Type'] == 'All Electric']['Total Pounds of CO2 Equivalent'].values[0]
        phev_emissions = emissions_data[emissions_data['Car Type'] == 'Plug In Hybrid']['Total Pounds of CO2 Equivalent'].values[0]
        hev_emissions = emissions_data[emissions_data['Car Type'] == 'Hybrid']['Total Pounds of CO2 Equivalent'].values[0]
        gasoline_emissions = emissions_data[emissions_data['Car Type'] == 'Gasoline']['Total Pounds of CO2 Equivalent'].values[0]

        current_emissions = ev_count * ev_emissions + phev_count * phev_emissions + hev_count * hev_emissions + gasoline_count * gasoline_emissions
        new_emissions = new_ev_count * ev_emissions + new_phev_count * phev_emissions + new_hev_count * hev_emissions + new_gasoline_count * gasoline_emissions

        co2_reduction = current_emissions - new_emissions
        co2_reduction_pct = (co2_reduction / current_emissions) * 100

        co2_reduction_ev = (new_ev_count - ev_count) * (gasoline_emissions - ev_emissions)
        co2_reduction_phev = (new_phev_count - phev_count) * (gasoline_emissions - phev_emissions)
        co2_reduction_hev = (new_hev_count - hev_count) * (gasoline_emissions - hev_emissions)

        return {
            'state': state,
            'ev_increase_pct': ev_increase_pct,
            'phev_increase_pct': phev_increase_pct,
            'hev_increase_pct': hev_increase_pct,
            'co2_reduction': co2_reduction,
            'co2_reduction_pct': co2_reduction_pct,
            'co2_reduction_ev': co2_reduction_ev,
            'co2_reduction_phev': co2_reduction_phev,
            'co2_reduction_hev': co2_reduction_hev,
            'ev_count': ev_count,
            'phev_count': phev_count,
            'hev_count': hev_count,
            'gasoline_count': gasoline_count,
            'new_ev_count': new_ev_count,
            'new_phev_count': new_phev_count,
            'new_hev_count': new_hev_count,
            'new_gasoline_count': new_gasoline_count
        }
    except (KeyError, IndexError, ValueError, ZeroDivisionError):
        return {
            'state': state,
            'ev_increase_pct': ev_increase_pct,
            'phev_increase_pct': phev_increase_pct,
            'hev_increase_pct': hev_increase_pct,
            'co2_reduction': None,
            'co2_reduction_pct': None,
            'co2_reduction_ev': None,
            'co2_reduction_phev': None,
            'co2_reduction_hev': None,
            'ev_count': None,
            'phev_count': None,
            'hev_count': None,
            'gasoline_count': None,
            'new_ev_count': None,
            'new_phev_count': None,
            'new_hev_count': None,
            'new_gasoline_count': None
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data', methods=['GET', 'POST'])
def data():
    data_type = request.args.get('data_type')
    us_year = request.args.get('us_year', default=None)
    eu_year = request.args.get('eu_year', default=None)

    if data_type == 'us':
        us_data = load_us_data(us_year)
        state_mapping = load_state_mapping()
        us_data = pd.merge(us_data, state_mapping, on='State', how='left')

        us_data['Total Alt. Vehicles'] = us_data['Electric (EV)'] + us_data['Plug-In Hybrid Electric (PHEV)'] + us_data['Hybrid Electric (HEV)']
        us_data['Total Vehicles'] = us_data['Total Alt. Vehicles'] + us_data['Gasoline']
        us_data['Alt. Vehicle Percentage'] = (us_data['Total Alt. Vehicles'] / us_data['Total Vehicles']) * 100
        us_data['Alt. Vehicle Percentage'] = us_data['Alt. Vehicle Percentage'].round(2)

        us_fig = px.choropleth(us_data,
                               locations='State Code',
                               locationmode='USA-states',
                               color='Alt. Vehicle Percentage',
                               color_continuous_scale='Viridis',
                               range_color=(0, us_data['Alt. Vehicle Percentage'].max()),
                               scope='usa',
                               title='US Alternative Vehicle Registration Percentages by State',
                               hover_name='State',
                               hover_data={'State Code': False,
                                           'Alt. Vehicle Percentage': ':.2f',
                                           'Electric (EV)': ':,',
                                           'Plug-In Hybrid Electric (PHEV)': ':,',
                                           'Hybrid Electric (HEV)': ':,',
                                           'Gasoline': ':,'}
                               )

        us_fig.update_layout(
            coloraxis_colorbar=dict(
                title='Alt. Vehicle Percentage',
                tickvals=[i for i in range(0, int(us_data['Alt. Vehicle Percentage'].max()) + 1, 2)],
                ticktext=[f"{i}%" for i in range(0, int(us_data['Alt. Vehicle Percentage'].max()) + 1, 2)]
            )
        )

        us_chart_html = us_fig.to_html(full_html=False)

        emissions_data = load_emissions_data()
        emissions_fig = px.bar(emissions_data, x='Car Type', y='Total Pounds of CO2 Equivalent',
                               title='Total Pounds of CO2 Equivalent by Car Type')
        emissions_chart_html = emissions_fig.to_html(full_html=False)

        charging_data = load_charging_data(us_year)

        total_cars_data = load_total_cars_data()

        if request.method == 'POST':
            state = request.form['state']
            ev_increase_pct = float(request.form['ev_increase_pct'])
            phev_increase_pct = float(request.form['phev_increase_pct'])
            hev_increase_pct = float(request.form['hybrid_increase_pct'])
            co2_reduction_data = calculate_co2_reduction(state, ev_increase_pct, phev_increase_pct, hev_increase_pct, us_data, emissions_data)
        else:
            co2_reduction_data = None

        return render_template('data.html', us_chart_html=us_chart_html,
                               emissions_chart_html=emissions_chart_html,
                               charging_data=charging_data,
                               us_data=us_data,
                               co2_reduction_data=co2_reduction_data)

    elif data_type == 'eu':
        eu_data = load_eu_data(eu_year)
        eu_fig = px.choropleth(eu_data,
                               locations='Country',
                               locationmode='country names',
                               color='Registrations',
                               color_continuous_scale='Viridis',
                               scope='europe',
                               title='EU Vehicle Registrations by Country',
                               hover_name='Country',
                               hover_data={'Registrations': ':,'}
                               )

        eu_chart_html = eu_fig.to_html(full_html=False)

        eu_ev_data = load_eu_ev_data()

        return render_template('data.html', eu_chart_html=eu_chart_html,
                               eu_ev_data=eu_ev_data.to_dict(orient='records'),
                               eu_data=eu_data) 

    return render_template('data.html', eu_data=None)

@app.route('/calculate_eu_ev_percentage', methods=['POST'])
def calculate_eu_ev_percentage():
    country = request.form['country']
    eu_data = load_eu_data(None)
    eu_ev_data = load_eu_ev_data()
    
    country_data = eu_data[eu_data['Country'] == country].iloc[0]
    total_registrations = country_data['Registrations']
    
    country_ev_data = eu_ev_data[eu_ev_data['Country:text'] == country].iloc[0]
    bev_count = country_ev_data['Battery electric vehicels (number):number']
    phev_count = country_ev_data['Plug-in hybrid electric vehicles (number):number']
    total_ev_count = bev_count + phev_count
    
    bev_percentage = (bev_count / total_registrations) * 100
    phev_percentage = (phev_count / total_registrations) * 100
    total_ev_percentage = (total_ev_count / total_registrations) * 100
    
    eu_ev_percentage = {
        'country': country,
        'bev_percentage': round(bev_percentage, 2),
        'phev_percentage': round(phev_percentage, 2),
        'total_ev_percentage': round(total_ev_percentage, 2)
    }
    
    eu_fig = px.choropleth(eu_data,
                           locations='Country',
                           locationmode='country names',
                           color='Registrations',
                           color_continuous_scale='Viridis',
                           scope='europe',
                           title='EU Vehicle Registrations by Country',
                           hover_name='Country',
                           hover_data={'Registrations': ':,'}
                           )

    eu_chart_html = eu_fig.to_html(full_html=False)
    
    return render_template('data.html', eu_chart_html=eu_chart_html, eu_ev_data=eu_ev_data.to_dict(orient='records'),
                           eu_data=eu_data, eu_ev_percentage=eu_ev_percentage)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)