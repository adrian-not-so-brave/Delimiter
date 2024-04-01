from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import os

app = Flask(__name__)

def load_us_data(year):
    if year:
        filename = os.path.join("Raw Data", f"{year}.csv")
        data = pd.read_csv(filename, thousands=',', skiprows=1, header=0)
    else:
        filenames = [os.path.join("Raw Data", f"{yr}.csv") for yr in [2016, 2017, 2018, 2019, 2020]]
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
    data = pd.read_csv(filename)
    data.columns = data.columns.str.strip()  # Remove leading/trailing whitespace from column names
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    data_type = request.args.get('data_type')
    us_year = request.args.get('us_year', default=None)
    eu_year = request.args.get('eu_year', default=None)

    if data_type == 'us':
        us_data = load_us_data(us_year)
        state_mapping = load_state_mapping()
        us_data = pd.merge(us_data, state_mapping, on='State', how='left')

        us_data['EV Percentage'] = (us_data['Electric (EV)'] / (us_data['Electric (EV)'] + us_data['Gasoline'])) * 100
        us_data['EV Percentage'] = us_data['EV Percentage'].round(2)

        us_fig = px.choropleth(us_data,
                               locations='State Code',
                               locationmode='USA-states',
                               color='EV Percentage',
                               color_continuous_scale='Viridis',
                               range_color=(0, us_data['EV Percentage'].max()),
                               scope='usa',
                               title='US EV Registration Percentages by State',
                               hover_name='State',
                               hover_data={'State Code': False,
                                           'EV Percentage': ':.2f',
                                           'Electric (EV)': ':,',
                                           'Gasoline': ':,'}
                               )

        us_fig.update_layout(
            coloraxis_colorbar=dict(
                title='EV Percentage',
                tickvals=[i for i in range(0, int(us_data['EV Percentage'].max()) + 1, 2)],
                ticktext=[f"{i}%" for i in range(0, int(us_data['EV Percentage'].max()) + 1, 2)]
            )
        )

        us_chart_html = us_fig.to_html(full_html=False)

        emissions_data = load_emissions_data()
        emissions_fig = px.bar(emissions_data, x='Car Type', y='Total Pounds of CO2 Equivalent',
                               title='Total Pounds of CO2 Equivalent by Car Type')
        emissions_chart_html = emissions_fig.to_html(full_html=False)

        charging_data = load_charging_data(us_year)

        return render_template('data.html', us_chart_html=us_chart_html,
                               emissions_chart_html=emissions_chart_html,
                               charging_data=charging_data)

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
                               eu_ev_data=eu_ev_data.to_dict(orient='records'))

    return render_template('data.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)