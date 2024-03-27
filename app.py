from flask import Flask, render_template, request
import pandas as pd
import matplotlib.pyplot as plt
import os

app = Flask(__name__)

def load_data(year):
    filename = os.path.join("Raw Data", f"{year}.csv")
    data = pd.read_csv(filename, thousands=',', skiprows=1, header=0)
    print(f"Loaded data for year {year}:")
    print(data.head())
    print(f"Column names: {data.columns}")
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
        # Load data for all years and combine them
        data = pd.concat([load_data(year) for year in [2016, 2017, 2018, 2019, 2020]])
    
    print("Combined data:")
    print(data.head())
    print(f"Column names: {data.columns}")
    
    # Process the data and create visualizations
    states = data['State']
    ev_counts = data['Electric (EV)']

    # Sort the states based on EV counts in descending order
    sorted_data = sorted(zip(states, ev_counts), key=lambda x: x[1], reverse=True)

    # Get the top N states and their EV counts
    top_n = 10
    top_states, top_ev_counts = zip(*sorted_data[:top_n])

    plt.figure(figsize=(10, 6))
    plt.barh(top_states, top_ev_counts)
    plt.xlabel('Number of EVs')
    plt.ylabel('State')
    plt.title(f'Top {top_n} States by EV Registration Counts')
    plt.tight_layout()

    chart_filename = f"ev_chart_{year}.png" if year else "ev_chart_all.png"
    chart_path = os.path.join(app.root_path, 'static', chart_filename)
    plt.savefig(chart_path)
    
    return render_template('data.html', chart_filename=chart_filename)

if __name__ == '__main__':
    app.run(debug=True)