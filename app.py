from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import os

app = Flask(__name__)

def load_data(year):
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
    return data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    year = request.args.get('year', default=None)
    if year:
        data = load_data(year)
    else:
        data = pd.concat([load_data(year) for year in [2016, 2017, 2018, 2019, 2020]])
        data = data.groupby('State').sum().reset_index()
    
    state_mapping = load_state_mapping()
    data = pd.merge(data, state_mapping, on='State', how='left')
    
    data['EV Percentage'] = (data['Electric (EV)'] / (data['Electric (EV)'] + data['Gasoline'])) * 100
    data['EV Percentage'] = data['EV Percentage'].round(2)
    
    fig = px.choropleth(data,
                        locations='State Code',
                        locationmode='USA-states',
                        color='EV Percentage',
                        color_continuous_scale='Viridis',
                        range_color=(0, data['EV Percentage'].max()),
                        scope='usa',
                        title='EV Registration Percentages by State',
                        hover_name='State',
                        hover_data={'State Code': False,
                                    'EV Percentage': ':.2f',
                                    'Electric (EV)': ':,',
                                    'Gasoline': ':,'}
                        )
    
    fig.update_layout(
        coloraxis_colorbar=dict(
            title='EV Percentage',
            tickvals=[i for i in range(0, int(data['EV Percentage'].max()) + 1, 2)],
            ticktext=[f"{i}%" for i in range(0, int(data['EV Percentage'].max()) + 1, 2)]
        )
    )
    
    emissions_data = load_emissions_data()
    
    # Create a bar chart for Total Pounds of CO2 Equivalent by Car Type
    bar_fig = px.bar(emissions_data, x='Car Type', y='Total Pounds of CO2 Equivalent',
                     title='Total Pounds of CO2 Equivalent by Car Type')
    
    charging_data = load_charging_data(year)
    
    chart_filename = f"ev_chart_{year}.html" if year else "ev_chart_all.html"
    chart_path = os.path.join(app.root_path, 'static', chart_filename)
    fig.write_html(chart_path)
    
    bar_chart_filename = "emissions_bar_chart.html"
    bar_chart_path = os.path.join(app.root_path, 'static', bar_chart_filename)
    bar_fig.write_html(bar_chart_path)
    
    return render_template('data.html', chart_filename=chart_filename,
                           bar_chart_filename=bar_chart_filename,
                           charging_data=charging_data)

if __name__ == '__main__':
    app.run(debug=True)