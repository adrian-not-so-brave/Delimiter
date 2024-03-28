from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import os

app = Flask(__name__)

def load_data(year):
    filename = os.path.join("Raw Data", f"{year}.csv")
    data = pd.read_csv(filename, thousands=',', skiprows=1, header=0)
    print(f"Loaded data for year {year}:")
    print(data.head())
    print(f"Column names: {data.columns}")
    return data

def load_state_mapping():
    filename = os.path.join("Raw Data", "state_mapping.csv")
    mapping = pd.read_csv(filename)
    return mapping

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    year = request.args.get('year', default=None)
    if year:
        data = load_data(year)
    else:
        # Load data for all years and combine them
        data = pd.concat([load_data(year) for year in [2016, 2017, 2018, 2019, 2020]])
        data = data.groupby('State').sum().reset_index()
    
    print("Combined data:")
    print(data.head())
    print(f"Column names: {data.columns}")
    
    # Load state mapping data
    state_mapping = load_state_mapping()
    
    # Merge the state mapping with the EV data
    data = pd.merge(data, state_mapping, on='State', how='left')
    
    # Process the data and create visualizations
    data['EV Percentage'] = (data['Electric (EV)'] / (data['Electric (EV)'] + data['Gasoline'])) * 100
    data['EV Percentage'] = data['EV Percentage'].round(2)
    
    # Create a choropleth map using Plotly
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
    
    # Customize the colorbar
    fig.update_layout(
        coloraxis_colorbar=dict(
            title='EV Percentage',
            tickvals=[i for i in range(0, int(data['EV Percentage'].max()) + 1, 2)],
            ticktext=[f"{i}%" for i in range(0, int(data['EV Percentage'].max()) + 1, 2)]
        )
    )
    
    chart_filename = f"ev_chart_{year}.html" if year else "ev_chart_all.html"
    chart_path = os.path.join(app.root_path, 'static', chart_filename)
    fig.write_html(chart_path)
    
    return render_template('data.html', chart_filename=chart_filename)

if __name__ == '__main__':
    app.run(debug=True)