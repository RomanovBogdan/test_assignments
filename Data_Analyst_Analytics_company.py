from dash import Dash, html, dcc, Output, Input
import plotly.express as px
import pandas as pd
import numpy as np
import plotly.io as pio
import common_style_config as csc

pio.templates.default = "plotly_white"

df = pd.read_csv('./games.csv')


def clean_data(dataframe: pd.DataFrame, threshold: int):
    """
    The function removes irrelevant entries, i.e., games released before the 'threshold' year and
    transforms some of the variables

    :param dataframe: Input dataframe containing game market  data.
    :param threshold: The year threshold. Games released before this year will be removed.
    :return: pandas.DataFrame: Cleaned dataframe with irrelevant entries removed and missing values dropped.
    """
    dataframe = dataframe.query(f'Year_of_Release >= {threshold}')
    dataframe = dataframe.copy()
    dataframe.loc[:, 'User_Score'] = dataframe['User_Score'].replace('tbd', np.nan).astype(float)
    dataframe.loc[:, 'Year_of_Release'] = dataframe['Year_of_Release'].astype(int)
    dataframe = dataframe.dropna()
    return dataframe


def update_axis_ticks(figure, style_config):
    """
    The function modifies the input figure to apply a homogeneous style to the x and y axes.
    The style includes changes to the tickfont family, size, and color, as specified in the CommonStyleConfig instance.

    :param figure: Input figure of type plotly.graph_objs.Figure, to which the styling will be applied.
    :param config: An instance of CommonStyleConfig class containing the styling attributes.
    :return: None. The function modifies the figure in place.
    """
    figure.update_xaxes(
        tickfont=dict(
            family="serif",
            size=14,
            color=style_config.colors['support_text']
        )
    )

    figure.update_yaxes(
        tickfont=dict(
            family="serif",
            size=14,
            color=style_config.colors['support_text']
        )
    )


df_cleaned = clean_data(df, 2000)

external_stylesheets = ['https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/css/bootstrap.min.css']

app = Dash(__name__, external_stylesheets=external_stylesheets)

font_style = {'font-family': 'Arial, sans-serif'}

app.layout = html.Div([
    html.Div([
        html.H2('Dashboard: Games market historical evolution', style={'color': csc.colors['main_text'],
                                                                       'font-family': 'Georgia, serif',
                                                                       'textAlign': 'center'}),
        html.P("""The dashboard is devoted to the visual summary of the state of things in the games market from 2000 to
         2016. The dashboard functionality entails filtering the data based on the genres of games, age-content ratings,
          and year intervals. The area and scatter plots will be automatically adjusted to the filters. They can be used
           to trace the number of released games on various platforms and the "correlation" between critic and
            user scores."""),
        html.H5('Filters', style={'color': csc.colors['support_text'],
                                  'textAlign': 'center'})
    ], style={'background-color': csc.colors['background'],
              'font-family': 'serif'}
    ),

    html.Div([
        html.Div([
            dcc.Dropdown(
                id='genres-filter',
                options=[{'label': genre, 'value': genre} for genre in df_cleaned['Genre'].unique()],
                value=[],
                multi=True,
                placeholder="Select genres"
            )
        ], className='col-md-6'),

        html.Div([
            dcc.Dropdown(
                id='ratings-filter',
                options=[{'label': rating, 'value': rating} for rating in df_cleaned['Rating'].unique()],
                value=[],
                multi=True,
                placeholder="Select ratings"
            )
        ], className='col-md-6')
    ], className='row'),

    html.H4(id='game-count-text', style={'color': csc.colors['support_text'],
                                         'margin-top': '20px',
                                         'font-family': 'serif',
                                         'textAlign': 'center'}),

    html.Div([
        html.Div([
            dcc.Graph(id='game-release-graph',
                      style={'margin-bottom': '35px'})
        ], className='col-md-6'),
        html.Div([
            dcc.Graph(id='critic-user-scatter',
                      style={'margin-bottom': '35px'})
        ], className='col-md-6')
    ], className='row'),

    dcc.RangeSlider(
        id='year-range-filter',
        min=df_cleaned['Year_of_Release'].min(),
        max=df_cleaned['Year_of_Release'].max(),
        value=[df_cleaned['Year_of_Release'].min(), df_cleaned['Year_of_Release'].max()],
        step=1,
        marks={str(int(release_year)): str(int(release_year)) for release_year in
               np.sort(df_cleaned['Year_of_Release'].unique())}
    )
], style={'background-color': '#F5F8FD'}
)


@app.callback(
    Output('game-count-text', 'children'),
    [Input('genres-filter', 'value'),
     Input('ratings-filter', 'value'),
     Input('year-range-filter', 'value')]
)
def update_game_count_text(genres, ratings, year_range):
    filtered_df = df_cleaned[df_cleaned['Genre'].isin(genres) & df_cleaned['Rating'].isin(ratings) &
                             df_cleaned['Year_of_Release'].between(year_range[0], year_range[1])]
    game_count = len(filtered_df)
    return f"Number of the selected games is: {game_count}"


@app.callback(
    Output('game-release-graph', 'figure'),
    [Input('genres-filter', 'value'),
     Input('ratings-filter', 'value'),
     Input('year-range-filter', 'value')]
)
def update_game_release_area_plot(genres, ratings, year_range):
    filtered_df = df_cleaned[df_cleaned['Genre'].isin(genres) & df_cleaned['Rating'].isin(ratings) &
                             df_cleaned['Year_of_Release'].between(year_range[0], year_range[1])]
    grouped_df = filtered_df.groupby(['Year_of_Release', 'Platform']).size().reset_index(name='Number_of_Games')
    fig = px.area(grouped_df, x='Year_of_Release', y='Number_of_Games', color='Platform',
                  labels={
                      "Year_of_Release": "Release year",
                      "Number_of_Games": "Number of games"
                  },
                  )

    fig.update_layout(**csc.common_style_config)
    update_axis_ticks(fig, csc)

    return fig


@app.callback(
    Output('critic-user-scatter', 'figure'),
    [Input('genres-filter', 'value'),
     Input('ratings-filter', 'value'),
     Input('year-range-filter', 'value')]
)
def update_critic_user_scatter_plot(genres, ratings, year_range):
    filtered_df = df_cleaned[df_cleaned['Genre'].isin(genres) & df_cleaned['Rating'].isin(ratings) &
                             df_cleaned['Year_of_Release'].between(year_range[0], year_range[1])]
    fig = px.scatter(filtered_df, x='User_Score', y='Critic_Score', color='Genre',
                     labels={
                         "User_Score": "User score",
                         "Critic_Score": "Critic score"
                     },
                     )

    fig.update_layout(**csc.common_style_config)
    update_axis_ticks(fig, csc)

    return fig


if __name__ == '__main__':
    app.run(debug=True)
