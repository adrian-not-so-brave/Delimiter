from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import os

app = Flask(__name__)

def load_us_data(year):
    filename = os.path.join("Raw Data", f"{year}.csv")
    data = pd.read_csv(filename, thousands=',', skiprows=1, header=0)
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
        data = data.sum(numeric_only=True)
        data['Year'] = 'All Years'
        data = data.astype({'Year': str})  # Convert 'Year' column to string dtype
    return data

def load_eu_data(year):
    filename = os.path.join("Raw Data", f"{year}_registrationEU.csv")
    data = pd.read_csv(filename, sep='\t', thousands=',', skiprows=1)
    data = data.iloc[:, :-1]  # Remove the last column
    data = data.melt(id_vars=[data.columns[0]], var_name='Month', value_name='Registrations')
    data.columns = ['Country', 'Month', 'Registrations']
    data['Registrations'] = pd.to_numeric(data['Registrations'], errors='coerce')
    data = data.groupby('Country')['Registrations'].sum().reset_index()
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
        if us_year:
            us_data = load_us_data(us_year)
        else:
            us_data = pd.concat([load_us_data(year) for year in [2016, 2017, 2018, 2019, 2020]])
            us_data = us_data.groupby('State').sum().reset_index()

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

        us_chart_filename = f"us_ev_chart_{us_year}.html" if us_year else "us_ev_chart_all.html"
        us_chart_path = os.path.join(app.root_path, 'static', us_chart_filename)
        us_fig.write_html(us_chart_path)

        emissions_data = load_emissions_data()
        charging_data = load_charging_data(us_year)

        return render_template('data.html', us_chart_filename=us_chart_filename,
                               emissions_data=emissions_data.to_dict(orient='records'),
                               charging_data=charging_data)

    elif data_type == 'eu':
        eu_data = load_eu_data(eu_year)
        eu_fig = px.choropleth(eu_data,
                       locations='Country',
                       locationmode='country names',  # Use 'country names' instead of 'europe'
                       color='Registrations',
                       color_continuous_scale='Viridis',
                       scope='europe',
                       title='EU Vehicle Registrations by Country',
                       hover_name='Country',
                       hover_data={'Registrations': ':,'}
                       )

        eu_chart_filename = f"eu_registration_chart_{eu_year}.html" if eu_year else "eu_registration_chart_all.html"
        eu_chart_path = os.path.join(app.root_path, 'static', eu_chart_filename)
        eu_fig.write_html(eu_chart_path)

        return render_template('data.html', eu_chart_filename=eu_chart_filename)

    return render_template('data.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)